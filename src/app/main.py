import math
import base64
import warnings
import json
import os
from io import BytesIO
from pathlib import Path

import pandas as pd
import geopandas as gpd
import pgeocode
import folium
from branca.element import Element
from PIL import Image

# Importiere neuen Data Loader (mit Fallback für relative/absolute imports)
try:
    from .data_loader import load_projects, get_data_source
except ImportError:
    from data_loader import load_projects, get_data_source

ICON_SIZE = 18
PIN_SIZE = 36

warnings.filterwarnings("ignore")

# ======================================================
# BASIS
# ======================================================
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# ======================================================
# BASIS (portable)
# ======================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../deutschlandkarte
if load_dotenv:
    load_dotenv(PROJECT_ROOT / ".env")  # lokale .env (nicht committen)

def env_path(var_name: str, default: Path) -> Path:
    v = os.getenv(var_name, "").strip()
    return Path(v).expanduser().resolve() if v else default

BASE_DIR = env_path("DEUTSCHLANDKARTE_BASE", PROJECT_ROOT)

GERMANY_GEOJSON_PATH = env_path("GERMANY_GEOJSON_PATH", BASE_DIR / 'assets/germany.geojson')
EUROPE_GEOJSON_PATH  = env_path("EUROPE_GEOJSON_PATH",  BASE_DIR / 'assets/europe.geojson')
EXCEL_PATH           = env_path("EXCEL_PATH",           BASE_DIR / 'data/Datenmuster_OSNV_Maps.xlsx')
ICON_DIR             = env_path("ICON_DIR",             BASE_DIR / 'assets/icons')
OUT_HTML             = env_path("OUT_HTML",             BASE_DIR / "deutschland_projekte.html")
JITTER_STEP_M = 120

# ======================================================
# FARBEN / WHITELIST SHEETS
# (wird v.a. als Whitelist genutzt, damit nur diese Sheets gelesen werden + UI Labels)
# ======================================================
CATEGORY_COLOR = {
    "EZA":  "#5c7cfa",
    "EZAR": "#51cf66",
    "OSNV": "#fcc419",
    "EZE":  "#74c0fc",
}

# Status wird NUR Angebot vs Auftrag unterschieden (alles andere => Auftrag)
STATUS_RING_COLOR = {
    "Angebot": "#e9c46a",
    "Auftrag": "#2f9e44",
}

# ======================================================
# ICONS (Art muss exakt einem dieser Keys entsprechen)
# ======================================================
PLANT_ICONS = {
    "Batterie": ICON_DIR / "Batterie.png",
    "Wind": ICON_DIR / "Wind.png",
    "BHKW": ICON_DIR / "BHKW.png",
    "HKW": ICON_DIR / "HKW.png",
    "Wasser": ICON_DIR / "Wasser.png",
    "PV": ICON_DIR / "PV.png",
    "EZAR": ICON_DIR / "EZAR.png",
}

# ======================================================
# HAUPTSTÄDTE DE (16)
# ======================================================
GER_STATE_CAPITALS = {
    "Berlin": (52.5200, 13.4050),
    "Hamburg": (53.5488, 9.9872),
    "Bremen": (53.0793, 8.8017),
    "Hannover": (52.3759, 9.7320),
    "Kiel": (54.3233, 10.1228),
    "Schwerin": (53.6355, 11.4012),
    "Potsdam": (52.3906, 13.0645),
    "Magdeburg": (52.1205, 11.6276),
    "Dresden": (51.0504, 13.7373),
    "Erfurt": (50.9848, 11.0299),
    "Wiesbaden": (50.0826, 8.2415),
    "Mainz": (49.9929, 8.2473),
    "Saarbrücken": (49.2402, 6.9969),
    "Stuttgart": (48.7758, 9.1829),
    "München": (48.1374, 11.5755),
    "Düsseldorf": (51.2277, 6.7735),
}

# ======================================================
# NACHBARLÄNDER DEUTSCHLAND
# ======================================================
GER_NEIGHBORS = {
    "Dänemark", "Danmark", "Denmark", "Polen", "Poland", "Czechia", "Czech Republic",
    "Österreich", "Austria", "Schweiz", "Switzerland", "Frankreich", "France", 
    "Luxemburg", "Luxembourg", "Belgien", "Belgium", "Niederlande", "Netherlands"
}

# Länder die zu Europa gehören (ohne Russland, Türkei, Kasachstan, etc.)
EUROPEAN_COUNTRIES = {
    "Aland", "Albania", "Andorra", "Armenia", "Austria", "Azerbaijan",
    "Belarus", "Belgium", "Bosnia and Herzegovina", "Bulgaria", "Croatia", 
    "Cyprus", "Czechia", "Dänemark", "Danmark", "Denmark", "Estonia", 
    "Faroe Islands", "Finland", "France", "Georgia", "Greece", "Guernsey",
    "Hungary", "Iceland", "Ireland", "Isle of Man", "Italy", "Jersey",
    "Kosovo", "Latvia", "Liechtenstein", "Lithuania", "Luxembourg", "Malta",
    "Moldova", "Monaco", "Montenegro", "Netherlands", "North Macedonia", 
    "Norway", "Poland", "Portugal", "Romania", "Slovakia", "Slovenia", 
    "Spain", "Sweden", "Switzerland", "United Kingdom", "Vatican"
}

# Farben für Länder - verschiedene leichte Farbtöne
COUNTRY_COLORS = {
    # Nachbarländer - heller
    "Austria": "#c7e9c0", "Belgium": "#d9f0d3", "Czechia": "#e5f5e0",
    "Czech Republic": "#e5f5e0", "Denmark": "#dae8f4", "Dänemark": "#dae8f4",
    "France": "#f4f1de", "Frankreich": "#f4f1de", "Luxembourg": "#e2f0d9", 
    "Luxemburg": "#e2f0d9", "Netherlands": "#daeef7", "Niederlande": "#daeef7", 
    "Poland": "#d4edda", "Switzerland": "#e8d5f2", "Schweiz": "#e8d5f2",
    # Andere Länder - unterschiedliche Pastelltöne
    "Aland": "#e0f2f7", "Albania": "#d9e8d9", "Andorra": "#f0d9e8",
    "Armenia": "#f5ddb0", "Azerbaijan": "#fce4d6", "Belarus": "#dae8f4",
    "Bulgaria": "#e5d9f0", "Croatia": "#d9f0d3", "Cyprus": "#fff4d6",
    "Estonia": "#cce7ff", "Finland": "#ccf0ff", "Georgia": "#ffe5cc",
    "Greece": "#fff9e6", "Guernsey": "#e5f2ff", "Hungary": "#e2d9f0",
    "Iceland": "#ccdaff", "Ireland": "#d9f0d3", "Isle of Man": "#e5f2ff",
    "Italy": "#fce5d6", "Jersey": "#e5f2ff", "Kosovo": "#e0d9f0",
    "Latvia": "#cce7ff", "Liechtenstein": "#e8d5f2", "Lithuania": "#cce7ff",
    "Malta": "#fff4d6", "Moldova": "#f0d9e8", "Monaco": "#fce5d6",
    "Montenegro": "#e0d9f0", "North Macedonia": "#e5d9f0", "Norway": "#ccdaff",
    "Portugal": "#fff9e6", "Romania": "#f0d9e8", "Slovakia": "#d9f0d3",
    "Slovenia": "#d9f0d3", "Spain": "#fff9e6", "Sweden": "#ccdaff",
    "United Kingdom": "#e5f2ff", "Vatican": "#fce5d6"
}

# ======================================================
# EU-LÄNDER HAUPTSTÄDTE (nur wenn Land eingeblendet wird)
# Keys müssen zu europe.geojson ADMIN passen (idR englische Ländernamen)
# Falls ein Land fehlt => es wird einfach ohne Hauptstadt angezeigt.
# ======================================================
EU_CAPITALS = {
    "Austria": ("Vienna", 48.2082, 16.3738),
    "Belgium": ("Brussels", 50.8503, 4.3517),
    "Bulgaria": ("Sofia", 42.6977, 23.3219),
    "Croatia": ("Zagreb", 45.8150, 15.9819),
    "Cyprus": ("Nicosia", 35.1856, 33.3823),
    "Czechia": ("Prague", 50.0755, 14.4378),
    "Denmark": ("Copenhagen", 55.6761, 12.5683),
    "Estonia": ("Tallinn", 59.4370, 24.7536),
    "Finland": ("Helsinki", 60.1699, 24.9384),
    "France": ("Paris", 48.8566, 2.3522),
    "Greece": ("Athens", 37.9838, 23.7275),
    "Hungary": ("Budapest", 47.4979, 19.0402),
    "Ireland": ("Dublin", 53.3498, -6.2603),
    "Italy": ("Rome", 41.9028, 12.4964),
    "Latvia": ("Riga", 56.9496, 24.1052),
    "Lithuania": ("Vilnius", 54.6872, 25.2797),
    "Luxembourg": ("Luxembourg", 49.6116, 6.1319),
    "Malta": ("Valletta", 35.8989, 14.5146),
    "Netherlands": ("Amsterdam", 52.3676, 4.9041),
    "Poland": ("Warsaw", 52.2297, 21.0122),
    "Portugal": ("Lisbon", 38.7223, -9.1393),
    "Romania": ("Bucharest", 44.4268, 26.1025),
    "Slovakia": ("Bratislava", 48.1486, 17.1077),
    "Slovenia": ("Ljubljana", 46.0569, 14.5058),
    "Spain": ("Madrid", 40.4168, -3.7038),
    "Sweden": ("Stockholm", 59.3293, 18.0686),

    # häufig zusätzlich gebraucht (nicht EU, aber in Europe.geojson oft enthalten)
    "United Kingdom": ("London", 51.5074, -0.1278),
    "Norway": ("Oslo", 59.9139, 10.7522),
    "Switzerland": ("Bern", 46.9480, 7.4474),
    "Iceland": ("Reykjavik", 64.1466, -21.9426),
    "Serbia": ("Belgrade", 44.7866, 20.4489),
    "Bosnia and Herz.": ("Sarajevo", 43.8563, 18.4131),
    "Montenegro": ("Podgorica", 42.4304, 19.2594),
    "Albania": ("Tirana", 41.3275, 19.8187),
    "Macedonia": ("Skopje", 41.9973, 21.4280),
    "Moldova": ("Chisinau", 47.0105, 28.8638),
    "Ukraine": ("Kyiv", 50.4501, 30.5234),
    "Belarus": ("Minsk", 53.9006, 27.5590),
    "Russia": ("Moscow", 55.7558, 37.6173),
    "Turkey": ("Ankara", 39.9334, 32.8597),
}

# ======================================================
# HILFSFUNKTIONEN
# ======================================================
def image_to_base64(path: Path) -> str:
    img = Image.open(path).convert("RGBA")
    img = img.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

def meters_to_deg(lat, east, north):
    dlat = north / 111_320
    dlon = east / (111_320 * max(math.cos(math.radians(lat)), 1e-6))
    return dlat, dlon

def spiral(n, step):
    return [
        (step * math.sqrt(i) * math.cos(i * 0.9),
         step * math.sqrt(i) * math.sin(i * 0.9))
        for i in range(n)
    ]

def normalize_status(value) -> str:
    if isinstance(value, str) and value.strip().lower() == "angebot":
        return "Angebot"
    return "Auftrag"

def safe_str(v, fallback="—") -> str:
    if pd.isna(v):
        return fallback
    s = str(v).replace("\xa0", " ").strip()
    return s if s else fallback

# Nur wenn Messtechnik eingebaut == "nein"/false/0/no => Projekt ausblenden
# Bei "ja" oder leer => anzeigen
def hide_if_messtechnik_eingebaut_nein(value) -> bool:
    if pd.isna(value):
        return False  # leer => anzeigen
    v = str(value).replace("\xa0", " ").strip().lower()
    return v in {"nein", "no", "false", "0"}

def normalize_country_for_pgeocode(v) -> str:
    """
    Optional: falls Excel 'Land' hat. Erwartet idealerweise ISO2 ("DE","AT"...).
    Wenn leer/unbekannt -> DE.
    """
    if pd.isna(v):
        return "DE"
    s = str(v).strip()
    if not s:
        return "DE"

    s_low = s.lower()
    mapping = {
        "de": "DE", "deu": "DE", "germany": "DE", "deutschland": "DE",
        "at": "AT", "aut": "AT", "austria": "AT", "österreich": "AT", "osterreich": "AT",
        "ch": "CH", "che": "CH", "switzerland": "CH", "schweiz": "CH",
        "nl": "NL", "nld": "NL", "netherlands": "NL", "holland": "NL",
        "be": "BE", "belgium": "BE", "belgien": "BE",
        "fr": "FR", "france": "FR", "frankreich": "FR",
        "pl": "PL", "poland": "PL", "polen": "PL",
        "cz": "CZ", "czechia": "CZ", "tschechien": "CZ",
        "dk": "DK", "denmark": "DK", "dänemark": "DK", "danemark": "DK",
        "se": "SE", "sweden": "SE", "schweden": "SE",
        "no": "NO", "norway": "NO", "norwegen": "NO",
        "es": "ES", "spain": "ES", "spanien": "ES",
        "pt": "PT", "portugal": "PT",
        "it": "IT", "italy": "IT", "italien": "IT",
    }

    if len(s) == 2 and s.upper().isalpha():
        return s.upper()

    return mapping.get(s_low, "DE")

def load_europe_geojson(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ======================================================
# MAIN
# ======================================================
def main():
    # ---------- MAP (Deutschland als Basis-Zoom) ----------
    states = gpd.read_file(GERMANY_GEOJSON_PATH)
    m = folium.Map(tiles=None, zoom_control=True)

    minx, miny, maxx, maxy = states.total_bounds
    m.fit_bounds([[miny, minx], [maxy, maxx]])

    # ---------- CSS (Map + Sidebar + EU Menu) ----------
    css = f"""
    <style>
    /* ===== Project Pin ===== */
    .pin {{
        width:{PIN_SIZE}px;
        height:{PIN_SIZE}px;
        border-radius:50%;
        border:3px solid var(--status);
        background:#ffffff;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 4px 12px rgba(0,0,0,.22);
        transition: transform .15s ease, box-shadow .2s ease;
    }}
    .pin img {{
        width:{ICON_SIZE}px;
        height:{ICON_SIZE}px;
        display:block;
    }}
    /* Deutlichere Hervorhebung als "grau": blaues Pulse-Glow */
    .pin.active {{
        transform: translateY(-1px);
        animation: pulse 1.25s infinite;
    }}
    @keyframes pulse {{
        0%   {{ box-shadow: 0 0 0 0 rgba(51,154,240,.35), 0 10px 24px rgba(0,0,0,.18); }}
        70%  {{ box-shadow: 0 0 0 16px rgba(51,154,240,0), 0 10px 24px rgba(0,0,0,.18); }}
        100% {{ box-shadow: 0 0 0 0 rgba(51,154,240,0), 0 10px 24px rgba(0,0,0,.18); }}
    }}

    /* ===== Popups ===== */
    .popup {{
        min-width: 460px;
        max-width: 580px;
        font-size: 14px;
        line-height: 1.55;
    }}
    .popup h3 {{
        margin: 0 0 10px 0;
        font-size: 17px;
    }}
    .popup .row {{
        display:flex;
        gap:10px;
        margin: 5px 0;
    }}
    .popup .k {{
        width: 140px;
        color:#495057;
        font-weight:600;
        flex: 0 0 auto;
    }}
    .popup .v {{
        color:#212529;
        flex: 1 1 auto;
        word-break: break-word;
    }}
    .badge {{
        display:inline-block;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
        background: #f1f3f5;
        color: #343a40;
        vertical-align: middle;
    }}
    .badge.auftrag {{ background:#eafaf0; color:#1b5e20; }}
    .badge.angebot {{ background:#fff7e6; color:#8a5a00; }}

    /* ===== DE Capitals ===== */
    .capital {{
        font-size:12px;
        font-weight:700;
        opacity:.82;
        text-shadow:0 0 5px rgba(255,255,255,.95);
        pointer-events:none;
        transform: translate(12px,-12px);
        white-space: nowrap;
    }}

    /* ===== Right Sidebar (Projects) ===== */
    #menu {{
        position:fixed;
        top:20px;
        right:20px;
        z-index:9999;
        width: 300px;
        height: calc(100vh - 40px); /* volle Höhe -> scrollbar */
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 10px 26px rgba(0,0,0,.18);
        overflow: hidden;
        font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
        display:flex;
        flex-direction: column;
    }}
    #menu .header {{
        padding: 12px 14px;
        border-bottom: 1px solid #edf2f7;
        display:flex;
        align-items:center;
        justify-content:space-between;
        flex: 0 0 auto;
    }}
    #menu .header h3 {{
        margin:0;
        font-size: 15px;
    }}
    #menu .content {{
        padding: 12px 14px;
        flex: 1 1 auto;
        min-height: 0;
        display:flex;
        flex-direction: column;
    }}
    .section {{
        margin-bottom: 12px;
        flex: 0 0 auto;
    }}
    .section-title {{
        font-weight: 800;
        font-size: 12px;
        color: #495057;
        text-transform: uppercase;
        letter-spacing: .04em;
        margin: 6px 0 8px 0;
    }}
    .filters {{
        display:grid;
        grid-template-columns: 1fr 1fr;
        gap: 6px 10px;
        font-size: 13px;
    }}
    .filters label {{
        display:flex;
        align-items:center;
        gap:8px;
        cursor:pointer;
        color:#212529;
        user-select:none;
    }}
    .filters input {{
        transform: translateY(1px);
    }}
    .divider {{
        height: 1px;
        background: #edf2f7;
        margin: 10px 0;
        flex: 0 0 auto;
    }}

    #project-list {{
        flex: 1 1 auto;     /* nimmt Resthöhe */
        min-height: 0;
        overflow-y: auto;    /* ✅ scrollbar */
        padding-right: 4px;
        margin-top: 6px;
    }}
    .project-item {{
        padding: 8px 10px;
        border-radius: 10px;
        cursor: pointer;
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
        border: 1px solid transparent;
    }}
    .project-item:hover {{
        background:#f8f9fa;
    }}
    .project-item.active {{
        background:#eef6ff;
        border-color:#d0ebff;
    }}
    .project-name {{
        font-weight: 700;
        font-size: 13px;
        color:#212529;
        line-height:1.2;
    }}
    .project-meta {{
        font-size: 12px;
        color:#495057;
        display:flex;
        align-items:center;
        gap:8px;
        white-space: nowrap;
        flex-wrap: wrap;
    }}
    .meta-status {{
        display:inline-flex;
        align-items:center;
        gap:6px;
    }}
    .status-dot-list {{
        width:8px;
        height:8px;
        border-radius:50%;
        display:inline-block;
        background: var(--statuscolor);
        box-shadow: 0 0 0 2px rgba(0,0,0,.06);
    }}
    .small-pill {{
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 999px;
        background:#f1f3f5;
        color:#343a40;
        border: 1px solid #e9ecef;
        flex: 0 0 auto;
    }}

    /* ===== Bottom-left Status Legend ===== */
    #legend {{
        position:fixed;
        bottom:20px;
        left:20px;
        background:white;
        padding:12px 14px;
        border-radius:10px;
        box-shadow:0 6px 18px rgba(0,0,0,.25);
        font-size:13px;
        z-index:9999;
    }}

    /* ===== Left Europe Country Menu (default off) ===== */
    #country-menu {{
        position:fixed;
        top:20px;
        left:20px;
        z-index:9998;
        width: 280px;
        max-width: calc(100vw - 40px);
        height: calc(100vh - 140px);
        background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%);
        border-radius: 16px;
        box-shadow: 0 20px 60px rgba(0,0,0,.15);
        overflow: hidden;
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
        display: none;
        flex-direction: column;
        border: 1px solid rgba(59,130,246,.1);
    }}
    #country-menu .header {{
        padding: 16px 18px;
        border-bottom: 2px solid rgba(59,130,246,.1);
        display:flex;
        align-items:center;
        justify-content:space-between;
        flex: 0 0 auto;
        background: linear-gradient(to right, rgba(59,130,246,.05), transparent);
    }}
    #country-menu .header h3 {{
        margin:0;
        font-size: 16px;
        font-weight: 700;
        color: #1e293b;
        letter-spacing: -0.3px;
    }}
    #country-menu .content {{
        padding: 12px;
        flex: 1 1 auto;
        min-height: 0;
        display:flex;
        flex-direction: column;
    }}
    #country-list {{
        flex: 1 1 auto;
        min-height: 0;
        overflow-y: auto;
        padding-right: 6px;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        align-content: start;
    }}
    #country-list::-webkit-scrollbar {{
        width: 6px;
    }}
    #country-list::-webkit-scrollbar-track {{
        background: transparent;
    }}
    #country-list::-webkit-scrollbar-thumb {{
        background: rgba(100,116,139,.3);
        border-radius: 3px;
    }}
    #country-list::-webkit-scrollbar-thumb:hover {{
        background: rgba(100,116,139,.5);
    }}
    .country-item {{
        padding: 10px 12px;
        border-radius: 10px;
        cursor: pointer;
        display:flex;
        align-items:center;
        justify-content:center;
        text-align: center;
        gap:6px;
        border: 2px solid #e2e8f0;
        background: #ffffff;
        font-size: 12px;
        font-weight: 500;
        color: #334155;
        transition: all 0.2s ease;
        min-height: 40px;
    }}
    .country-item:hover {{
        border-color: #3b82f6;
        background: #f0f7ff;
        color: #1e40af;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(59,130,246,.15);
    }}
    .country-item.active {{
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: #ffffff;
        border-color: #1e40af;
        box-shadow: 0 8px 20px rgba(59,130,246,.3);
    }}
    .country-item.active:hover {{
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(59,130,246,.35);
    }}

    /* EU capital label (only when country visible) */
    .eu-capital {{
        font-size: 12px;
        font-weight: 800;
        color:#1f2937;
        opacity:.9;
        text-shadow:0 0 5px rgba(255,255,255,.95);
        pointer-events:none;
        transform: translate(12px,-12px);
        white-space: nowrap;
    }}
    .eu-capital .dot {{
        margin-right:6px;
        color:#364fc7;
    }}
    </style>
    """
    m.get_root().header.add_child(Element(css))

    # ---------- Deutschland Fläche ----------
    folium.GeoJson(
        states.to_json(),
        style_function=lambda _: {
            "color": "#555",
            "weight": 1,
            "fillColor": "#f8f9fa",
            "fillOpacity": 0.95,
        },
        control=False,
    ).add_to(m)

    # ---------- DE Hauptstädte (nur Labels, ohne Koordinaten-Offset) ----------
    for city, (lat, lon) in GER_STATE_CAPITALS.items():
        folium.Marker(
            [lat, lon],
            icon=folium.DivIcon(html=f"<div class='capital'>● {city}</div>", icon_anchor=(0, 10)),
        ).add_to(m)

    # ======================================================
    # PROJEKTE - Lade Daten (Excel oder Datenbank)
    # ======================================================
    print(f"\n📊 Datenquelle: {get_data_source().upper()}")
    
    try:
        projects_dict = load_projects()
    except Exception as e:
        print(f"❌ Fehler beim Laden der Projekte: {e}")
        print(f"   Fallback auf Excel: {EXCEL_PATH}")
        try:
            xls = pd.ExcelFile(EXCEL_PATH)
            projects_dict = {sheet: pd.read_excel(xls, sheet_name=sheet) for sheet in xls.sheet_names}
        except Exception as e2:
            print(f"❌ Auch Excel-Fallback fehlgeschlagen: {e2}")
            projects_dict = {}

    pid_counter = 0

    for sheet, df in projects_dict.items():
        if sheet not in CATEGORY_COLOR:
            continue
        
        if df.empty:
            continue

        required = {"Art", "VN", "Name", "Status", "PLZ"}
        if not required.issubset(df.columns):
            print(f"⚠ Sheet '{sheet}' hat nicht alle erforderlichen Spalten: {required}")
            continue

        has_kunde = "Kunde" in df.columns
        has_messtechnik = "Messtechnik eingebaut" in df.columns
        has_land = "Land" in df.columns

        df["PLZ"] = (
            df["PLZ"].astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.strip()
        )

        # Optional: Land -> country code
        if has_land:
            df["_CC"] = df["Land"].apply(normalize_country_for_pgeocode)
        else:
            df["_CC"] = "DE"

        # PLZ in vielen Ländern nicht immer 5-stellig – für DE ist das wichtig
        # Wir zfill nur bei DE, sonst lassen wir es so.
        df["_PLZ"] = df["PLZ"].copy()
        df.loc[df["_CC"] == "DE", "_PLZ"] = df.loc[df["_CC"] == "DE", "_PLZ"].astype(str).str.zfill(5)

        # Geocoding: pro CountryCode gruppieren (pgeocode)
        lat_all = [None] * len(df)
        lon_all = [None] * len(df)

        for cc, idxs in df.groupby("_CC").groups.items():
            try:
                geo = pgeocode.Nominatim(cc)
                codes = df.loc[idxs, "_PLZ"].astype(str).tolist()
                loc = geo.query_postal_code(codes)
                lat_vals = loc["latitude"].values
                lon_vals = loc["longitude"].values
                for j, ridx in enumerate(idxs):
                    lat_all[ridx] = lat_vals[j]
                    lon_all[ridx] = lon_vals[j]
            except Exception:
                # Fallback: nichts setzen (wird später dropna)
                continue

        df["lat"] = lat_all
        df["lon"] = lon_all
        df = df.dropna(subset=["lat", "lon"]).reset_index(drop=True)

        offsets = spiral(len(df), JITTER_STEP_M)

        for i, row in df.iterrows():
            # Messtechnik eingebaut: wenn "nein" => ausblenden, sonst anzeigen
            if has_messtechnik and hide_if_messtechnik_eingebaut_nein(row["Messtechnik eingebaut"]):
                continue

            plant = safe_str(row["Art"], "").replace("\xa0", "").strip()
            if plant not in PLANT_ICONS:
                continue

            status = normalize_status(row["Status"])
            status_color = STATUS_RING_COLOR[status]

            name = safe_str(row["Name"])
            vn = safe_str(row["VN"])
            kunde = safe_str(row["Kunde"]) if has_kunde else "—"

            lat = float(row["lat"])
            lon = float(row["lon"])

            img = image_to_base64(PLANT_ICONS[plant])
            dlat, dlon = meters_to_deg(lat, offsets[i][0], offsets[i][1])

            pid = f"proj-{pid_counter}"
            pid_counter += 1

            badge_class = "angebot" if status == "Angebot" else "auftrag"
            status_badge = f"<span class='badge {badge_class}'>{status}</span>"

            popup_html = f"""
            <div class="popup">
              <h3>{name}</h3>
              <div class="row"><div class="k">Kunde</div><div class="v">{kunde}</div></div>
              <div class="row"><div class="k">VN</div><div class="v">{vn}</div></div>
              <div class="row"><div class="k">Status</div><div class="v">{status_badge}</div></div>
              <div class="row"><div class="k">Kategorie</div><div class="v">{sheet}</div></div>
              <div class="row"><div class="k">Kraftwerksart</div><div class="v">{plant}</div></div>
              <div class="row"><div class="k">PLZ</div><div class="v">{safe_str(row['PLZ'])}</div></div>
            </div>
            """

            country = safe_str(row["_CC"], "DE") if "_CC" in row else "DE"

            icon_html = f"""
            <div class="pin project-marker"
                 data-id="{pid}"
                 data-category="{sheet}"
                 data-plant="{plant}"
                 data-name="{name}"
                 data-vn="{vn}"
                 data-kunde="{kunde}"
                 data-status="{status}"
                 data-country="{country}"
                 data-lat="{lat + dlat}"
                 data-lon="{lon + dlon}"
                 style="--status:{status_color}">
                <img src="{img}">
            </div>
            """

            folium.Marker(
                [lat + dlat, lon + dlon],
                popup=folium.Popup(popup_html, max_width=580),
                icon=folium.DivIcon(
                    html=icon_html,
                    icon_size=(PIN_SIZE, PIN_SIZE),
                    icon_anchor=(PIN_SIZE // 2, PIN_SIZE // 2),
                ),
            ).add_to(m)

    # ======================================================
    # RIGHT SIDEBAR (Filter + Projektliste + Highlight + Popup open robust)
    # ======================================================
    menu_html = """
    <div id="menu">
      <div class="header">
        <h3>Projekte</h3>
        <span class="small-pill" id="visible-count">—</span>
      </div>

      <div class="content">
        <div class="section">
          <div class="section-title">Filter Kategorie</div>
          <div class="filters">
            <label><input type="checkbox" class="f-cat" value="EZA" checked> EZA</label>
            <label><input type="checkbox" class="f-cat" value="EZAR" checked> EZAR</label>
            <label><input type="checkbox" class="f-cat" value="OSNV" checked> OSNV</label>
            <label><input type="checkbox" class="f-cat" value="EZE" checked> EZE</label>
          </div>
        </div>

        <div class="section">
          <div class="section-title">Filter Kraftwerksart</div>
          <div class="filters">
            <label><input type="checkbox" class="f-plant" value="Batterie" checked> Batterie</label>
            <label><input type="checkbox" class="f-plant" value="Wind" checked> Wind</label>
            <label><input type="checkbox" class="f-plant" value="PV" checked> PV</label>
            <label><input type="checkbox" class="f-plant" value="BHKW" checked> BHKW</label>
            <label><input type="checkbox" class="f-plant" value="HKW" checked> HKW</label>
            <label><input type="checkbox" class="f-plant" value="Wasser" checked> Wasser</label>
            <label><input type="checkbox" class="f-plant" value="EZAR" checked> EZAR</label>
          </div>
        </div>

        <div class="divider"></div>

        <div class="section-title">Projektliste</div>
        <div id="project-list"></div>
      </div>
    </div>

    <script>
    const STATUS_COLORS = {
      "Angebot": "__COLOR_ANGEBOT__",
      "Auftrag": "__COLOR_AUFTRAG__"
    };

    function getLeafletMapInstance() {
      for (var k in window) {
        var v = window[k];
        if (v && typeof v === "object" && typeof v.setView === "function" && typeof v.panTo === "function" && v._leaflet_id) {
          return v;
        }
      }
      return null;
    }

    function markerIconElement(markerDiv) {
      return markerDiv.closest('.leaflet-marker-icon');
    }

    function setMarkerVisible(markerDiv, visible) {
      var icon = markerIconElement(markerDiv);
      if (!icon) return;
      icon.style.display = visible ? '' : 'none';
    }

    function isMarkerVisible(markerDiv) {
      var icon = markerIconElement(markerDiv);
      if (!icon) return false;
      return icon.style.display !== 'none';
    }

    function clearActive() {
      document.querySelectorAll('.pin.active').forEach(function(p){ p.classList.remove('active'); });
      document.querySelectorAll('.project-item.active').forEach(function(i){ i.classList.remove('active'); });
    }

    function sortKeyName(s) {
      if (!s) return "";
      return s
        .replace(/\\u00A0/g, " ")
        .replace(/\\s+/g, " ")
        .trim()
        .toLocaleLowerCase("de-DE");
    }

    // Robust: finde Leaflet Marker-Objekt über DOM (popup öffnen zuverlässig auch nach Drag)
    function findLeafletMarkerById(pid) {
      var map = getLeafletMapInstance();
      if (!map || !map._layers) return null;

      for (var id in map._layers) {
        var layer = map._layers[id];
        if (!layer) continue;
        if (layer instanceof L.Marker && layer._icon) {
          var el = layer._icon.querySelector('.project-marker[data-id="' + pid + '"]');
          if (el) return layer;
        }
      }
      return null;
    }

    function buildProjectList() {
      var list = document.getElementById('project-list');
      var count = document.getElementById('visible-count');
      if (!list) return;

      list.innerHTML = '';

      var markers = Array.from(document.querySelectorAll('.project-marker'))
        .filter(function(m){ return isMarkerVisible(m); });

      markers.sort(function(a,b){
        return sortKeyName(a.dataset.name).localeCompare(sortKeyName(b.dataset.name), "de-DE");
      });

      markers.forEach(function(m){
        var item = document.createElement('div');
        item.className = 'project-item';
        item.dataset.target = m.dataset.id;

        var left = document.createElement('div');
        left.style.minWidth = '0';

        var name = document.createElement('div');
        name.className = 'project-name';
        name.textContent = m.dataset.name || 'Unbenannt';

        var meta = document.createElement('div');
        meta.className = 'project-meta';

        var vn = document.createElement('span');
        vn.textContent = m.dataset.vn ? ('VN ' + m.dataset.vn) : '';

        var statusWrap = document.createElement('span');
        statusWrap.className = 'meta-status';

        var statusText = (m.dataset.status || '').trim() || 'Auftrag';
        var dot = document.createElement('span');
        dot.className = 'status-dot-list';
        dot.style.setProperty('--statuscolor', STATUS_COLORS[statusText] || STATUS_COLORS["Auftrag"]);

        var statusLabel = document.createElement('span');
        statusLabel.textContent = statusText;

        statusWrap.appendChild(dot);
        statusWrap.appendChild(statusLabel);

        if (vn.textContent) meta.appendChild(vn);
        meta.appendChild(statusWrap);

        left.appendChild(name);
        left.appendChild(meta);

        var pill = document.createElement('span');
        pill.className = 'small-pill';
        pill.textContent = m.dataset.category || '';

        item.appendChild(left);
        item.appendChild(pill);

        item.addEventListener('click', function(){
          clearActive();
          item.classList.add('active');
          m.classList.add('active');

          var map = getLeafletMapInstance();
          var lat = parseFloat(m.dataset.lat);
          var lon = parseFloat(m.dataset.lon);

          if (map && !isNaN(lat) && !isNaN(lon)) {
            var z = Math.max(map.getZoom(), 7);
            map.setView([lat, lon], z, { animate: true });
          }

          // ✅ Popup zuverlässig öffnen
          var leaf = findLeafletMarkerById(m.dataset.id);
          if (leaf && typeof leaf.openPopup === "function") {
            leaf.openPopup();
          }
        });

        list.appendChild(item);
      });

      if (count) count.textContent = String(markers.length);
    }

    function applyFiltersAndRefreshList() {
      var cats = Array.from(document.querySelectorAll('.f-cat:checked')).map(function(e){ return e.value; });
      var plants = Array.from(document.querySelectorAll('.f-plant:checked')).map(function(e){ return e.value; });

      document.querySelectorAll('.project-marker').forEach(function(m){
        var countryCode = m.dataset.country || 'DE';
        var countryVisible = (countryCode === 'DE') || EU_VISIBLE.has(getCountryNameFromCode(countryCode));
        var filterPass = cats.includes(m.dataset.category) && plants.includes(m.dataset.plant);
        var show = filterPass && countryVisible;
        setMarkerVisible(m, show);
      });

      var active = document.querySelector('.pin.active');
      if (active && !isMarkerVisible(active)) {
        clearActive();
      }

      buildProjectList();
    }
    
    function getCountryNameFromCode(code) {
      // Umkehrung: Code -> Name
      const codeToName = {
        'AT': 'Austria', 'BE': 'Belgium', 'CZ': 'Czechia', 'DK': 'Denmark',
        'FR': 'France', 'LU': 'Luxembourg', 'NL': 'Netherlands', 'PL': 'Poland',
        'CH': 'Switzerland'
      };
      return codeToName[code] || 'Germany';
    }

    function initSidebar() {
      document.querySelectorAll('.f-cat, .f-plant').forEach(function(cb){
        cb.addEventListener('change', applyFiltersAndRefreshList);
      });
      applyFiltersAndRefreshList();
    }

    function waitForMarkersThenInit(retries) {
      if (retries === undefined) retries = 60;
      var markers = document.querySelectorAll('.project-marker');
      if (markers && markers.length > 0) {
        initSidebar();
        return;
      }
      if (retries <= 0) {
        initSidebar();
        return;
      }
      setTimeout(function(){ waitForMarkersThenInit(retries - 1); }, 150);
    }

    document.addEventListener('DOMContentLoaded', function(){
      waitForMarkersThenInit();
    });
    </script>
    """
    menu_html = (
        menu_html
        .replace("__COLOR_ANGEBOT__", STATUS_RING_COLOR["Angebot"])
        .replace("__COLOR_AUFTRAG__", STATUS_RING_COLOR["Auftrag"])
    )
    m.get_root().html.add_child(Element(menu_html))

    # ======================================================
    # STATUS-LEGENDE (unten links)
    # ======================================================
    legend_html = """
    <div id="legend">
      <b>Status (Ring)</b><br>
      <span style="color:#e9c46a">●</span> Angebot<br>
      <span style="color:#2f9e44">●</span> Auftrag
    </div>
    """
    m.get_root().html.add_child(Element(legend_html))

    # ======================================================
    # EUROPA LÄNDER (direct JS embedding, NOT via Folium layers)
    # ======================================================
    europe_data = load_europe_geojson(EUROPE_GEOJSON_PATH)
    europe_countries = {}  # country_name -> geojson feature collection

    if europe_data:
        name_field = "ADMIN"

        for ft in europe_data.get("features", []):
            props = ft.get("properties") or {}
            cname = str(props.get(name_field, "")).strip()
            if not cname:
                continue
            # Nur europäische Länder + Deutschland ausschließen
            if cname not in EUROPEAN_COUNTRIES:
                continue
            if cname.lower() in {"germany", "deutschland", "bundesrepublik deutschland"}:
                continue  # Deutschland ausschließen
            europe_countries.setdefault(cname, []).append(ft)

        print(f"📍 Europa: {len(europe_countries)} Länder geladen (gefiltert)")
        print(f"   Nachbarländer: {', '.join(sorted([c for c in europe_countries.keys() if c in GER_NEIGHBORS]))}")

    if europe_countries:
        # Erstelle GeoJSON Daten als JavaScript-Objekt
        eu_data_js_lines = []
        country_names_sorted = sorted(europe_countries.keys(), key=lambda s: s.casefold())

        for cname in country_names_sorted:
            features = europe_countries[cname]
            fc = {"type": "FeatureCollection", "features": features}
            geojson_json = json.dumps(fc, ensure_ascii=False)
            eu_data_js_lines.append(f'  {json.dumps(cname)}: {geojson_json}')

        eu_data_js = "{\n" + ",\n".join(eu_data_js_lines) + "\n}"

        # Nachbarländer Liste für JavaScript
        neighbor_names_js = json.dumps(sorted([c for c in country_names_sorted if c in GER_NEIGHBORS]))
        
        items_html = "\n".join(
            f"""<button class="country-item" data-country="{c}" title="Zeige {c}">
                    {c}
                </button>"""
            for c in country_names_sorted
        )

        capitals_json = {
            k.lower(): {"city": v[0], "lat": v[1], "lon": v[2]}
            for k, v in EU_CAPITALS.items()
        }
        
        # Länder-Farben für JavaScript
        country_colors_json = {c: COUNTRY_COLORS.get(c, "#e5f5e0") for c in country_names_sorted}

        europe_menu_html = """
        <div id="country-menu">
          <div class="header">
            <h3>🌍 Europa</h3>
            <button id="country-menu-close" style="background:none;border:none;font-size:20px;cursor:pointer;color:#64748b;padding:0;width:24px;height:24px;display:flex;align-items:center;justify-content:center;border-radius:6px;transition:all 0.2s;" title="Schließen">✕</button>
          </div>
          <div class="content">
            <button id="neighbors-button" style="width:100%;padding:10px;background:linear-gradient(135deg,#10b981 0%,#059669 100%);color:white;border:none;border-radius:8px;font-weight:600;cursor:pointer;margin-bottom:12px;transition:all 0.2s;box-shadow:0 4px 12px rgba(16,185,129,.2);" title="Nachbarländer anzeigen">
              🇩🇪 Nachbarländer
            </button>
            <div id="country-list">
              {items}
            </div>
            <div style="margin-top:8px;padding:8px;background:rgba(59,130,246,.05);border-radius:8px;border-left:3px solid #3b82f6;">
              <div style="font-size:11px;color:#475569;line-height:1.5;font-weight:500;">
                💡 Länder anklicken zum Einblenden
              </div>
            </div>
          </div>
        </div>

        <div id="country-menu-toggle" style="position:fixed;top:20px;left:20px;z-index:9999;">
          <button id="open-country-menu" style="background:linear-gradient(135deg,#3b82f6 0%,#2563eb 100%);color:white;border:none;padding:12px 18px;border-radius:12px;font-size:14px;font-weight:600;cursor:pointer;box-shadow:0 8px 20px rgba(59,130,246,.3);transition:all 0.3s ease;display:flex;align-items:center;gap:8px;" title="Europa anzeigen">
            🌍 Europa
          </button>
        </div>

        <script>
        // Globale Variablen für Land-Filterung (müssen global sein für beide Scripts)
        window.EU_VISIBLE = new Set();
        window.COUNTRY_NAME_TO_CODE = {{
          'Austria': 'AT', 'Belgium': 'BE', 'Czechia': 'CZ', 'Denmark': 'DK',
          'France': 'FR', 'Luxembourg': 'LU', 'Netherlands': 'NL', 'Poland': 'PL',
          'Switzerland': 'CH'
        }};
        
        window.getCountryCode = function(countryName) {{
          return window.COUNTRY_NAME_TO_CODE[countryName] || 'DE';
        }};
        
        window.getCountryNameFromCode = function(code) {{
          const codeToName = {{
            'AT': 'Austria', 'BE': 'Belgium', 'CZ': 'Czechia', 'DK': 'Denmark',
            'FR': 'France', 'LU': 'Luxembourg', 'NL': 'Netherlands', 'PL': 'Poland',
            'CH': 'Switzerland'
          }};
          return codeToName[code] || 'Germany';
        }};
        
        // Toggle Menu öffnen/schließen
        document.getElementById('open-country-menu').addEventListener('click', function(){{
          var menu = document.getElementById('country-menu');
          var toggle = document.getElementById('country-menu-toggle');
          menu.style.display = 'flex';
          toggle.style.display = 'none';
        }});
        
        function getLeafletMapInstance() {{
          for (var k in window) {{
            var v = window[k];
            if (!v) continue;
            if (typeof v === "object" && typeof v.setView === "function" && typeof v.panTo === "function" && v._leaflet_id) {{
              return v;
            }}
          }}
          return null;
        }}

        // EU-Länder GeoJSON Daten
        const EU_DATA = {eu_data_js};
        const NEIGHBOR_NAMES = {neighbor_names_js};
        const COUNTRY_COLORS = {country_colors_json};
        
        // Layer-Objekte, die wir dynamisch erstellen
        const EU_LAYERS = {{}};
        const EU_CAPITAL_MARKERS = {{}};
        
        // Erstelle Layer beim Start
        function initEULayers() {{
          const map = getLeafletMapInstance();
          if (!map) {{
            console.warn('Map nicht gefunden');
            return;
          }}

          for (const countryName in EU_DATA) {{
            const geoData = EU_DATA[countryName];
            const fillColor = COUNTRY_COLORS[countryName] || '#e5f5e0';
            const layer = L.geoJSON(geoData, {{
              style: function() {{
                return {{
                  color: '#333333',
                  weight: 1.5,
                  fillColor: fillColor,
                  fillOpacity: 0.6
                }};
              }},
              onEachFeature: function(feature, layer) {{
                layer.on('mouseover', function() {{
                  layer.setStyle({{ weight: 2.5, fillOpacity: 0.8 }});
                }});
                layer.on('mouseout', function() {{
                  layer.setStyle({{ weight: 1.5, fillOpacity: 0.6 }});
                }});
              }}
            }});
            EU_LAYERS[countryName] = layer;
          }}
          console.log('✓ EU-Layer erstellt:', Object.keys(EU_LAYERS).length);
        }}

        const EU_CAPITALS = {capitals};
        
        // Mapping: Ländernamen -> Länder-Codes (ISO2)
        const COUNTRY_NAME_TO_CODE = window.COUNTRY_NAME_TO_CODE;
        
        function getCountryCode(countryName) {{
          return window.getCountryCode(countryName);
        }}

        function addCapital(countryName) {{
          const map = getLeafletMapInstance();
          if (!map) return;

          const key = countryName.toLowerCase().trim();
          const info = EU_CAPITALS[key];
          if (!info) return;

          if (!EU_CAPITAL_MARKERS[key]) {{
            const html = `<div class="eu-capital"><span class="dot">●</span>${{info.city}}</div>`;
            const icon = L.divIcon({{ html: html, className: "", iconAnchor: [0, 10] }});
            EU_CAPITAL_MARKERS[key] = L.marker([info.lat, info.lon], {{ icon }});
          }}
          EU_CAPITAL_MARKERS[key].addTo(map);
        }}

        function removeCapital(countryName) {{
          const map = getLeafletMapInstance();
          if (!map) return;

          const key = countryName.toLowerCase().trim();
          const m = EU_CAPITAL_MARKERS[key];
          if (m && map.hasLayer(m)) map.removeLayer(m);
        }}

        function addCapital(countryName) {{
          const map = getLeafletMapInstance();
          if (!map) return;

          const key = countryName.toLowerCase().trim();
          const info = EU_CAPITALS[key];
          if (!info) return;

          if (!EU_CAPITAL_MARKERS[key]) {{
            const html = `<div class="eu-capital"><span class="dot">●</span>${{info.city}}</div>`;
            const icon = L.divIcon({{ html: html, className: "", iconAnchor: [0, 10] }});
            EU_CAPITAL_MARKERS[key] = L.marker([info.lat, info.lon], {{ icon }});
          }}
          EU_CAPITAL_MARKERS[key].addTo(map);
        }}

        function removeCapital(countryName) {{
          const map = getLeafletMapInstance();
          if (!map) return;

          const key = countryName.toLowerCase().trim();
          const m = EU_CAPITAL_MARKERS[key];
          if (m && map.hasLayer(m)) map.removeLayer(m);
        }}

        function showCountry(countryName) {{
          const map = getLeafletMapInstance();
          if (!map) {{
            console.error('Map nicht gefunden');
            return;
          }}

          const layer = EU_LAYERS[countryName];
          if (!layer) {{
            console.error('Layer nicht gefunden für:', countryName);
            return;
          }}

          if (!map.hasLayer(layer)) {{
            map.addLayer(layer);
          }}
          
          addCapital(countryName);
          window.EU_VISIBLE.add(countryName);
          
          // Zeige auch Projekte in diesem Land
          const countryCode = getCountryCode(countryName);
          document.querySelectorAll('.project-marker[data-country="' + countryCode + '"]').forEach(function(markerDiv) {{
            if (markerDiv) {{
              setMarkerVisible(markerDiv, true);
            }}
          }});
          
          // Aktualisiere Projektliste
          buildProjectList();
        }}

        function hideCountry(countryName) {{
          const map = getLeafletMapInstance();
          if (!map) return;

          const layer = EU_LAYERS[countryName];
          if (!layer) return;

          if (map.hasLayer(layer)) map.removeLayer(layer);
          removeCapital(countryName);
          window.EU_VISIBLE.delete(countryName);
          
          // Verstecke auch Projekte in diesem Land
          const countryCode = getCountryCode(countryName);
          document.querySelectorAll('.project-marker[data-country="' + countryCode + '"]').forEach(function(markerDiv) {{
            if (markerDiv) {{
              setMarkerVisible(markerDiv, false);
            }}
          }});
          
          // Aktualisiere Projektliste
          buildProjectList();
        }}

        function toggleCountry(countryName) {{
          if (window.EU_VISIBLE.has(countryName)) {{
            hideCountry(countryName);
          }} else {{
            showCountry(countryName);
          }}
        }}

        function initCountryMenu() {{
          document.querySelectorAll("#country-list .country-item").forEach(function(item) {{
            item.addEventListener("click", function() {{
              const c = item.dataset.country;
              toggleCountry(c);
              item.classList.toggle("active", window.EU_VISIBLE.has(c));
            }});
          }});

          // Nachbarländer Button
          document.getElementById('neighbors-button').addEventListener('click', function() {{
            NEIGHBOR_NAMES.forEach(function(country) {{
              if (!window.EU_VISIBLE.has(country)) {{
                showCountry(country);
                var btn = document.querySelector('[data-country="' + country + '"]');
                if (btn) btn.classList.add('active');
              }}
            }});
          }});

          // Schließen-Button
          var closeBtn = document.getElementById('country-menu-close');
          var openContainer = document.getElementById('country-menu-toggle');
          if (closeBtn) {{
            closeBtn.addEventListener('click', function() {{
              var el = document.getElementById('country-menu');
              if (!el) return;
              el.style.display = 'none';
              if (openContainer) openContainer.style.display = 'block';
            }});
          }}
        }}

        document.addEventListener("DOMContentLoaded", function() {{
          setTimeout(function() {{
            initEULayers();
            initCountryMenu();
            
            // Automatisch Nachbarländer beim Laden anzeigen (damit Projekte dort sichtbar sind)
            NEIGHBOR_NAMES.forEach(function(country) {{
              showCountry(country);
              var btn = document.querySelector('[data-country="' + country + '"]');
              if (btn) btn.classList.add('active');
            }});
            
            console.log('✓ Nachbarländer automatisch geladen:', NEIGHBOR_NAMES.join(', '));
          }}, 300);
        }});
        </script>
        """.format(items=items_html, eu_data_js=eu_data_js, neighbor_names_js=neighbor_names_js, 
                   capitals=json.dumps(capitals_json, ensure_ascii=False), 
                   country_colors_json=json.dumps(country_colors_json, ensure_ascii=False))
        m.get_root().html.add_child(Element(europe_menu_html))

    # ---------- SAVE ----------
    m.save(OUT_HTML)
    print("✅ Karte erfolgreich erstellt:", OUT_HTML)

if __name__ == "__main__":
    main()

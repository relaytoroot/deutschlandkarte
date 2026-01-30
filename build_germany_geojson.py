import os
import urllib.request
import zipfile
import geopandas as gpd

# Ziel-Dateien / Ordner
DATA_DIR = "data"
ZIP_PATH = os.path.join(DATA_DIR, "ne_10m_admin_1_states_provinces.zip")
EXTRACT_DIR = os.path.join(DATA_DIR, "ne_admin1_extract")
OUT_GEOJSON = "germany.geojson"

# Natural Earth Admin-1 (10m) ZIP (enthält Bundesländer/Provinzen weltweit)
NE_ZIP_URL = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip"

def download_if_missing():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(ZIP_PATH) and os.path.getsize(ZIP_PATH) > 0:
        print(f"OK: ZIP existiert schon: {ZIP_PATH}")
        return

    print("Lade Natural Earth Admin-1 ZIP herunter...")
    urllib.request.urlretrieve(NE_ZIP_URL, ZIP_PATH)
    print(f"Download fertig: {ZIP_PATH}")

def extract_zip():
    # Zielordner frisch machen
    if os.path.exists(EXTRACT_DIR):
        # nicht zwingend löschen, aber sauberer:
        for root, dirs, files in os.walk(EXTRACT_DIR, topdown=False):
            for f in files:
                os.remove(os.path.join(root, f))
            for d in dirs:
                os.rmdir(os.path.join(root, d))
    os.makedirs(EXTRACT_DIR, exist_ok=True)

    print("Entpacke ZIP...")
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        z.extractall(EXTRACT_DIR)

    # Suche die .shp Datei im entpackten Ordner
    shp_files = [f for f in os.listdir(EXTRACT_DIR) if f.lower().endswith(".shp")]
    if not shp_files:
        raise FileNotFoundError("Keine .shp Datei im ZIP gefunden.")
    shp_path = os.path.join(EXTRACT_DIR, shp_files[0])
    print(f"Shapefile gefunden: {shp_path}")
    return shp_path

def filter_germany(shp_path: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(shp_path)

    # Typische Spalten in Natural Earth Admin-1:
    # - "admin" = Ländername (z.B. "Germany")  :contentReference[oaicite:2]{index=2}
    # - "iso_a2" = DE
    # - "name"  = Bundeslandname
    cols = set(gdf.columns.str.lower())

    if "admin" in cols:
        germany = gdf[gdf["admin"] == "Germany"].copy()
    elif "iso_a2" in cols:
        germany = gdf[gdf["iso_a2"] == "DE"].copy()
    else:
        raise KeyError(f"Unerwartete Spalten. Vorhanden: {list(gdf.columns)}")

    if len(germany) == 0:
        raise ValueError("Filter hat 0 Treffer ergeben. (Deutschland nicht gefunden)")

    # GeoJSON ist üblicherweise EPSG:4326 (lat/lon)
    if germany.crs is None:
        germany = germany.set_crs(epsg=4326)
    else:
        germany = germany.to_crs(epsg=4326)

    return germany

def main():
    download_if_missing()
    shp_path = extract_zip()
    germany_states = filter_germany(shp_path)

    # Export als GeoJSON (enthält mehrere Features = Bundesländer)
    germany_states.to_file(OUT_GEOJSON, driver="GeoJSON")
    print(f"✅ Fertig: {OUT_GEOJSON}")
    print(f"Features (Bundesländer): {len(germany_states)}")
    print("Spalten:", list(germany_states.columns))

if __name__ == "__main__":
    main()

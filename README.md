# Deutschlandkarte – Projekte

## Struktur
- `src/app/main.py` →  Map-Code (Folium)
- `assets/germany.geojson` → Deutschland-GeoJSON
- `assets/icons/` → PNG Icons
- `data/Datenmuster_OSNV_Maps.xlsx` → Excel Datenquelle
- `config/config.yaml` → Pfade/Settings (später erweiterbar)
- `scripts/run.sh` → Start (Git Bash / Linux / WSL)

## Setup (empfohlen)
```bash
cd deutschlandkarte
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/run.sh

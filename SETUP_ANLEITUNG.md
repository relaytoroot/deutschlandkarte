# 🗺️ DeutschlandKarte - Setup Anleitung

## Schnellstart - Zuhause (Excel)

```bash
# Repository klonen
git clone <url> deutschlandkarte
cd deutschlandkarte

# Virtual Environment
python3 -m venv .venv
source .venv/bin/activate  # oder: .venv\Scripts\activate (Windows)

# Dependencies
pip install -r requirements.txt

# Starten
.venv/bin/python ./src/app/main.py
```

✅ Fertig! Karte unter `deutschland_projekte.html`

---

## Im Büro - Mit Datenbank

### 1️⃣ **Repository klonen & vorbereiten**

```bash
git clone <url> deutschlandkarte
cd deutschlandkarte

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### 2️⃣ **`.env` Datei erstellen**

Kopiere `.env.example` zu `.env`:

```bash
cp .env.example .env
```

### 3️⃣ **`.env` mit Datenbank-Credentials ausfüllen**

Öffne `.env` und bearbeite:

```env
# Ändere:
DATA_SOURCE=excel

# Zu:
DATA_SOURCE=database

# Und setze DATABASE_URL (je nach DB-Typ):

# PostgreSQL:
DATABASE_URL=postgresql://username:password@db-server.local:5432/database_name

# MySQL:
DATABASE_URL=mysql+pymysql://username:password@db-server.local:3306/database_name

# MS SQL Server:
DATABASE_URL=mssql+pyodbc://username:password@server_name/database_name?driver=ODBC+Driver+17+for+SQL+Server

# SQLite (für Tests):
DATABASE_URL=sqlite:///./test.db
```

### 4️⃣ **Optional: DB-Spezifische Treiber installieren**

Je nach Datenbank-Typ:

```bash
# PostgreSQL (normalerweise schon in requirements.txt)
pip install psycopg2-binary

# MySQL
pip install pymysql

# MS SQL Server
pip install pyodbc
# + ODBC Driver 17 for SQL Server auf dem System installieren

# SQLite (kein Install nötig, in Python integriert)
```

### 5️⃣ **Testen**

```bash
# Datenbank-Verbindung testen
.venv/bin/python -c "from src.app.data_loader import load_projects; load_projects()"

# Sollte so aussehen:
# 🔗 Verbinde mit Datenbank...
# ✓ Datenbankverbindung erfolgreich
# ✓ Tabelle 'EZA': X Zeilen
# etc.
```

### 6️⃣ **Karte generieren**

```bash
.venv/bin/python ./src/app/main.py
```

✅ Fertig! Karte unter `deutschland_projekte.html`

---

## 🔧 Erweiterte Konfiguration

### `.env` Optionen

```env
# Datenquelle
DATA_SOURCE=database              # oder: excel

# Für Excel-Modus:
EXCEL_PATH=data/Datenmuster_OSNV_Maps.xlsx

# Für Datenbank-Modus:
DATABASE_URL=postgresql://...

# Umgebung
ENVIRONMENT=development           # oder: production

# Debug
DEBUG=True                         # oder: False
```

### Datenbank-Anforderungen

Die Datenbank sollte folgende Tabellen/Spalten haben:

```
Tabellen: EZA, EZAR, OSNV, EZE
(oder alternativ: eine Tabelle namens "projekte")

Erforderliche Spalten:
- Art (Kraftwerksart: HKW, Wind, PV, etc.)
- VN (Verkehrsnummer)
- Name (Projektname)
- Status (Angebot/Auftrag)
- PLZ (Postleitzahl)

Optional:
- Land (Länder-Code: DE, AT, CH, etc.)
- Kunde (Kundenname)
- Messtechnik eingebaut (ja/nein)
- Bundesland (Bundesland-Name)
- Stadt (Stadt-Name)
```

---

## 🆘 Fehlerbehebung

### Fehler: "DATABASE_URL nicht gefunden"

```bash
# Überprüfe .env Datei
cat .env

# Sollte DATABASE_URL haben wenn DATA_SOURCE=database
# Sonst: .env.example kopieren und ausfüllen
```

### Fehler: "Datenbankverbindung fehlgeschlagen"

```bash
# 1. Überprüfe DATABASE_URL Syntax
# 2. Überprüfe ob DB-Server erreichbar ist
# 3. Überprüfe Credentials (Username/Password)
# 4. Überprüfe ob DB-Driver installiert ist
pip install psycopg2-binary  # oder entsprechender Driver
```

### Fehler: "Keine passenden Projekt-Tabellen gefunden"

```bash
# Die Datenbank hat nicht die erwarteten Tabellen
# Entweder:
# 1. Erstelle Tabellen: EZA, EZAR, OSNV, EZE
# 2. Oder: Erstelle Tabelle "projekte" mit allen Spalten
# 3. Oder: Nutze Excel-Modus (DATA_SOURCE=excel)
```

### Fallback auf Excel

Wenn Datenbank fehlschlägt, versucht die App automatisch auf Excel auszuweichen:

```env
# Auch mit DATA_SOURCE=database
# Wenn DB-Fehler → nutzt automatisch Excel-Datei
EXCEL_PATH=data/Datenmuster_OSNV_Maps.xlsx
```

---

## 📝 Workflow mit Git

### Zuhause (Excel)

```bash
# .env ist NICHT committed (in .gitignore)
git pull
.venv/bin/python ./src/app/main.py
```

### Im Büro (Datenbank)

```bash
# .env ist NICHT committed (in .gitignore)
git pull
# → Code ist aktuell
# → Deine .env bleibt wie sie ist (mit DB-Credentials)
.venv/bin/python ./src/app/main.py
```

### Neue Features entwickeln

```bash
git checkout -b feature/mein-feature
# ... Code ändern ...
git add src/app/main.py src/app/data_loader.py
git commit -m "feat: Neue Feature"
git push origin feature/mein-feature
# → Pull Request erstellen
```

**Wichtig: `.env` niemals committen!**

```bash
# Überprüfe vor dem Commit:
git status
# .env sollte NICHT aufgelistet sein (wenn in .gitignore)
```

---

## 🚀 Production Deployment

Für echte Kundendaten in Production:

```env
ENVIRONMENT=production
DEBUG=False

# Sichere Datenbank-Credentials:
DATABASE_URL=postgresql://produser:SICHERES_PW@prod-db.firma.de:5432/firmendb

# Verwende starke Passwords!
# Nutze SSH-Tunnel für DB-Verbindung wenn möglich
```

---

## 📞 Support

Bei Fragen oder Problemen:
1. `.env` Syntax überprüfen (keine Spaces um `=`)
2. Database-Verbindung testen: `python -c "from src.app.data_loader import load_projects; load_projects()"`
3. Logs anschauen: Script mit `-v` Flag oder `DEBUG=True` in `.env`

---

## ✅ Checkliste für die Arbeit

- [ ] Repository geklont
- [ ] `.venv` erstellt und aktiviert
- [ ] `requirements.txt` installiert
- [ ] `.env` Datei erstellt (`.env.example` kopiert)
- [ ] DATABASE_URL in `.env` gesetzt
- [ ] DB-Treiber installiert (`pip install psycopg2-binary` etc.)
- [ ] `load_projects()` Test erfolgreich
- [ ] `main.py` startet und generiert HTML
- [ ] Karte im Browser öffnet sich

Viel Erfolg! 🎯

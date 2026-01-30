"""
Data Loader - Flexible Datenquelle (Excel oder Datenbank)
Unterstützt mehrere DB-Typen: PostgreSQL, MySQL, MS SQL Server, SQLite
"""

import os
import pandas as pd
from dotenv import load_dotenv
from typing import Optional

# Lade .env Variablen
load_dotenv()


def get_data_source() -> str:
    """Bestimmt Datenquelle: 'excel' oder 'database'"""
    return os.getenv('DATA_SOURCE', 'excel').lower()


def load_from_excel(excel_path: Optional[str] = None) -> dict:
    """
    Lädt Projekte aus Excel-Datei
    
    Args:
        excel_path: Pfad zur Excel-Datei (falls nicht in .env definiert)
    
    Returns:
        Dict mit DataFrames für jedes Sheet: {sheet_name: DataFrame}
    """
    if not excel_path:
        excel_path = os.getenv('EXCEL_PATH', 'data/Datenmuster_OSNV_Maps.xlsx')
    
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel-Datei nicht gefunden: {excel_path}")
    
    print(f"📂 Lade Excel: {excel_path}")
    
    xls = pd.ExcelFile(excel_path)
    projects_dict = {}
    
    for sheet in xls.sheet_names:
        projects_dict[sheet] = pd.read_excel(xls, sheet_name=sheet)
        print(f"   ✓ Sheet '{sheet}': {len(projects_dict[sheet])} Zeilen")
    
    return projects_dict


def load_from_database(db_url: Optional[str] = None) -> dict:
    """
    Lädt Projekte aus Datenbank
    
    Unterstützt:
    - PostgreSQL: postgresql://user:pass@host:5432/db
    - MySQL:      mysql+pymysql://user:pass@host:3306/db
    - MS SQL:     mssql+pyodbc://user:pass@host/db?driver=ODBC+Driver+17+for+SQL+Server
    - SQLite:     sqlite:///path/to/database.db
    
    Args:
        db_url: Datenbank-URL (falls nicht in .env definiert)
    
    Returns:
        Dict mit DataFrames für jede Kategorie: {category: DataFrame}
    """
    if not db_url:
        db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        raise ValueError(
            "DATABASE_URL nicht gefunden! "
            "Bitte .env Datei mit DATABASE_URL ausfüllen."
        )
    
    print(f"🔗 Verbinde mit Datenbank...")
    
    try:
        from sqlalchemy import create_engine, text, inspect
    except ImportError:
        raise ImportError(
            "SQLAlchemy nicht installiert! "
            "Bitte installieren: pip install sqlalchemy"
        )
    
    try:
        engine = create_engine(db_url, echo=False)
        
        # Teste Verbindung
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("   ✓ Datenbankverbindung erfolgreich")
        
    except Exception as e:
        raise ConnectionError(
            f"Fehler bei Datenbankverbindung: {e}\n"
            f"Überprüfe DATABASE_URL in .env"
        )
    
    # Lade Daten
    projects_dict = {}
    
    # Versuch 1: Nach Kategorien-Tabelle suchen (EZA, EZAR, OSNV, EZE)
    categories = ['EZA', 'EZAR', 'OSNV', 'EZE']
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    found_tables = [cat for cat in categories if cat in tables]
    
    if found_tables:
        print(f"   Gefundene Tabellen: {found_tables}")
        for category in found_tables:
            try:
                df = pd.read_sql_table(category, engine)
                projects_dict[category] = df
                print(f"   ✓ {category}: {len(df)} Zeilen")
            except Exception as e:
                print(f"   ⚠ {category}: Fehler - {e}")
    
    # Versuch 2: Falls nur eine "projekte" Tabelle existiert
    elif 'projekte' in tables or 'projects' in tables:
        table_name = 'projekte' if 'projekte' in tables else 'projects'
        try:
            df = pd.read_sql_table(table_name, engine)
            projects_dict['Projekte'] = df
            print(f"   ✓ {table_name}: {len(df)} Zeilen")
        except Exception as e:
            print(f"   ⚠ {table_name}: Fehler - {e}")
    
    else:
        # Fallback: Zeige verfügbare Tabellen
        print(f"   ⚠ Keine Standard-Tabellen gefunden")
        print(f"   Verfügbare Tabellen: {tables}")
        raise ValueError(
            f"Keine passenden Projekt-Tabellen gefunden. "
            f"Erwartete: 'EZA', 'EZAR', 'OSNV', 'EZE' oder 'projekte'. "
            f"Vorhanden: {tables}"
        )
    
    engine.dispose()
    return projects_dict


def load_projects() -> dict:
    """
    Haupt-Funktion: Lädt Projekte je nach Konfiguration
    
    Returns:
        Dict mit DataFrames: {sheet_name: DataFrame}
    
    Raises:
        FileNotFoundError: Excel-Datei nicht gefunden
        ConnectionError: Datenbankverbindung fehlgeschlagen
        ValueError: Ungültige Konfiguration
    """
    source = get_data_source()
    
    if source == 'database':
        return load_from_database()
    elif source == 'excel':
        return load_from_excel()
    else:
        raise ValueError(
            f"Unbekannte DATA_SOURCE: '{source}'. "
            f"Erwartet: 'excel' oder 'database'"
        )


def get_projects_dataframe() -> pd.DataFrame:
    """
    Kombiniert alle Projekt-Sheets in einen DataFrame
    
    Returns:
        Kombinierter DataFrame mit allen Projekten
    """
    projects_dict = load_projects()
    
    # Kombiniere alle Sheets
    dfs = []
    for sheet_name, df in projects_dict.items():
        if df.empty:
            continue
        dfs.append(df)
    
    if not dfs:
        return pd.DataFrame()
    
    combined_df = pd.concat(dfs, ignore_index=True)
    print(f"✅ Gesamt {len(combined_df)} Projekte geladen")
    
    return combined_df


# Für Debugging
if __name__ == '__main__':
    try:
        projects = load_projects()
        print("\n📊 Geladene Daten:")
        for sheet, df in projects.items():
            print(f"\n{sheet}:")
            print(df.head(2))
            print(f"Spalten: {list(df.columns)}")
    except Exception as e:
        print(f"❌ Fehler: {e}")

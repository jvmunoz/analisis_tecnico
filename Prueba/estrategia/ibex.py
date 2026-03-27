import requests
import pandas as pd
import os
from io import StringIO
from datetime import datetime

CORRECCIONES_MANUALES_WIKIPEDIA = {"MEL.MC": ("PUIG.MC", "Puig Brands")}

HISTORIAL_IBEX_FILE = "ibex_constituents_history.csv"

SECTORES_IBEX = {
    "SAN.MC": "Banca",
    "BBVA.MC": "Banca",
    "CABK.MC": "Banca",
    "SAB.MC": "Banca",
    "BKT.MC": "Banca",
    "UNI.MC": "Banca",
    "IBE.MC": "Energia",
    "ELE.MC": "Energia",
    "NTGY.MC": "Energia",
    "RED.MC": "Energia",
    "ENG.MC": "Energia",
    "SLR.MC": "Energia",
    "ANE.MC": "Energia",
    "REP.MC": "Petroleo",
    "ITX.MC": "Retail/Textil",
    "AMS.MC": "Tecnologia",
    "IDR.MC": "Tecnologia",
    "CLNX.MC": "Telecom",
    "TEF.MC": "Telecom",
    "AENA.MC": "Transporte",
    "IAG.MC": "Transporte",
    "ACS.MC": "Construccion",
    "FER.MC": "Construccion",
    "SCYR.MC": "Construccion",
    "ANA.MC": "Construccion",
    "MTS.MC": "Acero/Mineria",
    "ACX.MC": "Acero/Mineria",
    "GRF.MC": "Farmacia",
    "ROVI.MC": "Farmacia",
    "COL.MC": "Inmobiliaria",
    "MRL.MC": "Inmobiliaria",
    "LOG.MC": "Logistica",
    "MAP.MC": "Seguros",
    "FDR.MC": "Industrial",
    "PUIG.MC": "Consumo",
}

HISTORIAL_IBEX_FILE = "ibex_constituents_history.csv"

SECTORES_IBEX = {
    "SAN.MC": "Banca",
    "BBVA.MC": "Banca",
    "CABK.MC": "Banca",
    "SAB.MC": "Banca",
    "BKT.MC": "Banca",
    "UNI.MC": "Banca",
    "IBE.MC": "Energia",
    "ELE.MC": "Energia",
    "NTGY.MC": "Energia",
    "RED.MC": "Energia",
    "ENG.MC": "Energia",
    "SLR.MC": "Energia",
    "ANE.MC": "Energia",
    "REP.MC": "Petroleo",
    "ITX.MC": "Retail/Textil",
    "AMS.MC": "Tecnologia",
    "IDR.MC": "Tecnologia",
    "CLNX.MC": "Telecom",
    "TEF.MC": "Telecom",
    "AENA.MC": "Transporte",
    "IAG.MC": "Transporte",
    "ACS.MC": "Construccion",
    "FER.MC": "Construccion",
    "SCYR.MC": "Construccion",
    "ANA.MC": "Construccion",
    "MTS.MC": "Acero/Mineria",
    "ACX.MC": "Acero/Mineria",
    "GRF.MC": "Farmacia",
    "ROVI.MC": "Farmacia",
    "COL.MC": "Inmobiliaria",
    "MRL.MC": "Inmobiliaria",
    "LOG.MC": "Logistica",
    "MAP.MC": "Seguros",
    "FDR.MC": "Industrial",
    "PUIG.MC": "Consumo",
}

def obtener_componentes_ibex():
    """Obtiene un diccionario {ticker: nombre} actual de componentes del IBEX 35 desde Wikipedia."""
    print("Obteniendo componentes del IBEX 35 desde Wikipedia...", flush=True)
    url = "https://es.wikipedia.org/wiki/IBEX_35"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        tables = pd.read_html(StringIO(response.text))

        ibex_table = None
        for table in tables:
            str_cols = [str(col).lower() for col in table.columns]
            if (
                any("ticket" in c for c in str_cols)
                or any("ticker" in c for c in str_cols)
                or any("símbolo" in c for c in str_cols)
            ) and any("empresa" in c for c in str_cols):
                ibex_table = table
                break

        if ibex_table is not None:
            ticker_col = next(
                (
                    c
                    for c in ibex_table.columns
                    if "ticket" in str(c).lower()
                    or "ticker" in str(c).lower()
                    or "símbolo" in str(c).lower()
                ),
                None,
            )

            name_col = next(
                (c for c in ibex_table.columns if "empresa" in str(c).lower()), None
            )

            if ticker_col and name_col:
                results = {}
                for index, row in ibex_table.iterrows():
                    ticker = str(row[ticker_col]).strip()
                    name = str(row[name_col]).strip()
                    if not ticker.endswith(".MC"):
                        ticker += ".MC"
                    results[ticker] = name

                # --- CORRECCIÓN MANUAL DE DATOS DESACTUALIZADOS ---
                # Aplicamos las correcciones definidas en configuración si Wikipedia está desactualizada
                for old_ticker, (
                    new_ticker,
                    new_name,
                ) in CORRECCIONES_MANUALES_WIKIPEDIA.items():
                    if old_ticker in results and new_ticker not in results:
                        print(
                            f"AVISO: Detectado '{old_ticker}' desactualizado. Sustituyendo por '{new_ticker}' ({new_name}) según configuración manual."
                        )
                        del results[old_ticker]
                        results[new_ticker] = new_name

                print(f"Se han encontrado {len(results)} componentes con nombres.")
                return results
            else:
                print("No se encontraron las columnas necesarias (Ticker/Empresa).")
                return {}
        else:
            print("No se encontró la tabla de componentes del IBEX 35.")
            return {}

    except Exception as e:
        print(f"Error al obtener componentes del IBEX: {e}")
        return {}

def cargar_historial_ibex(filename=HISTORIAL_IBEX_FILE):
    """Carga el historial de componentes IBEX para evitar sesgo de supervivencia."""
    print(f"DEBUG: Intentando cargar historial desde {filename}...", flush=True)
    if not os.path.exists(filename):
        print(
            f"Aviso: No se encontró el historial IBEX '{filename}'. Usando componentes actuales.",
            flush=True,
        )
        return []

    try:
        df = pd.read_csv(filename)
    except Exception as e:
        print(f"Aviso: No se pudo leer el historial IBEX '{filename}': {e}")
        return []

    if df.empty:
        print(f"Aviso: Historial IBEX '{filename}' vacío. Usando componentes actuales.")
        return []

    cols_lower = {c.lower(): c for c in df.columns}
    ticker_col = (
        cols_lower.get("ticker")
        or cols_lower.get("tickers")
        or cols_lower.get("simbolo")
        or cols_lower.get("símbolo")
    )
    start_col = (
        cols_lower.get("start")
        or cols_lower.get("inicio")
        or cols_lower.get("start_date")
        or cols_lower.get("fecha_inicio")
    )
    end_col = (
        cols_lower.get("end")
        or cols_lower.get("fin")
        or cols_lower.get("end_date")
        or cols_lower.get("fecha_fin")
    )
    name_col = (
        cols_lower.get("name") or cols_lower.get("empresa") or cols_lower.get("nombre")
    )

    if not ticker_col:
        print(
            f"Aviso: Historial IBEX '{filename}' sin columna de Ticker. Usando componentes actuales."
        )
        return []

    records = []
    for _, row in df.iterrows():
        ticker = str(row[ticker_col]).strip().upper()
        if not ticker:
            continue
        start_val = (
            pd.to_datetime(row[start_col], errors="coerce") if start_col else pd.NaT
        )
        end_val = pd.to_datetime(row[end_col], errors="coerce") if end_col else pd.NaT
        name_val = (
            str(row[name_col]).strip()
            if name_col and not pd.isna(row[name_col])
            else ""
        )

        records.append(
            {
                "ticker": ticker,
                "start": None if pd.isna(start_val) else start_val,
                "end": None if pd.isna(end_val) else end_val,
                "name": name_val,
            }
        )

    if not records:
        print(
            f"Aviso: Historial IBEX '{filename}' sin registros válidos. Usando componentes actuales."
        )
    else:
        print(f"Historial IBEX cargado: {len(records)} registros.")
    return records

def construir_dicc_tickers_desde_historial(historial, fallback_dict=None):
    nombres = {}
    for item in historial:
        t = item.get("ticker")
        name = item.get("name") or ""
        if t:
            nombres[t] = name if name else t
    if fallback_dict:
        for t, name in fallback_dict.items():
            if t not in nombres:
                nombres[t] = name
    return nombres

def construir_mapa_historial(historial):
    mapa = {}
    for item in historial:
        t = item.get("ticker")
        if not t:
            continue
        start = item.get("start") or datetime.min
        end = item.get("end")
        mapa.setdefault(t, []).append((start, end))
    for t in mapa:
        mapa[t].sort(key=lambda x: x[0])
    return mapa

def filtrar_datos_por_historial(df, historial_map, tickers_always=None):
    if df is None or df.empty or not historial_map:
        return df

    always = set([t.upper() for t in (tickers_always or [])])
    filtered = []
    for ticker, df_t in df.groupby("ticker"):
        if ticker in always or ticker == "^IBEX":
            filtered.append(df_t)
            continue
        intervals = historial_map.get(ticker)
        if not intervals:
            continue

        mask = pd.Series(False, index=df_t.index)
        for start, end in intervals:
            if end is None:
                mask |= df_t["date"] >= start
            else:
                mask |= (df_t["date"] >= start) & (df_t["date"] <= end)
        filtered.append(df_t[mask])

    if not filtered:
        return df.iloc[0:0]
    return pd.concat(filtered).sort_values(by=["ticker", "date"])


# ==============================================================================
# FUNCIÓN 3: VISUALIZACIÓN EN PDF
# ==============================================================================


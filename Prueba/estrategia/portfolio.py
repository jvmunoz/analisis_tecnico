import os
import glob
import re
from datetime import datetime
from pathlib import Path
import pandas as pd


MAX_APERTURA_SOBRE_ENTRADA_PCT = 1.5


def _leer_csv_journal(path):
    try:
        try:
            return pd.read_csv(path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(path, encoding="latin1")
    except Exception:
        return pd.DataFrame()


def _normalizar_fecha(valor):
    fecha = pd.to_datetime(valor, errors="coerce")
    if pd.isna(fecha):
        return ""
    return fecha.strftime("%Y-%m-%d")


def _operacion_id(fecha_deteccion, ticker, setup):
    fecha_norm = _normalizar_fecha(fecha_deteccion)
    ticker = "" if pd.isna(ticker) else str(ticker)
    setup = "" if pd.isna(setup) else str(setup)
    if not fecha_norm or not ticker or not setup:
        return ""
    return f"{fecha_norm.replace('-', '')}|{ticker}|{setup}"


def _precio_demasiado_alejado_de_entrada(
    senal, max_pct=MAX_APERTURA_SOBRE_ENTRADA_PCT
):
    try:
        entrada = float(senal.get("Entrada", 0))
        precio = float(senal.get("Precio", 0))
    except (TypeError, ValueError):
        return False
    if entrada <= 0 or precio <= 0:
        return False
    exceso_pct = ((precio / entrada) - 1) * 100
    return exceso_pct > max_pct


def _tipo_evento_desde_estado(estado_previo, estado_nuevo):
    estado_previo = "" if pd.isna(estado_previo) else str(estado_previo)
    estado_nuevo = "" if pd.isna(estado_nuevo) else str(estado_nuevo)

    if estado_previo == "" and not estado_nuevo.startswith("CERRADA"):
        return "APERTURA"
    if "CERRADA" in estado_nuevo:
        return "CIERRE"
    if "VIGILANCIA" in estado_nuevo:
        return "ALERTA"
    if estado_nuevo == "ABIERTA" and "VIGILANCIA" in estado_previo:
        return "REACTIVACION"
    return "CAMBIO_ESTADO"


def _motivo_desde_estado(estado_nuevo, tipo_evento):
    estado_nuevo = "" if pd.isna(estado_nuevo) else str(estado_nuevo)

    if tipo_evento == "APERTURA":
        return "Nueva señal VERDE"
    if "STOP" in estado_nuevo:
        return "Stop alcanzado"
    if "TARGET" in estado_nuevo:
        return "Objetivo T2 alcanzado"
    if "DETERIORO" in estado_nuevo:
        return "Deterioro técnico (Semáforo ROJO)"
    if "VIGILANCIA (T2)" in estado_nuevo:
        return "Proximidad a T2"
    if "VIGILANCIA (T1)" in estado_nuevo:
        return "Proximidad a T1"
    if tipo_evento == "REACTIVACION":
        return "ABIERTA"
    return estado_nuevo


def _ordenar_eventos_journal(df_eventos):
    if df_eventos is None or df_eventos.empty:
        return df_eventos

    prioridad_tipo = {
        "CIERRE": 0,
        "CAMBIO_ESTADO": 1,
        "REACTIVACION": 2,
        "ALERTA": 3,
        "APERTURA": 4,
    }
    df_ordenado = df_eventos.copy()
    df_ordenado["_Fecha_Evento_Orden"] = pd.to_datetime(
        df_ordenado["Fecha_Evento"], errors="coerce"
    )
    df_ordenado["_Fecha_Deteccion_Orden"] = pd.to_datetime(
        df_ordenado["Fecha_Deteccion"], errors="coerce"
    )
    df_ordenado["_Tipo_Evento_Orden"] = (
        df_ordenado["Tipo_Evento"].map(prioridad_tipo).fillna(99)
    )
    df_ordenado = df_ordenado.sort_values(
        by=[
            "_Fecha_Evento_Orden",
            "_Fecha_Deteccion_Orden",
            "Ticker",
            "Setup",
            "_Tipo_Evento_Orden",
        ],
        ascending=[False, False, True, True, True],
    )
    return df_ordenado.drop(
        columns=[
            "_Fecha_Evento_Orden",
            "_Fecha_Deteccion_Orden",
            "_Tipo_Evento_Orden",
        ]
    ).reset_index(drop=True)


def _construir_evento_journal(
    fecha_evento,
    row,
    estado_previo,
    estado_nuevo,
):
    tipo_evento = _tipo_evento_desde_estado(estado_previo, estado_nuevo)
    fecha_deteccion = _normalizar_fecha(row.get("Fecha_Deteccion", ""))
    ticker = row.get("Ticker", "")
    setup = row.get("Setup", "")
    return {
        "Fecha_Evento": _normalizar_fecha(fecha_evento),
        "Operacion_ID": _operacion_id(fecha_deteccion, ticker, setup),
        "Fecha_Deteccion": fecha_deteccion,
        "Ticker": ticker,
        "Setup": setup,
        "Estado_Previo": estado_previo,
        "Estado_Nuevo": estado_nuevo,
        "Tipo_Evento": tipo_evento,
        "Motivo": _motivo_desde_estado(estado_nuevo, tipo_evento),
        "Precio_Entrada": row.get("Precio_Entrada", ""),
        "Stop_Inicial": row.get("Stop_Inicial", ""),
        "T1": row.get("T1", ""),
        "T2": row.get("T2", ""),
        "Precio": row.get("Precio_Ultimo", row.get("Precio", "")),
        "P&L_%": row.get("P&L_%", ""),
    }


def normalizar_y_deduplicar_eventos(df_eventos, eventos_cols):
    dedup_cols = [
        "Operacion_ID",
        "Fecha_Evento",
        "Estado_Previo",
        "Estado_Nuevo",
        "Tipo_Evento",
    ]
    if df_eventos is None or df_eventos.empty:
        return pd.DataFrame(columns=eventos_cols)

    df_eventos = df_eventos.copy()
    for col in eventos_cols:
        if col not in df_eventos.columns:
            df_eventos[col] = pd.NA
    df_eventos = df_eventos[eventos_cols].copy()
    df_eventos["Fecha_Evento"] = pd.to_datetime(
        df_eventos["Fecha_Evento"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    df_eventos["Fecha_Deteccion"] = pd.to_datetime(
        df_eventos["Fecha_Deteccion"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    missing_op_id = df_eventos["Operacion_ID"].isna() | (
        df_eventos["Operacion_ID"].astype(str).str.strip() == ""
    )
    df_eventos.loc[missing_op_id, "Operacion_ID"] = df_eventos.loc[
        missing_op_id
    ].apply(
        lambda row: _operacion_id(
            row.get("Fecha_Deteccion", ""),
            row.get("Ticker", ""),
            row.get("Setup", ""),
        ),
        axis=1,
    )
    for col in dedup_cols:
        df_eventos[col] = df_eventos[col].fillna("").astype(str)

    # Cuando se reconstruyen eventos con identidad completa, las filas legacy
    # sin Operacion_ID solo duplican informacion ambigua de CSV antiguos.
    if (df_eventos["Operacion_ID"] != "").any():
        df_eventos = df_eventos[df_eventos["Operacion_ID"] != ""].copy()

    # Una apertura debe representar la creacion de una operacion ABIERTA. Si el
    # primer snapshot disponible ya estaba en vigilancia, no inventamos una
    # apertura con ese estado porque duplica la alerta real y confunde el orden.
    apertura_ambigua = (
        (df_eventos["Estado_Previo"] == "")
        & (df_eventos["Tipo_Evento"] == "APERTURA")
        & (df_eventos["Estado_Nuevo"] != "ABIERTA")
    )
    if apertura_ambigua.any():
        df_eventos = df_eventos[~apertura_ambigua].copy()

    df_eventos = df_eventos.drop_duplicates(
        subset=dedup_cols,
        keep="last",
    )
    return _ordenar_eventos_journal(df_eventos)


def columnas_exportacion_eventos(eventos_cols):
    return [col for col in eventos_cols if col != "Operacion_ID"]


def _fecha_snapshot_desde_nombre(path):
    m_fecha = re.search(r"hasta_(\d{8})\.csv$", os.path.basename(str(path)))
    if not m_fecha:
        return pd.NaT
    return pd.to_datetime(m_fecha.group(1), format="%Y%m%d", errors="coerce")


def reconstruir_eventos_desde_snapshots(snapshots, eventos_cols):
    snapshots = sorted(snapshots, key=lambda item: item[0])
    eventos = []
    estados_previos = {}

    for fecha_snapshot, df in snapshots:
        for _, row in df.iterrows():
            key = (
                _normalizar_fecha(row.get("Fecha_Deteccion", "")),
                str(row.get("Ticker", "")),
                str(row.get("Setup", "")),
            )
            estado_actual = row.get("Estado_Actual", "")
            estado_nuevo = "" if pd.isna(estado_actual) else str(estado_actual)
            estado_previo = estados_previos.get(key)

            if estado_previo is None:
                if estado_nuevo == "ABIERTA":
                    eventos.append(
                        _construir_evento_journal(
                            fecha_snapshot,
                            row,
                            "",
                            estado_nuevo,
                        )
                    )
                estados_previos[key] = estado_nuevo
                continue

            if estado_nuevo != estado_previo:
                eventos.append(
                    _construir_evento_journal(
                        fecha_snapshot,
                        row,
                        estado_previo,
                        estado_nuevo,
                    )
                )
                estados_previos[key] = estado_nuevo

    if not eventos:
        return pd.DataFrame(columns=eventos_cols)
    return pd.DataFrame(eventos, columns=eventos_cols)


def reconstruir_eventos_desde_journals(archivos_journal, eventos_cols):
    snapshots = []
    for path in sorted(archivos_journal):
        fecha_snapshot = _fecha_snapshot_desde_nombre(path)
        if pd.isna(fecha_snapshot):
            continue
        df = _leer_csv_journal(path)
        if df.empty or "Estado_Actual" not in df.columns:
            continue
        for col in ["Fecha_Deteccion", "Ticker", "Setup"]:
            if col not in df.columns:
                df[col] = ""
        snapshots.append((fecha_snapshot, df.copy()))

    return reconstruir_eventos_desde_snapshots(snapshots, eventos_cols)


def cargar_cartera(filename="cartera.csv"):
    """
    Carga el archivo de cartera del usuario y calcula posiciones netas.
    Admite UTF-8 y Latin-1 (para compatibilidad con Excel).
    """
    if not os.path.exists(filename):
        print(f"Aviso: No se encontró el archivo de cartera '{filename}'.")
        return pd.DataFrame(), [], None, pd.DataFrame()

    try:
        try:
            df = pd.read_csv(filename, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(filename, encoding="latin1")

        df.columns = [c.strip() for c in df.columns]

        req_cols = {"Ticker", "Tipo", "Cantidad", "Precio", "Fecha"}
        if not req_cols.issubset(df.columns):
            print(
                f"Error Cartera: Faltan columnas requeridas {req_cols - set(df.columns)}"
            )
            return pd.DataFrame(), [], None, df

        # Normalización
        df["Ticker"] = df["Ticker"].str.strip().str.upper()
        df["Tipo"] = df["Tipo"].str.strip().str.upper()
        df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
        df = df.dropna(subset=["Fecha"])

        posiciones = {}
        for ticker in df["Ticker"].unique():
            df_t = df[df["Ticker"] == ticker]
            compras = df_t[df_t["Tipo"] == "COMPRA"]["Cantidad"].sum()
            ventas = df_t[df_t["Tipo"] == "VENTA"]["Cantidad"].sum()
            net_qty = compras - ventas

            if net_qty > 0.0001:
                df_compras = df_t[df_t["Tipo"] == "COMPRA"]
                # Cálculo de Precio Medio Ponderado (FIFO simplificado)
                coste_total = (df_compras["Cantidad"] * df_compras["Precio"]).sum()
                qty_comprada = df_compras["Cantidad"].sum()
                precio_medio = coste_total / qty_comprada if qty_comprada > 0 else 0
                posiciones[ticker] = {"Cantidad": net_qty, "Precio_Medio": precio_medio}

        if not posiciones:
            return pd.DataFrame(), [], None, df

        df_active = pd.DataFrame.from_dict(posiciones, orient="index").reset_index()
        df_active.columns = ["Ticker", "Cantidad", "Precio_Medio"]

        early_date = df["Fecha"].min()
        return df_active, df_active["Ticker"].tolist(), early_date, df

    except Exception as e:
        print(f"Error al procesar cartera: {e}")
        return pd.DataFrame(), [], None, pd.DataFrame()

def gestionar_journal_operaciones(
    data_enriquecida,
    filename="journal_operaciones.csv",
    fecha_v="",
    rules_config=None,
):
    """
    Registra señales VERDE y hace seguimiento de las existentes.
    Acumula datos de múltiples fechas y se renombra dinámicamente según la fecha máxima analizada.
    """
    cols = [
        "Fecha_Deteccion",
        "Fecha_Actualizacion",
        "Fecha_Cierre",
        "Ticker",
        "Setup",
        "Precio_Entrada",
        "Stop_Inicial",
        "T1",
        "T2",
        "Estado_Actual",
        "Tipo",
        "Icono",
        "Precio_Ultimo",
        "P&L_%",
    ]
    eventos_cols = [
        "Fecha_Evento",
        "Operacion_ID",
        "Fecha_Deteccion",
        "Ticker",
        "Setup",
        "Estado_Previo",
        "Estado_Nuevo",
        "Tipo_Evento",
        "Motivo",
        "Precio_Entrada",
        "Stop_Inicial",
        "T1",
        "T2",
        "Precio",
        "P&L_%",
    ]
    max_apertura_sobre_entrada_pct = MAX_APERTURA_SOBRE_ENTRADA_PCT
    if isinstance(rules_config, dict):
        try:
            max_apertura_sobre_entrada_pct = float(
                rules_config.get(
                    "max_apertura_sobre_entrada_pct",
                    MAX_APERTURA_SOBRE_ENTRADA_PCT,
                )
            )
        except (TypeError, ValueError):
            max_apertura_sobre_entrada_pct = MAX_APERTURA_SOBRE_ENTRADA_PCT

    # 1. Identificar y consolidar journals del run actual + historicos de runs previos
    cwd = Path.cwd()
    archivos_locales = sorted(cwd.glob("journal_operaciones*.csv"))
    archivos_journal = {str(p.resolve()) for p in archivos_locales}
    archivos_eventos_locales = sorted(cwd.glob("journal_eventos*.csv"))
    archivos_eventos = {str(p.resolve()) for p in archivos_eventos_locales}

    # Buscar carpeta runs en la ruta actual (normalmente .../Prueba/runs/YYYYMMDD)
    runs_root = next((p for p in [cwd, *cwd.parents] if p.name == "runs"), None)
    if runs_root is not None and runs_root.exists():
        for p in runs_root.glob("*/journal_operaciones_hasta_*.csv"):
            archivos_journal.add(str(p.resolve()))
        for p in runs_root.glob("*/journal_eventos_hasta_*.csv"):
            archivos_eventos.add(str(p.resolve()))

    fecha_analisis = fecha_v if fecha_v else datetime.now().strftime("%Y-%m-%d")
    fecha_analisis_norm = pd.to_datetime(fecha_analisis).strftime("%Y-%m-%d")
    fecha_analisis_ts = pd.to_datetime(fecha_analisis_norm)

    def _solo_hasta_fecha_analisis(paths):
        filtrados = []
        for path in paths:
            fecha_snapshot = _fecha_snapshot_desde_nombre(path)
            if pd.isna(fecha_snapshot) or fecha_snapshot <= fecha_analisis_ts:
                filtrados.append(path)
        return filtrados

    archivos_journal = sorted(archivos_journal)
    archivos_journal = _solo_hasta_fecha_analisis(archivos_journal)
    archivos_eventos = _solo_hasta_fecha_analisis(sorted(archivos_eventos))
    print(f"DEBUG: Archivos de diario encontrados: {archivos_journal}")
    dataframes = []
    fechas_historia_files = []
    eventos_dataframes = []
    fechas_historia_eventos_files = []

    for f in archivos_journal:
        try:
            # Extraer fecha del nombre del archivo (ej: journal_operaciones_hasta_20260102.csv)
            base_name = os.path.basename(f)
            m_fecha = re.search(r"hasta_(\d{8})\.csv$", base_name)
            if m_fecha:
                fechas_historia_files.append(
                    pd.to_datetime(m_fecha.group(1), format="%Y%m%d")
                )

            try:
                temp_df = pd.read_csv(f, encoding="utf-8-sig")
            except UnicodeDecodeError:
                temp_df = pd.read_csv(f, encoding="latin1")
            if not temp_df.empty and "Fecha_Deteccion" in temp_df.columns:
                temp_df["Fecha_Deteccion"] = pd.to_datetime(
                    temp_df["Fecha_Deteccion"], errors="coerce"
                ).dt.strftime("%Y-%m-%d")
            dataframes.append(temp_df)
        except:
            pass

    for f in archivos_eventos:
        try:
            base_name = os.path.basename(f)
            m_fecha = re.search(r"hasta_(\d{8})\.csv$", base_name)
            if m_fecha:
                fechas_historia_eventos_files.append(
                    pd.to_datetime(m_fecha.group(1), format="%Y%m%d")
                )
            try:
                temp_df = pd.read_csv(f, encoding="utf-8-sig")
            except UnicodeDecodeError:
                temp_df = pd.read_csv(f, encoding="latin1")
            if not temp_df.empty and "Fecha_Evento" in temp_df.columns:
                temp_df["Fecha_Evento"] = pd.to_datetime(
                    temp_df["Fecha_Evento"], errors="coerce"
                ).dt.strftime("%Y-%m-%d")
            eventos_dataframes.append(temp_df)
        except:
            pass

    if dataframes:
        df_journal = pd.concat(dataframes, ignore_index=True)
        # Compatibilidad hacia atrás: añadir columnas nuevas si no existen
        for c in cols:
            if c not in df_journal.columns:
                df_journal[c] = pd.NA
        df_journal = df_journal.drop_duplicates(
            subset=["Fecha_Deteccion", "Ticker", "Setup"], keep="last"
        )
        df_journal = df_journal.reset_index(drop=True)
    else:
        df_journal = pd.DataFrame(columns=cols)

    if eventos_dataframes:
        df_eventos = pd.concat(eventos_dataframes, ignore_index=True)
        for c in eventos_cols:
            if c not in df_eventos.columns:
                df_eventos[c] = pd.NA
        df_eventos = df_eventos[eventos_cols].copy()
    else:
        df_eventos = pd.DataFrame(columns=eventos_cols)

    # 2. Sustitución: Si ya existen señales DETECTADAS el mismo día, las borramos para poner las nuevas del análisis
    if not df_journal.empty:
        df_journal = df_journal[
            df_journal["Fecha_Deteccion"] != fecha_analisis_norm
        ].copy()
        df_journal = df_journal.reset_index(drop=True)

    # 3. Añadir nuevas señales VERDE detectadas hoy
    nuevas_senales = [d for d in data_enriquecida if d["Semaforo"] == "VERDE"]
    for s in nuevas_senales:
        if _precio_demasiado_alejado_de_entrada(
            s, max_pct=max_apertura_sobre_entrada_pct
        ):
            continue
        ticker = s["Ticker"]
        if (
            ticker
            not in df_journal[df_journal["Estado_Actual"] == "ABIERTA"]["Ticker"].values
        ):
            nueva_fila = {
                "Fecha_Deteccion": fecha_analisis_norm,
                "Fecha_Actualizacion": fecha_analisis_norm,
                "Fecha_Cierre": "",
                "Ticker": ticker,
                "Setup": s["Setup"],
                "Precio_Entrada": s["Entrada"],
                "Stop_Inicial": s["Stop"],
                "T1": s["T1"],
                "T2": s["T2"],
                "Estado_Actual": "ABIERTA",
                "Tipo": "🟢 Activo",
                "Icono": "✅",
                "Precio_Ultimo": s["Precio"],
                "P&L_%": 0.0,
            }
            df_journal.loc[len(df_journal)] = nueva_fila
            df_eventos.loc[len(df_eventos)] = _construir_evento_journal(
                fecha_analisis_norm,
                {
                    "Fecha_Deteccion": fecha_analisis_norm,
                    "Ticker": ticker,
                    "Setup": s["Setup"],
                    "Precio_Entrada": s["Entrada"],
                    "Stop_Inicial": s["Stop"],
                    "T1": s["T1"],
                    "T2": s["T2"],
                    "Precio_Ultimo": s["Precio"],
                    "P&L_%": 0.0,
                },
                "",
                "ABIERTA",
            )

    # 4. Actualizar seguimiento de todas las posiciones activas (ABIERTA o VIGILANCIA)
    for i, row in df_journal.iterrows():
        estado_act = str(row["Estado_Actual"])
        if not estado_act.startswith("CERRADA"):
            ticker = row["Ticker"]
            match = next((d for d in data_enriquecida if d["Ticker"] == ticker), None)
            if match:
                precio_act = match["Precio"]
                # Definir PRIORIDAD de estados (Cierres > Alertas > Abierta)
                try:
                    t1_val = float(row["T1"])
                    t2_val = float(row["T2"])
                    stop_val = float(row["Stop_Inicial"])
                    ent_val = float(row["Precio_Entrada"])
                except:
                    t1_val, t2_val, stop_val, ent_val = 0, 0, 0, 0

                # Actualizar precios y P&L
                precio_act_f = float(precio_act)
                df_journal.loc[i, "Precio_Ultimo"] = round(precio_act_f, 2)
                if ent_val != 0:
                    p_l_val = ((precio_act_f - ent_val) / ent_val) * 100
                    df_journal.loc[i, "P&L_%"] = round(p_l_val, 2)
                df_journal.loc[i, "Fecha_Actualizacion"] = fecha_analisis_norm

                # Lógica de estados (Cierres > Alertas > Abierta)
                nuevo_estado = "ABIERTA"

                if precio_act_f <= stop_val:
                    nuevo_estado = "CERRADA (STOP)"
                elif t2_val > 0 and precio_act_f >= t2_val:
                    nuevo_estado = "CERRADA (TARGET)"
                elif match["Semaforo"] == "ROJO":
                    nuevo_estado = "CERRADA (DETERIORO)"
                else:
                    # Alertas de proximidad al 1%
                    d_t1 = abs(precio_act_f / t1_val - 1) if t1_val > 0 else 999
                    d_t2 = abs(precio_act_f / t2_val - 1) if t2_val > 0 else 999

                    if d_t2 <= 0.01:
                        nuevo_estado = "VIGILANCIA (T2)"
                    elif d_t1 <= 0.01:
                        nuevo_estado = "VIGILANCIA (T1)"

                df_journal.loc[i, "Estado_Actual"] = nuevo_estado
                if "CERRADA" in nuevo_estado:
                    df_journal.loc[i, "Fecha_Cierre"] = fecha_analisis_norm

                if nuevo_estado != estado_act:
                    df_eventos.loc[len(df_eventos)] = _construir_evento_journal(
                        fecha_analisis_norm,
                        {
                            "Fecha_Deteccion": row.get("Fecha_Deteccion", ""),
                            "Ticker": ticker,
                            "Setup": row.get("Setup", ""),
                            "Precio_Entrada": row.get("Precio_Entrada", ""),
                            "Stop_Inicial": row.get("Stop_Inicial", ""),
                            "T1": row.get("T1", ""),
                            "T2": row.get("T2", ""),
                            "Precio_Ultimo": round(precio_act_f, 2),
                            "P&L_%": df_journal.loc[i, "P&L_%"],
                        },
                        estado_act,
                        nuevo_estado,
                    )

                # Actualizar Tipo e Icono según el nuevo estado
                if nuevo_estado == "ABIERTA":
                    df_journal.loc[i, "Tipo"] = "🟢 Activo"
                    df_journal.loc[i, "Icono"] = "✅"
                elif "VIGILANCIA" in nuevo_estado:
                    df_journal.loc[i, "Tipo"] = "🟡 Alerta"
                    df_journal.loc[i, "Icono"] = "⚠️"
                elif nuevo_estado == "CERRADA (TARGET)":
                    df_journal.loc[i, "Tipo"] = "✅ Cerrado"
                    df_journal.loc[i, "Icono"] = "🎯"
                elif "CERRADA" in nuevo_estado:
                    df_journal.loc[i, "Tipo"] = "❌ Cerrado"
                    df_journal.loc[i, "Icono"] = "🔴"

    # 5. Calcular nuevo nombre basado en la fecha máxima ABSOLUTA (archivos previos, datos o análisis actual)
    todas_las_fechas = (
        pd.to_datetime(df_journal["Fecha_Deteccion"], errors="coerce").dropna().tolist()
    )
    todas_las_fechas.append(pd.to_datetime(fecha_analisis_norm))
    todas_las_fechas.extend(fechas_historia_files)

    max_fecha_str = max(todas_las_fechas).strftime("%Y%m%d")
    new_filename = f"journal_operaciones_hasta_{max_fecha_str}.csv"

    # 6. Completar Tipo e Icono para todas las entradas (incluyendo históricas sin estos campos)
    for i, row in df_journal.iterrows():
        if pd.isna(row.get("Tipo", pd.NA)) or row.get("Tipo", "") == "":
            estado = str(row["Estado_Actual"])
            if estado == "ABIERTA":
                df_journal.loc[i, "Tipo"] = "🟢 Activo"
                df_journal.loc[i, "Icono"] = "✅"
            elif "VIGILANCIA" in estado:
                df_journal.loc[i, "Tipo"] = "🟡 Alerta"
                df_journal.loc[i, "Icono"] = "⚠️"
            elif estado == "CERRADA (TARGET)":
                df_journal.loc[i, "Tipo"] = "✅ Cerrado"
                df_journal.loc[i, "Icono"] = "🎯"
            elif "CERRADA" in estado:
                df_journal.loc[i, "Tipo"] = "❌ Cerrado"
                df_journal.loc[i, "Icono"] = "🔴"

    # 7. Reordenar columnas para mejor legibilidad (Tipo e Icono después de Estado_Actual)
    col_order = [
        "Fecha_Deteccion",
        "Fecha_Actualizacion",
        "Fecha_Cierre",
        "Ticker",
        "Setup",
        "Precio_Entrada",
        "Stop_Inicial",
        "T1",
        "T2",
        "Estado_Actual",
        "Tipo",
        "Icono",
        "Precio_Ultimo",
        "P&L_%",
    ]
    df_journal = df_journal[col_order]

    # 8. Ordenar por última actualización (y detección como desempate)
    df_journal = df_journal.sort_values(
        by=["Fecha_Actualizacion", "Fecha_Deteccion"], ascending=False
    ).reset_index(drop=True)

    abs_new = os.path.abspath(new_filename)
    try:
        # Guardar con UTF-8-sig (BOM) para que Excel muestre correctamente los emojis
        df_journal.to_csv(abs_new, index=False, encoding="utf-8-sig")
        print(f"Journal consolidado y actualizado (con alertas): {new_filename}")
    except Exception as e:
        print(f"ERROR: No se pudo guardar el diario {new_filename}: {e}")

    # 9. Persistir journal de eventos (una fila por evento de estado)
    try:
        eventos_reconstruidos = reconstruir_eventos_desde_journals(
            archivos_journal, eventos_cols
        )
        if not eventos_reconstruidos.empty:
            df_eventos = pd.concat(
                [df_eventos, eventos_reconstruidos], ignore_index=True
            )

        df_eventos = normalizar_y_deduplicar_eventos(df_eventos, eventos_cols)

        fechas_eventos = (
            pd.to_datetime(df_eventos["Fecha_Evento"], errors="coerce")
            .dropna()
            .tolist()
            if not df_eventos.empty
            else []
        )
        fechas_eventos.append(pd.to_datetime(fecha_analisis_norm))
        fechas_eventos.extend(fechas_historia_eventos_files)
        max_fecha_eventos_str = max(fechas_eventos).strftime("%Y%m%d")
        eventos_filename = f"journal_eventos_hasta_{max_fecha_eventos_str}.csv"
        abs_eventos = os.path.abspath(eventos_filename)
        eventos_export_cols = columnas_exportacion_eventos(eventos_cols)
        df_eventos[eventos_export_cols].to_csv(
            abs_eventos, index=False, encoding="utf-8-sig"
        )
        print(f"Journal de eventos actualizado: {eventos_filename}")
    except Exception as e:
        print(f"ERROR: No se pudo guardar el journal de eventos: {e}")

    # Normalizar rutas para evitar borrar el archivo que acabamos de guardar.
    # Limitar borrado al directorio actual para no eliminar historicos de runs previos.
    for f in archivos_locales:
        if os.path.exists(f):
            abs_f = os.path.abspath(f)
            if abs_f != abs_new:
                try:
                    os.remove(abs_f)
                except:
                    pass

    # Limpiar journals de eventos antiguos en el directorio actual
    for f in archivos_eventos_locales:
        if os.path.exists(f):
            abs_f = os.path.abspath(f)
            if "abs_eventos" in locals() and abs_f != abs_eventos:
                try:
                    os.remove(abs_f)
                except:
                    pass

    return df_journal


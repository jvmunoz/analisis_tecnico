import os
import glob
import re
from datetime import datetime
from pathlib import Path
import pandas as pd

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
    data_enriquecida, filename="journal_operaciones.csv", fecha_v=""
):
    """
    Registra señales VERDE y hace seguimiento de las existentes.
    Acumula datos de múltiples fechas y se renombra dinámicamente según la fecha máxima analizada.
    """
    cols = [
        "Fecha_Deteccion",
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

    # 1. Identificar y consolidar journals del run actual + historicos de runs previos
    cwd = Path.cwd()
    archivos_locales = sorted(cwd.glob("journal_operaciones*.csv"))
    archivos_journal = {str(p.resolve()) for p in archivos_locales}

    # Buscar carpeta runs en la ruta actual (normalmente .../Prueba/runs/YYYYMMDD)
    runs_root = next((p for p in [cwd, *cwd.parents] if p.name == "runs"), None)
    if runs_root is not None and runs_root.exists():
        for p in runs_root.glob("*/journal_operaciones_hasta_*.csv"):
            archivos_journal.add(str(p.resolve()))

    archivos_journal = sorted(archivos_journal)
    print(f"DEBUG: Archivos de diario encontrados: {archivos_journal}")
    dataframes = []
    fechas_historia_files = []

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

    if dataframes:
        df_journal = pd.concat(dataframes, ignore_index=True)
        df_journal = df_journal.drop_duplicates(
            subset=["Fecha_Deteccion", "Ticker", "Setup"], keep="last"
        )
        df_journal = df_journal.reset_index(drop=True)
    else:
        df_journal = pd.DataFrame(columns=cols)

    fecha_analisis = fecha_v if fecha_v else datetime.now().strftime("%Y-%m-%d")
    fecha_analisis_norm = pd.to_datetime(fecha_analisis).strftime("%Y-%m-%d")

    # 2. Sustitución: Si ya existen señales DETECTADAS el mismo día, las borramos para poner las nuevas del análisis
    if not df_journal.empty:
        df_journal = df_journal[
            df_journal["Fecha_Deteccion"] != fecha_analisis_norm
        ].copy()
        df_journal = df_journal.reset_index(drop=True)

    # 3. Añadir nuevas señales VERDE detectadas hoy
    nuevas_senales = [d for d in data_enriquecida if d["Semaforo"] == "VERDE"]
    for s in nuevas_senales:
        ticker = s["Ticker"]
        if (
            ticker
            not in df_journal[df_journal["Estado_Actual"] == "ABIERTA"]["Ticker"].values
        ):
            nueva_fila = {
                "Fecha_Deteccion": fecha_analisis_norm,
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

    # 8. Ordenar por fecha descendente (más recientes primero) y guardar
    df_journal = df_journal.sort_values(
        by="Fecha_Deteccion", ascending=False
    ).reset_index(drop=True)

    abs_new = os.path.abspath(new_filename)
    try:
        # Guardar con UTF-8-sig (BOM) para que Excel muestre correctamente los emojis
        df_journal.to_csv(abs_new, index=False, encoding="utf-8-sig")
        print(f"Journal consolidado y actualizado (con alertas): {new_filename}")
    except Exception as e:
        print(f"ERROR: No se pudo guardar el diario {new_filename}: {e}")

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

    return df_journal


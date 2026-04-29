import numpy as np
import pandas as pd

from .reports_reportlab import generar_pdfs_enriquecidos_reportlab
from .ibex import SECTORES_IBEX
from .portfolio import gestionar_journal_operaciones
from .reports_matplotlib import generar_heatmap_sectores
from .reports_reportlab import generar_informe_cartera_pdf
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt


def _retorno_ventana(df_viz, close, sesiones):
    if len(df_viz) <= sesiones:
        return 0
    precio_previo = df_viz["close"].iloc[-(sesiones + 1)]
    if precio_previo == 0 or pd.isna(precio_previo):
        return 0
    return close / precio_previo - 1


def _caida_reciente_fuerte(df_viz, last, close, macd_bias):
    ret_5 = _retorno_ventana(df_viz, close, 5)
    ret_10 = _retorno_ventana(df_viz, close, 10)
    return bool(
        close < last["sma_short"]
        and macd_bias == "Baj."
        and (ret_5 <= -0.05 or ret_10 <= -0.08)
    )


def calcular_analisis_enriquecido(lista_datos_completos):
    """
    Traduce las reglas de INSTRUCCIONES_CHATGPT_20251224.txt a lógica determinista de Python.
    """
    analisis_enriquecido = []

    for item in lista_datos_completos:
        ticker = item["ticker"]
        df_viz = item["df_viz"]
        if df_viz is None or df_viz.empty:
            continue

        last = df_viz.iloc[-1]
        close = last["close"]

        # 1. Normalización de inputs
        df_recent = df_viz.tail(60)
        soporte_val = df_recent["low"].min()
        resistencia_val = df_recent["high"].max()

        dist_sop_p = (close / soporte_val - 1) if soporte_val != 0 else 0  # en decimal
        dist_res_p = (resistencia_val / close - 1) if close != 0 else 0  # en decimal

        atr_p = last["atr_perc"] / 100.0  # dacimal
        rsi_val = last["rsi"]

        rsi_flag = None
        if rsi_val > 70:
            rsi_flag = "SC"
        elif rsi_val < 30:
            rsi_flag = "SV"

        adx_val = last["adx"]
        adx_regime = (
            "Trend" if adx_val > 25 else "Lateral" if adx_val < 20 else "Neutral"
        )

        macd_bias = "Alc." if last["macd_histogram"] > 0 else "Baj."
        trend_sma = "Alc." if last["sma_short"] > last["sma_long"] else "Baj."
        rvol = last["rvol"]
        caida_reciente_fuerte = _caida_reciente_fuerte(
            df_viz, last, close, macd_bias
        )

        # 2. Niveles Absolutos (Paso 2)
        sop_est = close * (1 - dist_sop_p)
        res_est = close * (1 + dist_res_p)
        atr_abs = close * atr_p

        # 3. Asignación de Setup (Paso 3)
        breakout_cand = dist_res_p <= 0.03
        pullback_cand = (dist_sop_p <= 0.05) or (rsi_val <= 45) or (rsi_flag == "SV")

        if trend_sma == "Alc." and macd_bias == "Alc." and dist_res_p <= 0.02:
            setup = "Breakout"
        elif pullback_cand:
            setup = "Pullback"
        else:
            setup = "Breakout"

        # 4. Cálculo de Entrada/Stop/T1/T2 (Paso 4)
        if setup == "Breakout":
            entrada = res_est + (0.25 * atr_abs)
            stop_inicial = res_est - (1.00 * atr_abs)
        else:  # Pullback
            entrada = sop_est + (0.50 * atr_abs)
            stop_inicial = sop_est - (1.00 * atr_abs)

        r_risk = entrada - stop_inicial
        t1 = entrada + r_risk
        t2 = entrada + (2.0 * r_risk)

        # Trailing Stop (2.5 * ATR desde el precio actual o máximo reciente)
        # Para señales nuevas, el trailing stop es una referencia de salida dinámica
        trailing_stop = close - (2.5 * atr_abs)

        # 5. Semáforo y Estado (Paso 5)
        semaforo = "AMARILLO"
        estado = "VIGILAR"

        # Reglas Rojas (Deterioro Técnico Real)
        rojo_deterioro = trend_sma == "Baj." and macd_bias == "Baj."

        # Sobrecalentamiento (Evita Verde, pero no es Rojo)
        rojo_sc = rsi_flag == "SC" and dist_res_p <= 0.015

        if rojo_deterioro:
            semaforo = "ROJO"
            estado = "NO EJECUTAR"
        else:
            # Criterios VERDE
            if setup == "Breakout":
                if (
                    trend_sma == "Alc."
                    and macd_bias == "Alc."
                    and adx_regime in ["Trend", "Neutral"]
                    and dist_res_p <= 0.02
                    and rsi_flag != "SC"
                    and rvol >= 0.15
                ):  # Cambiado de 1.15 a 0.15 (instrucciones)
                    semaforo = "VERDE"
                    estado = "EJECUTAR"
            else:  # Pullback
                if (
                    dist_sop_p <= 0.05
                    and adx_regime in ["Trend", "Neutral"]
                    and (rsi_val <= 45 or rsi_flag == "SV")
                    and rvol >= 0.15
                    and not caida_reciente_fuerte
                ):  # Cambiado de 1.15 a 0.15
                    semaforo = "VERDE"
                    estado = "EJECUTAR"

        # 6. Score (Paso 6)
        # A) Dirección (0-4)
        score_a = (2 if trend_sma == "Alc." else 0) + (2 if macd_bias == "Alc." else 0)
        # B) ADX (0-2)
        score_b = 2 if adx_regime == "Trend" else 1 if adx_regime == "Neutral" else 0

        # C) Ubicación (0-2)
        def clamp(v, min_v, max_v):
            return max(min(v, max_v), min_v)

        if setup == "Breakout":
            score_c = 2 * clamp((0.02 - dist_res_p) / 0.02, 0, 1)
        else:
            score_c = 2 * clamp((0.05 - dist_sop_p) / 0.05, 0, 1)
        # D) RSI (0-1)
        score_d = 0
        if setup == "Breakout":
            if 55 <= rsi_val <= 68:
                score_d = 1
            elif (45 <= rsi_val < 55) or (68 < rsi_val <= 70):
                score_d = 0.5
        else:
            if rsi_val <= 35 or rsi_flag == "SV":
                score_d = 1
            elif 35 < rsi_val <= 45:
                score_d = 0.5
        # E) Vol (0-1)
        score_e = (
            1 if rvol >= 0.20 else 0.5 if rvol >= 0.15 else 0
        )  # Cambiado de 1.20 a 0.20

        score_final = round(score_a + score_b + score_c + score_d + score_e, 2)
        if rojo_sc:
            score_final = 4.00

        analisis_enriquecido.append(
            {
                "Ticker": ticker,
                "Precio": round(close, 2),  # Redondeo de precio
                "Semaforo": semaforo,
                "Estado": estado,
                "Setup": setup,
                "Score": score_final,
                "Entrada": round(entrada, 2),
                "Stop": round(stop_inicial, 2),
                "T1": round(t1, 2),
                "T2": round(t2, 2),
                "Trailing_Stop": round(trailing_stop, 2),
                "Inputs": {
                    "dist_sop_p": dist_sop_p,
                    "dist_res_p": dist_res_p,
                    "atr_p": atr_p,
                    "rsi_val": rsi_val,
                    "rsi_flag": rsi_flag,
                    "adx_val": adx_val,
                    "adx_regime": adx_regime,
                    "macd_bias": macd_bias,
                    "trend_sma": trend_sma,
                    "rvol": rvol,
                    "caida_reciente_fuerte": caida_reciente_fuerte,
                },
            }
        )

    return analisis_enriquecido

def calcular_pesos_inversion_enriquecido(
    data_enriquecida, exposicion_total=80.0, cash_pct=20.0
):
    """
    Calcula pesos de inversión basados en Risk Parity (1/distancia).
    """
    BANK_TICKERS = {"BBVA.MC", "SAB.MC", "BKT.MC", "CABK.MC", "SAN.MC", "UNI.MC"}

    ejecutables = [item for item in data_enriquecida if item["Estado"] == "EJECUTAR"]
    if not ejecutables:
        for item in data_enriquecida:
            item["Opción1_W"] = 0
            item["Opción2_W"] = 0
            item["Distancia_stop_pct"] = 0
        return data_enriquecida

    for item in ejecutables:
        dist = (item["Entrada"] - item["Stop"]) / item["Entrada"]
        if dist > 0:
            item["Distancia_stop_pct"] = round(dist * 100, 2)
            item["inv_dist"] = 1.0 / dist
        else:
            item["Distancia_stop_pct"] = 0
            item["inv_dist"] = 0

    sum_inv_dist = sum(item["inv_dist"] for item in ejecutables)

    # Opción 1: Proporcional puro (80%)
    if sum_inv_dist > 0:
        for item in ejecutables:
            item["Opción1_W"] = round(
                (item["inv_dist"] / sum_inv_dist) * exposicion_total, 1
            )
    else:
        for item in ejecutables:
            item["Opción1_W"] = 0

    # Opción 2: Cap Banca 25% (Límite real, no objetivo fijo)
    BANK_TICKERS = {"BBVA.MC", "SAB.MC", "BKT.MC", "CABK.MC", "SAN.MC", "UNI.MC"}
    banca = [item for item in ejecutables if item["Ticker"].upper() in BANK_TICKERS]
    no_banca = [
        item for item in ejecutables if item["Ticker"].upper() not in BANK_TICKERS
    ]

    # 1. Verificamos el peso natural de la banca en la Opción 1
    peso_natural_banca = sum(item["Opción1_W"] for item in banca)

    if peso_natural_banca > 25.0 and no_banca:
        # Solo aplicamos el CAP si la banca supera el 25% y hay otros activos
        sum_banca = sum(item["inv_dist"] for item in banca)
        sum_no_banca = sum(item["inv_dist"] for item in no_banca)

        # Reparto: Banca se queda en el 25% exacto
        for item in banca:
            item["Opción2_W"] = round((item["inv_dist"] / sum_banca) * 25.0, 1)

        # El resto (75%) se reparte entre los no banca para llegar al 80% total exposure
        # En realidad es (80 - 25) = 55% para los no banca
        target_no_banca = exposicion_total - 25.0
        for item in no_banca:
            item["Opción2_W"] = round(
                (item["inv_dist"] / sum_no_banca) * target_no_banca, 1
            )
    else:
        # Si la banca no llega al 25%, la Opción 2 es igual a la Opción 1
        for item in ejecutables:
            item["Opción2_W"] = item["Opción1_W"]

    # Rellenar ceros para el resto
    for item in data_enriquecida:
        if item["Estado"] != "EJECUTAR":
            item["Opción1_W"] = 0
            item["Opción2_W"] = 0
            item["Distancia_stop_pct"] = 0

    return data_enriquecida

def ejecutar_flujo_enriquecido_completo(
    lista_datos_completos,
    fecha_v,
    tickers_cartera=[],
    df_cartera=pd.DataFrame(),
    df_log_completo=pd.DataFrame(),
):
    """
    Orquestador principal del análisis enriquecido determinista.
    """
    print("\n" + "=" * 80)
    print("INICIANDO ANÁLISIS ENRIQUECIDO DETERMINISTA (SIN ALEATORIEDAD)")
    print("=" * 80)

    # 1. Calcular Amplitud de Mercado
    breadth_val, exposure_goal = calcular_amplitud_mercado(lista_datos_completos)
    print(
        f"Amplitud de Mercado: {breadth_val}% (Exposición objetivo: {exposure_goal}%)"
    )

    # 2. Calcular todo nativamente en Python
    data_enriquecida = calcular_analisis_enriquecido(lista_datos_completos)

    # 3. Calcular pesos dinámicos según Amplitud
    data_enriquecida = calcular_pesos_inversion_enriquecido(
        data_enriquecida, exposicion_total=exposure_goal, cash_pct=100.0 - exposure_goal
    )

    # 4. Calcular Correlaciones
    alertas_corr = calcular_correlaciones_ejecutables(
        lista_datos_completos, data_enriquecida
    )

    # 5. Gestionar Journal de Operaciones (Persistencia y Seguimiento)
    gestionar_journal_operaciones(data_enriquecida, fecha_v=fecha_v)

    # 6. Generar Heatmap Sectorial
    heatmap_path = "heatmap_sectores.png"
    generar_heatmap_sectores(data_enriquecida, filename=heatmap_path)

    # 7. Generar Informe de Cartera Personal (si existe)
    if not df_cartera.empty:
        generar_informe_cartera_pdf(
            data_enriquecida,
            df_cartera,
            lista_datos_completos,
            df_log_completo,
            fecha_ult=fecha_v,
        )

    # 8. Generar PDFs Enriquecidos
    generar_pdfs_enriquecidos_reportlab(
        data_enriquecida,
        fecha_ult=fecha_v,
        breadth=(breadth_val, exposure_goal),
        exposure=exposure_goal,
        alertas_corr=alertas_corr,
        heatmap=heatmap_path,
        portfolio_tickers=tickers_cartera,
    )

    print("=" * 80 + "\n")


# ==============================================================================
# FUNCIÓN 4: ORQUESTADOR DEL ANÁLISIS INDIVIDUAL
# ==============================================================================

def generar_recomendacion_perfiles(
    metricas_globales,
    nombres_tickers={},
    capital_inicial=10000,
    fecha_ult="",
    portfolio_tickers=[],
    lista_datos_completos=None,
):
    """
    Genera recomendaciones de inversión para 3 perfiles: Conservador, Neutral y Agresivo
    basadas en filtros de riesgo y asignación por paridad de riesgo (inversa de la volatilidad).
    """
    suffix = f"_{fecha_ult.replace('-', '')}" if fecha_ult else ""
    filename = f"INFORME_RECOMENDACION_PERFILES{suffix}.pdf"
    print(f"\nGenerando recomendación por perfiles: {filename}...")

    perfiles = {
        "Conservador": {
            "min_sharpe": 0.60,
            "max_vol": 0.20,
            "max_dd": -0.20,
            "max_weight": 0.45,
            "sector_cap": 0.35,
            "vol_target": 0.12,
            "corr_max": 0.85,
        },
        "Neutral": {
            "min_sharpe": 0.50,
            "max_vol": 0.30,
            "max_dd": -0.35,
            "max_weight": 0.55,
            "sector_cap": 0.45,
            "vol_target": 0.18,
            "corr_max": 0.85,
        },
        "Agresivo": {
            "min_sharpe": 0.40,
            "max_vol": 0.40,
            "max_dd": -0.50,
            "max_weight": 0.65,
            "sector_cap": 0.55,
            "vol_target": 0.25,
            "corr_max": 0.85,
        },
    }

    with PdfPages(filename) as pdf:
        def _get_metric_any(metricas, *keys, default=0):
            for k in keys:
                if k in metricas:
                    v = metricas.get(k)
                    if v is not None:
                        return v
                try:
                    k_mojibake = str(k).encode("utf-8").decode("latin-1")
                    if k_mojibake in metricas:
                        v = metricas.get(k_mojibake)
                        if v is not None:
                            return v
                except Exception:
                    pass
            return default

        for nombre_perfil, criterios in perfiles.items():
            print(f"  -> Procesando perfil {nombre_perfil}...")

            # 1. Filtrar candidatos
            candidatos = []

            for item in metricas_globales:
                ticker = item["ticker"]
                # EXCLUIR IBEX
                if "IBEX" in ticker.upper() or "^" in ticker:
                    continue

                m = item["metricas"]
                sharpe_c = _get_metric_any(m, "Ratio de Sharpe_Combinada", default=0)
                vol_c = _get_metric_any(m, "Volatilidad_Combinada", default=0)
                sharpe_m = _get_metric_any(m, "Sharpe Mercado", default=0)
                vol_m = _get_metric_any(m, "Volatilidad Mercado", default=0)
                dd_c = _get_metric_any(m, "Máximo Drawdown_Combinada", default=0)
                dd_m = _get_metric_any(m, "Máximo Drawdown Mercado", default=0)
                cagr_c = _get_metric_any(m, "CAGR_Combinada", default=0)
                cagr_m = _get_metric_any(m, "CAGR Mercado", default=0)

                if (
                    sharpe_c >= criterios["min_sharpe"]
                    and vol_c <= criterios["max_vol"]
                    and dd_c >= criterios["max_dd"]
                ):  # DD es negativo, mayor es mas cercano a 0
                    # Obtener estados de las estrategias
                    ops = item.get("operaciones", [])
                    estados_list = []
                    for op in ops:
                        short_name = op["Estrategia"][0]  # T, B, R, M
                        status_short = "Act" if op["Estado"] == "Activo" else "Ina"
                        estados_list.append(f"{short_name}:{status_short}")

                    # Dividir en 2 líneas de 2 estrategias para que ocupe menos ancho
                    if len(estados_list) >= 4:
                        estados_str = f"{estados_list[0]}, {estados_list[1]}\n{estados_list[2]}, {estados_list[3]}"
                    else:
                        estados_str = ", ".join(estados_list)

                    candidatos.append(
                        {
                            "Ticker": ticker,
                            "Display_Ticker": f"{ticker} [C]"
                            if ticker in portfolio_tickers
                            else ticker,
                            "Sharpe": sharpe_c,
                            "Sharpe_Mercado": sharpe_m,
                            "Volatilidad": vol_c,
                            "Volatilidad_Mercado": vol_m,
                            "Drawdown": dd_c,
                            "Drawdown_Mercado": dd_m,
                            "CAGR": cagr_c,
                            "CAGR_Mercado": cagr_m,
                            "Precio": item.get("precio_actual", 0),
                            "Estados": estados_str,
                        }
                    )

            # 2. DEFINIR MÉTODO DE ORDENACIÓN (RANKING)
            criterio_ranking = ""
            if nombre_perfil == "Conservador":
                # Prioriza Ratio de Calmar (CAGR / |MaxDD|) - Eficiencia en la recuperación
                for c in candidatos:
                    dd_abs = abs(c["Drawdown"]) if c["Drawdown"] != 0 else 0.001
                    c["Calmar"] = c["CAGR"] / dd_abs
                candidatos.sort(key=lambda x: x["Calmar"], reverse=True)
                criterio_ranking = "Ratio de Calmar (Rentabilidad/Riesgo DD)"
            elif nombre_perfil == "Neutral":
                # Prioriza MAYOR Sharpe
                candidatos.sort(key=lambda x: x["Sharpe"], reverse=True)
                criterio_ranking = "Mayor Ratio de Sharpe"
            elif nombre_perfil == "Agresivo":
                # Prioriza MAYOR CAGR (Rentabilidad)
                candidatos.sort(key=lambda x: x["CAGR"], reverse=True)
                criterio_ranking = "Mayor Rentabilidad (CAGR)"

            alertas_corr = []
            if lista_datos_completos:
                candidatos, alertas_corr = _filtrar_por_correlacion(
                    candidatos,
                    lista_datos_completos,
                    corr_max=criterios.get("corr_max", 0.85),
                    window=60,
                )

            # LIMITE: MÁXIMO 3 VALORES
            if len(candidatos) > 3:
                candidatos = candidatos[:3]

            fig = plt.figure(figsize=(10, 7), dpi=72)
            title = f"Recomendación de Cartera: Perfil {nombre_perfil} (Capital: {capital_inicial}€)"
            if fecha_ult:
                title += f" (Datos hasta {fecha_ult})"
            fig.suptitle(title, fontsize=16, y=0.95)

            # Metodología texto
            metodologia_texto = ""
            if nombre_perfil == "Conservador":
                metodologia_texto = "- Paridad de Riesgo (Inversa a la Volatilidad)\n- Activos menos volátiles reciben más capital."
            elif nombre_perfil == "Neutral":
                metodologia_texto = "- Equiponderada (Equal Weight)\n- Todos los activos reciben la misma asignación para diversificar."
            elif nombre_perfil == "Agresivo":
                metodologia_texto = "- Proporcional al CAGR (Rentabilidad)\n- Activos más rentables reciben más capital (Apuesta por crecimiento)."

            # Texto explicativo
            ax_text = fig.add_subplot(211)
            ax_text.axis("off")

            info_text = (
                f"Criterios de Selección ({nombre_perfil}):\n"
                f"- Ratio de Sharpe > {criterios['min_sharpe']}\n"
                f"- Volatilidad Anual < {criterios['max_vol']:.1%}\n"
                f"- Máximo Drawdown Histórico > {criterios['max_dd']:.1%}\n"
                f"- SELECCIÓN: Top {len(candidatos)} activos por {criterio_ranking} (Excl. Índices)\n"
                f"- Límites: peso máx {criterios['max_weight']:.0%}, sector máx {criterios['sector_cap']:.0%}\n"
                f"- Control de riesgo: vol objetivo {criterios['vol_target']:.0%}, ATR disponible, ajuste por DD\n"
                f"- Correlación máx: {criterios['corr_max']:.2f}"
                + (f" (excluidos {len(alertas_corr)} activos)" if alertas_corr else "")
                + "\n\n"
                f"Metodología de Asignación:\n"
                f"{metodologia_texto}\n"
                "\nMétricas en tabla: M/C = Mercado / Combinada."
            )
            ax_text.text(0.1, 0.5, info_text, fontsize=12, verticalalignment="center")

            ax_table = fig.add_subplot(212)
            ax_table.axis("off")

            if not candidatos:
                ax_table.text(
                    0.5,
                    0.5,
                    "No se encontraron activos que cumplan los criterios estrictos de este perfil.",
                    horizontalalignment="center",
                    verticalalignment="center",
                    fontsize=14,
                )
            else:
                # 3. CALCULAR PESOS SEGÚN PERFIL
                table_data = []
                total_alloc = 0
                sectores_map = {
                    c["Ticker"]: SECTORES_IBEX.get(c["Ticker"], "Otros")
                    for c in candidatos
                }

                if nombre_perfil == "Conservador":
                    inv_vol_sum = sum(
                        1 / c["Volatilidad"] for c in candidatos if c["Volatilidad"] > 0
                    )
                    pesos = {}
                    if inv_vol_sum > 0:
                        for c in candidatos:
                            pesos[c["Ticker"]] = (
                                (1 / c["Volatilidad"]) / inv_vol_sum
                                if c["Volatilidad"] > 0
                                else 0
                            )
                    else:
                        weight = 1.0 / len(candidatos)
                        for c in candidatos:
                            pesos[c["Ticker"]] = weight

                elif nombre_perfil == "Neutral":
                    weight = 1.0 / len(candidatos)
                    pesos = {c["Ticker"]: weight for c in candidatos}

                elif nombre_perfil == "Agresivo":
                    cagr_sum = sum(max(0, c["CAGR"]) for c in candidatos)
                    pesos = {}
                    if cagr_sum <= 0:
                        weight = 1.0 / len(candidatos)
                        for c in candidatos:
                            pesos[c["Ticker"]] = weight
                    else:
                        for c in candidatos:
                            pesos[c["Ticker"]] = max(0, c["CAGR"]) / cagr_sum

                pesos = _aplicar_cap_maximo(pesos, criterios.get("max_weight"))
                pesos = _aplicar_cap_sector(
                    pesos, sectores_map, criterios.get("sector_cap")
                )

                vol_map = {c["Ticker"]: max(0.0, c["Volatilidad"]) for c in candidatos}
                atr_map = {}
                if lista_datos_completos:
                    candidatos_set = set(vol_map.keys())
                    for item in lista_datos_completos:
                        t = item.get("ticker")
                        if t in candidatos_set:
                            df_viz = item.get("df_viz")
                            if (
                                df_viz is not None
                                and not df_viz.empty
                                and "atr_pct" in df_viz.columns
                            ):
                                atr_val = df_viz["atr_pct"].iloc[-1]
                                if not np.isnan(atr_val):
                                    atr_map[t] = float(atr_val)

                for t in list(vol_map.keys()):
                    if t in atr_map:
                        atr_ann = atr_map[t] * np.sqrt(252)
                        vol_map[t] = max(vol_map[t], atr_ann)
                dd_vals = [
                    abs(c["Drawdown"]) for c in candidatos if c["Drawdown"] is not None
                ]
                dd_limit = abs(criterios.get("max_dd", 0))
                avg_dd = np.mean(dd_vals) if dd_vals else 0.0
                dd_factor = 1.0
                if dd_limit > 0 and avg_dd > 0:
                    dd_factor = max(0.7, 1.0 - 0.3 * (avg_dd / dd_limit))

                expected_vol = sum(
                    pesos.get(t, 0.0) * vol_map.get(t, 0.0) for t in pesos
                )
                vol_target = criterios.get("vol_target", 0.0)
                vol_factor = 1.0
                if expected_vol > 0 and vol_target > 0:
                    vol_factor = min(1.0, vol_target / expected_vol)

                exposure_factor = vol_factor * dd_factor
                for t in list(pesos.keys()):
                    pesos[t] = pesos[t] * exposure_factor

                cash_weight = max(0.0, 1.0 - sum(pesos.values()))

                # Generar filas tabla
                for c in candidatos:
                    c["Peso"] = pesos.get(c["Ticker"], 0.0)
                    allocation = capital_inicial * c["Peso"]
                    c["Asignacion"] = allocation
                    total_alloc += allocation

                    table_data.append(
                        [
                            f"{c['Display_Ticker']}\n{nombres_tickers.get(c['Ticker'], '')[:15]}",
                            f"{c['Precio']:.2f}€",
                            c["Estados"],
                            f"M:{c['CAGR_Mercado']:.2%}\nC:{c['CAGR']:.2%}",
                            f"M:{c['Sharpe_Mercado']:.2f}\nC:{c['Sharpe']:.2f}",
                            f"M:{c['Volatilidad_Mercado']:.2%}\nC:{c['Volatilidad']:.2%}",
                            f"M:{c['Drawdown_Mercado']:.2%}\nC:{c['Drawdown']:.2%}",
                            f"{c['Peso']:.2%}",
                            f"{c['Asignacion']:.2f}€",
                        ]
                    )

                # Ordenar tabla visualmente por peso descendente
                table_data.sort(key=lambda x: float(x[7].strip("%")), reverse=True)

                if cash_weight > 0:
                    table_data.append(
                        [
                            "CASH",
                            "-",
                            "-",
                            "-",
                            "-",
                            "-",
                            "-",
                            f"{cash_weight:.2%}",
                            f"{capital_inicial * cash_weight:.2f}€",
                        ]
                    )

                col_labels = [
                    "Ticker",
                    "Precio",
                    "Estados",
                    "CAGR M/C",
                    "Sharpe M/C",
                    "Vol M/C",
                    "Max. DD M/C",
                    "Peso",
                    "Asigna.",
                ]
                # Ajuste de anchos para columnas M/C en dos lineas.
                col_widths = [0.12, 0.08, 0.16, 0.10, 0.08, 0.10, 0.10, 0.10, 0.12]

                table = ax_table.table(
                    cellText=table_data,
                    colLabels=col_labels,
                    colWidths=col_widths,
                    cellLoc="center",
                    loc="center",
                )
                table.auto_set_font_size(False)
                table.set_fontsize(7.5)
                table.scale(1, 2.5)

            pdf.savefig(fig, dpi=72)
            plt.close(fig)
            import gc

            gc.collect()

    print(f"Informe {filename} generado con éxito.")

def _construir_retornos_candidatos(candidatos, lista_datos_completos, window=60):
    if not lista_datos_completos:
        return {}
    returns_dict = {}
    for c in candidatos:
        ticker = c["Ticker"]
        for item in lista_datos_completos:
            if item.get("ticker") == ticker:
                df_viz = item.get("df_viz")
                if df_viz is not None and not df_viz.empty:
                    closes = df_viz["close"].pct_change().dropna().tail(window)
                    if len(closes) >= 10:
                        returns_dict[ticker] = closes
                break
    return returns_dict

def _filtrar_por_correlacion(
    candidatos, lista_datos_completos, corr_max=0.85, window=60
):
    returns_dict = _construir_retornos_candidatos(
        candidatos, lista_datos_completos, window=window
    )
    if len(returns_dict) < 2:
        return candidatos, []

    df_returns = pd.DataFrame(returns_dict)
    corr_matrix = df_returns.corr()
    cols = list(corr_matrix.columns)
    rank = {c["Ticker"]: i for i, c in enumerate(candidatos)}
    keep = set(cols)
    alertas = []

    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            val = corr_matrix.iloc[i, j]
            if val > corr_max:
                t1, t2 = cols[i], cols[j]
                drop = t1 if rank.get(t1, 0) > rank.get(t2, 0) else t2
                if drop in keep:
                    keep.remove(drop)
                alertas.append({"T1": t1, "T2": t2, "Corr": round(float(val), 2)})

    filtrados = [c for c in candidatos if c["Ticker"] in keep]
    return filtrados, alertas

def _aplicar_cap_maximo(pesos, max_weight):
    pesos = pesos.copy()
    if max_weight is None:
        return pesos

    for _ in range(5):
        exceso = 0.0
        for t in list(pesos.keys()):
            if pesos[t] > max_weight:
                exceso += pesos[t] - max_weight
                pesos[t] = max_weight

        if exceso <= 1e-8:
            break

        elegibles = [t for t, w in pesos.items() if w < max_weight - 1e-8]
        if not elegibles:
            break
        total = sum(pesos[t] for t in elegibles)
        if total <= 0:
            break
        for t in elegibles:
            pesos[t] += exceso * (pesos[t] / total)

    return pesos

def _aplicar_cap_sector(pesos, sectores, sector_cap):
    pesos = pesos.copy()
    if sector_cap is None:
        return pesos

    for _ in range(5):
        sector_weights = {}
        for t, w in pesos.items():
            sector = sectores.get(t, "Otros")
            sector_weights[sector] = sector_weights.get(sector, 0.0) + w

        exceso = 0.0
        for sector, w in sector_weights.items():
            if w > sector_cap:
                factor = sector_cap / w
                for t in list(pesos.keys()):
                    if sectores.get(t, "Otros") == sector:
                        new_w = pesos[t] * factor
                        exceso += pesos[t] - new_w
                        pesos[t] = new_w

        if exceso <= 1e-8:
            break

        elegibles = []
        for t in pesos:
            sector = sectores.get(t, "Otros")
            if sector_weights.get(sector, 0.0) < sector_cap - 1e-8:
                elegibles.append(t)
        if not elegibles:
            break
        total = sum(pesos[t] for t in elegibles)
        if total <= 0:
            break
        for t in elegibles:
            pesos[t] += exceso * (pesos[t] / total)

    return pesos

def calcular_amplitud_mercado(lista_datos_completos):
    """
    Calcula el % de valores del IBEX que están por encima de su SMA 200.
    """
    total = 0
    encima = 0
    for item in lista_datos_completos:
        df_viz = item["df_viz"]
        if df_viz is not None and not df_viz.empty and "sma_200" in df_viz.columns:
            last_sma = df_viz["sma_200"].iloc[-1]
            if not np.isnan(last_sma):
                total += 1
                if df_viz["close"].iloc[-1] > last_sma:
                    encima += 1

    breadth = (encima / total * 100) if total > 0 else 0

    # Determinar exposición recomendada
    if breadth > 60:
        exposure = 80.0
    elif breadth >= 40:
        exposure = 60.0
    else:
        exposure = 40.0

    return round(breadth, 2), exposure

def calcular_correlaciones_ejecutables(lista_datos_completos, data_enriquecida):
    """
    Analiza la correlación de los últimos 60 días para valores en estado EJECUTAR.
    """
    ejecutables_names = [
        item["Ticker"] for item in data_enriquecida if item["Estado"] == "EJECUTAR"
    ]
    if len(ejecutables_names) < 2:
        return []

    returns_dict = {}
    for ticker in ejecutables_names:
        for item in lista_datos_completos:
            if item["ticker"] == ticker:
                df_viz = item["df_viz"]
                if df_viz is not None and not df_viz.empty:
                    closes = df_viz["close"].tail(60)
                    if len(closes) >= 10:
                        returns_dict[ticker] = closes.pct_change()
                break

    if len(returns_dict) < 2:
        return []

    df_returns = pd.DataFrame(returns_dict)
    corr_matrix = df_returns.corr()

    alertas_corr = []
    tickers = corr_matrix.columns
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            val = corr_matrix.iloc[i, j]
            if val > 0.85:
                alertas_corr.append(
                    {"T1": tickers[i], "T2": tickers[j], "Corr": round(val, 2)}
                )
    return alertas_corr

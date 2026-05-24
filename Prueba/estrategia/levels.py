import pandas as pd


SR_WINDOWS = (20, 60, 120)


def calcular_soportes_resistencias(df_viz, close=None, windows=SR_WINDOWS):
    if df_viz is None or df_viz.empty:
        return {}

    last = df_viz.iloc[-1]
    close = last["close"] if close is None else close
    niveles = {}

    for window in windows:
        df_recent = df_viz.tail(window)
        soporte = df_recent["low"].min()
        resistencia = df_recent["high"].max()
        niveles[f"Soporte_{window}"] = soporte
        niveles[f"Resistencia_{window}"] = resistencia
        niveles[f"Dist_Soporte_{window}_%"] = (
            (close / soporte - 1) * 100 if soporte != 0 and not pd.isna(soporte) else 0
        )
        niveles[f"Dist_Resistencia_{window}_%"] = (
            (resistencia / close - 1) * 100
            if close != 0 and not pd.isna(resistencia)
            else 0
        )

    return niveles


def rompe_soporte_previo(df_viz, close, window=20):
    if df_viz is None or len(df_viz) <= 1:
        return False
    soporte_previo = df_viz.iloc[:-1].tail(window)["low"].min()
    if pd.isna(soporte_previo):
        return False
    return bool(close < soporte_previo)


def ajustar_targets_por_resistencias(entrada, stop, niveles_sr):
    riesgo = entrada - stop
    t1_riesgo = entrada + riesgo
    t2_riesgo = entrada + (2.0 * riesgo)
    if riesgo <= 0:
        return t1_riesgo, t2_riesgo, "Riesgo", "Riesgo"

    resistencias = sorted(
        {
            float(niveles_sr.get(f"Resistencia_{window}"))
            for window in SR_WINDOWS
            if not pd.isna(niveles_sr.get(f"Resistencia_{window}"))
            and float(niveles_sr.get(f"Resistencia_{window}")) > entrada
        }
    )

    def _elegir_objetivo(target_riesgo, min_r, max_r, minimo=None):
        candidatos = []
        for resistencia in resistencias:
            if minimo is not None and resistencia <= minimo:
                continue
            multiple_r = (resistencia - entrada) / riesgo
            if min_r <= multiple_r <= max_r:
                candidatos.append((abs(resistencia - target_riesgo), resistencia))
        if not candidatos:
            return target_riesgo, "Riesgo"
        return min(candidatos)[1], "Resistencia"

    t1, metodo_t1 = _elegir_objetivo(t1_riesgo, 0.7, 1.5)
    t2, metodo_t2 = _elegir_objetivo(t2_riesgo, 1.3, 2.8, minimo=t1)
    return t1, t2, metodo_t1, metodo_t2

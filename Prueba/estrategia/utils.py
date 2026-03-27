import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

def normalizar_nombre_archivo(texto):
    return "".join([c if c.isalnum() else "_" for c in str(texto)])

def generar_heatmap_en_ax(
    ax, x_vals, y_vals, matriz, titulo, xlabel, ylabel, metric_label
):
    if np.all(np.isnan(matriz)):
        ax.text(0.5, 0.5, "Datos insuficientes", ha="center", va="center")
        return
    im = ax.imshow(matriz, aspect="auto", origin="lower", cmap="viridis")
    ax.set_xticks(range(len(x_vals)))
    ax.set_xticklabels(x_vals, fontsize=8)
    ax.set_yticks(range(len(y_vals)))
    ax.set_yticklabels(y_vals, fontsize=8)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_title(titulo, fontsize=10, fontweight="bold")
    plt.colorbar(im, ax=ax)

def analizar_matriz_heatmap(matriz, x_vals=None, y_vals=None):
    """
    Devuelve estadísticas clave de una matriz de sensibilidad.
    Si se proporcionan x_vals e y_vals, también devuelve los parámetros óptimos.
    """
    valid_vals = matriz[~np.isnan(matriz)]
    if len(valid_vals) == 0:
        return {"max": 0, "mean": 0, "std": 0, "robustness": 0, "best_params": None}

    max_val = np.max(valid_vals)
    mean_val = np.mean(valid_vals)
    std_val = np.std(valid_vals)

    # Robustez: % de configuraciones que tienen un Sharpe decente (> 70% del maximo o > 0.5 absoluto)
    thresh = max(0.5, max_val * 0.7)
    robust_count = np.sum(valid_vals >= thresh)
    robustness = robust_count / len(valid_vals)

    # Encontrar coordenadas del máximo
    best_params = None
    if x_vals is not None and y_vals is not None:
        max_idx = np.unravel_index(np.nanargmax(matriz), matriz.shape)
        # max_idx es (i, j) donde i=fila (y), j=columna (x)
        best_y = y_vals[max_idx[0]] if max_idx[0] < len(y_vals) else None
        best_x = x_vals[max_idx[1]] if max_idx[1] < len(x_vals) else None
        if best_x is not None and best_y is not None:
            best_params = {"x": best_x, "y": best_y}

    return {
        "max": max_val,
        "mean": mean_val,
        "std": std_val,
        "robustness": robustness,
        "best_params": best_params,
    }

def generar_conclusion_texto(metricas):
    lines = []

    # 1. Análisis de Eficiencia (Sharpe)
    sharpe_comb = metricas.get("Ratio de Sharpe_Combinada", 0)
    sharpe_mkt = metricas.get("Sharpe Mercado", 0)
    if sharpe_comb > 1.5:
        eff_status = "EXCELENTE"
    elif sharpe_comb > 1.0:
        eff_status = "BUENA"
    elif sharpe_comb > 0.5:
        eff_status = "ACEPTABLE"
    else:
        eff_status = "DEFICIENTE"

    comp_mkt = "SUPERIOR" if sharpe_comb > sharpe_mkt else "INFERIOR"
    lines.append(
        f"<b>Eficiencia Global:</b> La estrategia muestra una eficiencia <b>{eff_status}</b> (Sharpe {sharpe_comb:.2f}), siendo <b>{comp_mkt}</b> al mercado ({sharpe_mkt:.2f})."
    )

    # 2. Perfil de Riesgo (Drawdown & VaR)
    dd_comb = metricas.get("Máximo Drawdown_Combinada", 0)
    var_95 = metricas.get("VaR 95_Combinada", 0)
    if abs(dd_comb) < 0.15:
        risk_profile = "MUY CONSERVADOR"
    elif abs(dd_comb) < 0.25:
        risk_profile = "MODERADO"
    else:
        risk_profile = "AGRESIVO/ALTO RIESGO"

    lines.append(
        f"<b>Perfil de Riesgo:</b> {risk_profile}. El sistema ha contenido las caídas en un máximo del <b>{dd_comb:.1%}</b>. "
        f"En un escenario diario adverso (VaR 95%), se espera perder un <b>{var_95:.2%}</b>."
    )

    # 3. Estilo de Trading (Win Rate vs Profit Factor)
    win_rate = metricas.get(
        "Win Rate_Tendencia", 0
    )  # Usamos Tendencia como proxy de "estilo direccional"
    pf = metricas.get("Profit Factor_Tendencia", 0)

    if win_rate < 0.40 and pf > 1.5:
        style = "TENDENCIAL PURO (Cazador de olas)"
        desc = "baja tasa de aciertos pero grandes beneficios cuando gana"
    elif win_rate > 0.60:
        style = "REVERSION/PRECISIÓN"
        desc = "alta tasa de aciertos con beneficios más moderados"
    else:
        style = "HÍBRIDO/EQUILIBRADO"
        desc = "un equilibrio entre frecuencia de aciertos y magnitud de ganancia"

    lines.append(
        f"<b>Estilo Operativo:</b> Se comporta como un sistema <b>{style}</b>, caracterizado por tener {desc}. "
        f"(Profit Factor Tendencia: {pf:.2f})."
    )

    # 4. Aportación de Estrategias
    sharpes = {
        "Tendencia": metricas.get("Ratio de Sharpe_Tendencia", -99),
        "Bollinger": metricas.get("Ratio de Sharpe_Bollinger", -99),
        "RSI": metricas.get("Ratio de Sharpe_RSI", -99),
        "MACD": metricas.get("Ratio de Sharpe_MACD", -99),
    }
    best_strat = max(sharpes, key=sharpes.get)
    worst_strat = min(sharpes, key=sharpes.get)
    try:
        val_best = sharpes[best_strat]
        if val_best > -90:
            lines.append(
                f"<b>Contribución:</b> La estrategia estrella es <b>{best_strat}</b> (Sharpe {val_best:.2f}), "
                f"mientras que <b>{worst_strat}</b> es la que más lastra el conjunto."
            )
    except:
        pass

    return "<br/>".join(lines)

def generar_conclusion_sensibilidad(stats_dict):
    """
    Genera un texto de conclusiones basado en las estadisticas de las 4 estrategias.
    stats_dict: {'Tendencia': stats, 'Bollinger': stats, ...}
    """
    lines = []

    # 1. Identificar la mejor estrategia (potencial maximo)
    best_strat = max(stats_dict, key=lambda k: stats_dict[k]["max"])
    best_val = stats_dict[best_strat]["max"]

    # 2. Identificar la estrategia mas robusta
    most_stable = max(stats_dict, key=lambda k: stats_dict[k]["robustness"])
    stable_val = stats_dict[most_stable]["robustness"]

    lines.append(
        f"Potencial M\u00e1ximo: {best_strat} (Sharpe m\u00e1x: {best_val:.2f})"
    )

    if stable_val > 0.4:
        stab_desc = "muy noble" if stable_val > 0.7 else "bastante estable"
        lines.append(
            f"Estabilidad: {most_stable} ({stab_desc}, Robustez: {stable_val:.0%})"
        )
    else:
        lines.append(
            "Estabilidad: Resultados sensibles a par\u00e1metros. Se recomienda optimizaci\u00f3n precisa"
        )

    # 3. Advertencias
    warnings = []
    for strat, s in stats_dict.items():
        if s["max"] < 0.2:
            warnings.append(f"{strat} (d\u00e9bil)")
        elif s["std"] > 0.5:
            warnings.append(f"{strat} (inestable)")

    if warnings:
        clean_warns = ", ".join(warnings)
        lines.append(f"Atenci\u00f3n: Revisar {clean_warns}")

    return "\n".join(lines)

def generar_conclusion_global_sensibilidad(all_ticker_stats):
    """
    Genera conclusiones globales agregando estadísticas de todos los tickers.
    all_ticker_stats: lista de dicts con {'Ticker': ticker, 'Tendencia': stats, ...}
    Retorna un dict con recomendaciones de parámetros y pesos.
    """
    if not all_ticker_stats:
        return None

    # Agregar estadísticas por estrategia
    estrategias = ["Tendencia", "Bollinger", "RSI", "MACD"]
    global_stats = {}

    for estrat in estrategias:
        sharpes_max = []
        robustness = []
        params_x = []
        params_y = []
        fixed_params = []  # Para RSI window y MACD signal

        for ticker_data in all_ticker_stats:
            st = ticker_data.get(estrat, {})
            if st.get("max", 0) > 0:  # Solo considerar tickers con datos válidos
                sharpes_max.append(st.get("max", 0))
                robustness.append(st.get("robustness", 0))

                # Capturar parámetros óptimos
                best_params = st.get("best_params")
                if best_params:
                    params_x.append(best_params["x"])
                    params_y.append(best_params["y"])

                # Capturar parámetros fijos (solo para RSI y MACD)
                if estrat == "RSI" and "fixed_window" in st:
                    fixed_params.append(st["fixed_window"])
                elif estrat == "MACD" and "fixed_signal" in st:
                    fixed_params.append(st["fixed_signal"])

        if sharpes_max:
            # Calcular medianas de los parámetros
            median_x = int(np.median(params_x)) if params_x else None
            median_y = int(np.median(params_y)) if params_y else None
            median_fixed = int(np.median(fixed_params)) if fixed_params else None

            global_stats[estrat] = {
                "sharpe_promedio": np.mean(sharpes_max),
                "sharpe_mediano": np.median(sharpes_max),
                "robustez_promedio": np.mean(robustness),
                "n_tickers": len(sharpes_max),
                "param_x_median": median_x,
                "param_y_median": median_y,
                "param_fixed_median": median_fixed,  # Nueva clave
            }
        else:
            global_stats[estrat] = {
                "sharpe_promedio": 0,
                "sharpe_mediano": 0,
                "robustez_promedio": 0,
                "n_tickers": 0,
                "param_x_median": None,
                "param_y_median": None,
            }

    # Calcular ponderaciones recomendadas
    # Fórmula: peso = (sharpe_normalizado * 0.6) + (robustez_normalizada * 0.4)
    scores = {}
    for estrat, stats in global_stats.items():
        score = (stats["sharpe_promedio"] * 0.6) + (stats["robustez_promedio"] * 0.4)
        scores[estrat] = max(score, 0)  # No permitir negativos

    total_score = sum(scores.values())
    if total_score > 0:
        pesos_recomendados = {k.lower(): v / total_score for k, v in scores.items()}
    else:
        pesos_recomendados = {k.lower(): 0.25 for k in estrategias}

    return {"global_stats": global_stats, "pesos_recomendados": pesos_recomendados}

def _to_serializable(obj):
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    if isinstance(obj, pd.Timestamp):
        return obj.strftime("%Y-%m-%d")
    return obj



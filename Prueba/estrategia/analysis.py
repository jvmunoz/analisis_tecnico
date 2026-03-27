import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from .strategies import (
    analizar_tendencia,
    analizar_reversion_bollinger,
    analizar_reversion_rsi,
    analizar_macd,
    ejecutar_analisis_completo_individual,
)
from .utils import (
    generar_heatmap_en_ax,
    analizar_matriz_heatmap,
    generar_conclusion_sensibilidad,
    generar_conclusion_global_sensibilidad,
)
from .metrics import bootstrap_metricas_returns

def seleccionar_tickers_avanzado(lista_tickers, tickers_cartera, max_tickers=8):
    tickers_filtrados = [
        t for t in lista_tickers if "^" not in t and "IBEX" not in t.upper()
    ]
    preferidos = [t for t in tickers_cartera if t in tickers_filtrados]
    resto = [t for t in tickers_filtrados if t not in preferidos]
    seleccion = preferidos + resto
    return seleccion[:max_tickers]

def optimizar_parametros_estrategias(
    df_ticker,
    grids,
    costes_transaccion,
    execution_delay=1,
    slippage_bps=0.0,
    slippage_atr_mult=0.0,
    slippage_vol_mult=0.0,
    metric_key="Ratio de Sharpe",
):
    best_params = {}
    best_scores = {}

    def evaluar(score, params, estrategia):
        if score is None:
            return
        if isinstance(score, (float, np.floating)) and np.isnan(score):
            return
        if estrategia not in best_scores or score > best_scores[estrategia]:
            best_scores[estrategia] = score
            best_params[estrategia] = params

    for short_w in grids["tendencia"]["short_window"]:
        for long_w in grids["tendencia"]["long_window"]:
            if short_w >= long_w:
                continue
            params = {"short_window": short_w, "long_window": long_w}
            try:
                _, met = analizar_tendencia(
                    df_ticker,
                    **params,
                    costes_transaccion=costes_transaccion,
                    execution_delay=execution_delay,
                    slippage_bps=slippage_bps,
                    slippage_atr_mult=slippage_atr_mult,
                    slippage_vol_mult=slippage_vol_mult,
                )
                score = met.get(metric_key, np.nan)
                evaluar(score, params, "tendencia")
            except Exception:
                continue

    for window in grids["bollinger"]["window"]:
        for num_std in grids["bollinger"]["num_std_dev"]:
            params = {"window": window, "num_std_dev": num_std}
            try:
                _, met = analizar_reversion_bollinger(
                    df_ticker,
                    **params,
                    costes_transaccion=costes_transaccion,
                    execution_delay=execution_delay,
                    slippage_bps=slippage_bps,
                    slippage_atr_mult=slippage_atr_mult,
                    slippage_vol_mult=slippage_vol_mult,
                )
                score = met.get(metric_key, np.nan)
                evaluar(score, params, "bollinger")
            except Exception:
                continue

    for window in grids["rsi"]["window"]:
        for umbral_compra in grids["rsi"]["umbral_compra"]:
            for umbral_salida in grids["rsi"]["umbral_salida"]:
                if umbral_salida <= umbral_compra:
                    continue
                params = {
                    "window": window,
                    "umbral_compra": umbral_compra,
                    "umbral_salida": umbral_salida,
                }
                try:
                    _, met = analizar_reversion_rsi(
                        df_ticker,
                        **params,
                        costes_transaccion=costes_transaccion,
                        execution_delay=execution_delay,
                        slippage_bps=slippage_bps,
                        slippage_atr_mult=slippage_atr_mult,
                        slippage_vol_mult=slippage_vol_mult,
                    )
                    score = met.get(metric_key, np.nan)
                    evaluar(score, params, "rsi")
                except Exception:
                    continue

    for fast_p in grids["macd"]["fast_period"]:
        for slow_p in grids["macd"]["slow_period"]:
            if fast_p >= slow_p:
                continue
            for signal_p in grids["macd"]["signal_period"]:
                params = {
                    "fast_period": fast_p,
                    "slow_period": slow_p,
                    "signal_period": signal_p,
                }
                try:
                    _, met = analizar_macd(
                        df_ticker,
                        **params,
                        costes_transaccion=costes_transaccion,
                        execution_delay=execution_delay,
                        slippage_bps=slippage_bps,
                        slippage_atr_mult=slippage_atr_mult,
                        slippage_vol_mult=slippage_vol_mult,
                    )
                    score = met.get(metric_key, np.nan)
                    evaluar(score, params, "macd")
                except Exception:
                    continue

    return best_params, best_scores

def generar_splits_walk_forward(
    index, train_years=3, test_years=1, step_years=1, min_rows=200
):
    splits = []
    if index is None or len(index) == 0:
        return splits

    start = index.min()
    end = index.max()
    while True:
        train_end = start + pd.DateOffset(years=train_years)
        test_end = train_end + pd.DateOffset(years=test_years)
        if test_end > end:
            break

        train_mask = (index >= start) & (index < train_end)
        test_mask = (index >= train_end) & (index < test_end)

        if train_mask.sum() >= min_rows and test_mask.sum() >= min_rows:
            splits.append(
                {
                    "train_start": start,
                    "train_end": train_end,
                    "test_start": train_end,
                    "test_end": test_end,
                    "train_mask": train_mask,
                    "test_mask": test_mask,
                }
            )

        start = start + pd.DateOffset(years=step_years)

    return splits

def ejecutar_walk_forward_ticker(
    df_ticker,
    ticker,
    grids,
    costes_transaccion,
    pesos_estrategias,
    execution_delay=1,
    slippage_bps=0.0,
    slippage_atr_mult=0.0,
    slippage_vol_mult=0.0,
    train_years=3,
    test_years=1,
    step_years=1,
    metric_key="Ratio de Sharpe",
):
    resultados = []
    if df_ticker.empty:
        return resultados

    df_idx = df_ticker.copy().set_index("date").sort_index()
    splits = generar_splits_walk_forward(
        df_idx.index,
        train_years=train_years,
        test_years=test_years,
        step_years=step_years,
    )
    if not splits:
        return resultados

    for idx, split in enumerate(splits, start=1):
        df_train = df_idx.loc[split["train_mask"]].reset_index()
        df_test = df_idx.loc[split["test_mask"]].reset_index()

        best_params, _ = optimizar_parametros_estrategias(
            df_train,
            grids,
            costes_transaccion,
            execution_delay=execution_delay,
            slippage_bps=slippage_bps,
            slippage_atr_mult=slippage_atr_mult,
            slippage_vol_mult=slippage_vol_mult,
            metric_key=metric_key,
        )
        params_t = best_params.get("tendencia", grids["default"]["tendencia"])
        params_b = best_params.get("bollinger", grids["default"]["bollinger"])
        params_r = best_params.get("rsi", grids["default"]["rsi"])
        params_m = best_params.get("macd", grids["default"]["macd"])

        df_train_viz, met_train = ejecutar_analisis_completo_individual(
            df_train,
            params_t,
            params_b,
            params_r,
            params_m,
            costes_transaccion,
            pesos_estrategias,
            execution_delay=execution_delay,
            slippage_bps=slippage_bps,
            slippage_atr_mult=slippage_atr_mult,
            slippage_vol_mult=slippage_vol_mult,
        )
        df_test_viz, met_test = ejecutar_analisis_completo_individual(
            df_test,
            params_t,
            params_b,
            params_r,
            params_m,
            costes_transaccion,
            pesos_estrategias,
            execution_delay=execution_delay,
            slippage_bps=slippage_bps,
            slippage_atr_mult=slippage_atr_mult,
            slippage_vol_mult=slippage_vol_mult,
        )

        is_sharpe = met_train.get("Ratio de Sharpe_Combinada", 0)
        oos_sharpe = met_test.get("Ratio de Sharpe_Combinada", 0)
        if is_sharpe and not np.isnan(is_sharpe):
            overfit_ratio = oos_sharpe / is_sharpe
        else:
            overfit_ratio = 0

        resultados.append(
            {
                "Ticker": ticker,
                "Split": idx,
                "Train Start": split["train_start"].strftime("%Y-%m-%d"),
                "Train End": split["train_end"].strftime("%Y-%m-%d"),
                "Test Start": split["test_start"].strftime("%Y-%m-%d"),
                "Test End": split["test_end"].strftime("%Y-%m-%d"),
                "IS CAGR": met_train.get("CAGR_Combinada", 0),
                "IS Sharpe": is_sharpe,
                "IS Max DD": met_train.get("MÃ¡ximo Drawdown_Combinada", 0),
                "OOS CAGR": met_test.get("CAGR_Combinada", 0),
                "OOS Sharpe": oos_sharpe,
                "OOS Max DD": met_test.get("MÃ¡ximo Drawdown_Combinada", 0),
                "Overfit Sharpe Ratio": overfit_ratio,
                "Params Tendencia": f"{params_t.get('short_window')}/{params_t.get('long_window')}",
                "Params Bollinger": f"{params_b.get('window')}/{params_b.get('num_std_dev')}",
                "Params RSI": f"{params_r.get('window')}/{params_r.get('umbral_compra')}/{params_r.get('umbral_salida')}",
                "Params MACD": f"{params_m.get('fast_period')}/{params_m.get('slow_period')}/{params_m.get('signal_period')}",
            }
        )

    return resultados

def generar_informe_walk_forward(
    datos_completos,
    tickers,
    grids,
    costes_transaccion,
    pesos_estrategias,
    execution_delay=1,
    slippage_bps=0.0,
    slippage_atr_mult=0.0,
    slippage_vol_mult=0.0,
    fecha_ult="",
    train_years=3,
    test_years=1,
    step_years=1,
    metric_key="Ratio de Sharpe",
):
    if not tickers:
        return

    suffix = f"_{fecha_ult.replace('-', '')}" if fecha_ult else ""
    filename_detalle = f"WALK_FORWARD_OOS{suffix}.csv"
    filename_resumen = f"WALK_FORWARD_RESUMEN{suffix}.csv"

    resultados = []
    print(f"Ejecutando Walk-forward para {len(tickers)} tickers...")
    for idx_t, ticker in enumerate(tickers):
        if idx_t % 2 == 0:
            print(f"  Procesando Walk-forward {idx_t + 1}/{len(tickers)}: {ticker}")
        df_t = datos_completos[
            datos_completos["ticker"].str.lower() == ticker.lower()
        ].copy()
        if df_t.empty:
            continue
        resultados.extend(
            ejecutar_walk_forward_ticker(
                df_t,
                ticker,
                grids,
                costes_transaccion,
                pesos_estrategias,
                execution_delay=execution_delay,
                slippage_bps=slippage_bps,
                slippage_atr_mult=slippage_atr_mult,
                slippage_vol_mult=slippage_vol_mult,
                train_years=train_years,
                test_years=test_years,
                step_years=step_years,
                metric_key=metric_key,
            )
        )

    if not resultados:
        print("Walk-forward: no se pudieron generar splits suficientes.")
        return

    df_res = pd.DataFrame(resultados)
    df_res.sort_values(by=["Ticker", "Split"], inplace=True)
    df_res.to_csv(filename_detalle, index=False, encoding="utf-8")

    resumen = (
        df_res.groupby("Ticker")
        .agg(
            {
                "IS CAGR": "mean",
                "IS Sharpe": "mean",
                "IS Max DD": "mean",
                "OOS CAGR": "mean",
                "OOS Sharpe": "mean",
                "OOS Max DD": "mean",
                "Overfit Sharpe Ratio": "mean",
            }
        )
        .reset_index()
    )
    resumen.to_csv(filename_resumen, index=False, encoding="utf-8")
    print(f"Walk-forward generado: {filename_detalle}, {filename_resumen}")

def generar_sensibilidad_parametros(
    datos_completos,
    tickers,
    grids,
    costes_transaccion,
    execution_delay=1,
    slippage_bps=0.0,
    slippage_atr_mult=0.0,
    slippage_vol_mult=0.0,
    metric_key="Ratio de Sharpe",
    fecha_ult="",
    params_actuales=None,
    pesos_actuales=None,
):
    if not tickers:
        return

    suffix = f"_{fecha_ult.replace('-', '')}" if fecha_ult else ""
    filename = f"INFORME_SENSIBILIDAD{suffix}.pdf"
    print(f"Generando Informe de Sensibilidad (PDF Agrupado): {filename}...")
    params_actuales = params_actuales if isinstance(params_actuales, dict) else {}
    pesos_actuales = pesos_actuales if isinstance(pesos_actuales, dict) else {}

    with PdfPages(filename) as pdf:
        # Ordenar tickers alfabÃ©ticamente para que el PDF salga ordenado
        tickers_ordenados = sorted(tickers)

        # Lista para acumular estadÃ­sticas globales
        all_ticker_stats = []

        for idx_t, ticker in enumerate(tickers_ordenados):
            print(f"  Calculando Sensibilidad {idx_t + 1}/{len(tickers)}: {ticker}")
            df_t = datos_completos[
                datos_completos["ticker"].str.lower() == ticker.lower()
            ].copy()
            if df_t.empty:
                continue

            # Crear pÃ¡gina con 2x2 grÃ¡ficos
            fig, axes = plt.subplots(2, 2, figsize=(10, 7), dpi=72)
            fig.suptitle(
                f"An\u00e1lisis de Sensibilidad: {ticker} ({metric_key})",
                fontsize=16,
                y=0.95,
            )

            # Diccionario para almacenar estadÃ­sticas de cada estrategia
            stats_dict = {}

            # --- 1. Tendencia (Top-Left) ---
            x_vals = grids["tendencia"]["short_window"]
            y_vals = grids["tendencia"]["long_window"]
            matriz = np.full((len(y_vals), len(x_vals)), np.nan)
            for i, long_w in enumerate(y_vals):
                for j, short_w in enumerate(x_vals):
                    if short_w >= long_w:
                        continue
                    try:
                        _, met = analizar_tendencia(
                            df_t,
                            short_w,
                            long_w,
                            costes_transaccion,
                            execution_delay,
                            slippage_bps,
                            slippage_atr_mult,
                            slippage_vol_mult,
                        )
                        matriz[i, j] = met.get(metric_key, np.nan)
                    except:
                        continue
            generar_heatmap_en_ax(
                axes[0, 0],
                x_vals,
                y_vals,
                matriz,
                "Cruce Medias (Tendencia)",
                "Short SMA",
                "Long SMA",
                metric_key,
            )
            stats_dict["Tendencia"] = analizar_matriz_heatmap(matriz, x_vals, y_vals)

            # --- 2. Bollinger (Top-Right) ---
            x_vals = grids["bollinger"]["window"]
            y_vals = grids["bollinger"]["num_std_dev"]
            matriz = np.full((len(y_vals), len(x_vals)), np.nan)
            for i, num_std in enumerate(y_vals):
                for j, window in enumerate(x_vals):
                    try:
                        _, met = analizar_reversion_bollinger(
                            df_t,
                            window,
                            num_std,
                            costes_transaccion,
                            execution_delay,
                            slippage_bps,
                            slippage_atr_mult,
                            slippage_vol_mult,
                        )
                        matriz[i, j] = met.get(metric_key, np.nan)
                    except:
                        continue
            generar_heatmap_en_ax(
                axes[0, 1],
                x_vals,
                y_vals,
                matriz,
                "Mean Reversion (Bollinger)",
                "Window",
                "Std Dev",
                metric_key,
            )
            stats_dict["Bollinger"] = analizar_matriz_heatmap(matriz, x_vals, y_vals)

            # --- 3. RSI (Bottom-Left) ---
            # Seleccionamos una ventana RSI representativa (la mediana) para no generar demasiados grÃ¡ficos
            rsi_windows = sorted(grids["rsi"]["window"])
            selected_window = rsi_windows[len(rsi_windows) // 2] if rsi_windows else 14

            x_vals = grids["rsi"]["umbral_salida"]
            y_vals = grids["rsi"]["umbral_compra"]
            matriz = np.full((len(y_vals), len(x_vals)), np.nan)
            for i, umbral_compra in enumerate(y_vals):
                for j, umbral_salida in enumerate(x_vals):
                    if umbral_salida <= umbral_compra:
                        continue
                    try:
                        _, met = analizar_reversion_rsi(
                            df_t,
                            selected_window,
                            umbral_compra,
                            umbral_salida,
                            costes_transaccion,
                            execution_delay,
                            slippage_bps,
                            slippage_atr_mult,
                            slippage_vol_mult,
                        )
                        matriz[i, j] = met.get(metric_key, np.nan)
                    except:
                        continue
            generar_heatmap_en_ax(
                axes[1, 0],
                x_vals,
                y_vals,
                matriz,
                f"RSI Reversion (Window={selected_window})",
                "Exit Threshold",
                "Buy Threshold",
                metric_key,
            )
            stats_dict["RSI"] = analizar_matriz_heatmap(matriz, x_vals, y_vals)
            stats_dict["RSI"]["fixed_window"] = selected_window  # ParÃ¡metro fijo

            # --- 4. MACD (Bottom-Right) ---
            x_vals = grids["macd"]["fast_period"]
            y_vals = grids["macd"]["slow_period"]
            matriz = np.full((len(y_vals), len(x_vals)), np.nan)
            signal_vals = grids["macd"]["signal_period"]
            signal_p = signal_vals[0] if signal_vals else 9
            for i, slow_p in enumerate(y_vals):
                for j, fast_p in enumerate(x_vals):
                    if fast_p >= slow_p:
                        continue
                    try:
                        _, met = analizar_macd(
                            df_t,
                            fast_p,
                            slow_p,
                            signal_p,
                            costes_transaccion,
                            execution_delay,
                            slippage_bps,
                            slippage_atr_mult,
                            slippage_vol_mult,
                        )
                        matriz[i, j] = met.get(metric_key, np.nan)
                    except:
                        continue
            generar_heatmap_en_ax(
                axes[1, 1],
                x_vals,
                y_vals,
                matriz,
                f"MACD Trend (Signal={signal_p})",
                "Fast Period",
                "Slow Period",
                metric_key,
            )
            stats_dict["MACD"] = analizar_matriz_heatmap(matriz, x_vals, y_vals)
            stats_dict["MACD"]["fixed_signal"] = signal_p  # ParÃ¡metro fijo

            # Generar texto de conclusiones y aÃ±adirlo al final de la pÃ¡gina
            texto_conclusiones = generar_conclusion_sensibilidad(stats_dict)

            # Ajustamos el layout para dejar hueco abajo
            plt.tight_layout(rect=[0, 0.16, 1, 0.95])

            # AÃ±adimos el texto en el borde inferior
            # Usamos coordenadas de la figura (0 a 1)
            fig.text(
                0.02,
                0.02,
                texto_conclusiones,
                ha="left",
                va="bottom",
                fontsize=9,
                wrap=True,
                bbox=dict(boxstyle="round,pad=0.45", fc="#f0f0f0", ec="gray", alpha=0.8),
            )

            pdf.savefig(fig, dpi=72)
            plt.close(fig)
            import gc

            gc.collect()

            # Guardar estadÃ­sticas de este ticker para el anÃ¡lisis global
            ticker_stats = {"Ticker": ticker}
            ticker_stats.update(stats_dict)
            all_ticker_stats.append(ticker_stats)

        # Generar pÃ¡gina de conclusiones globales con mejor diseÃ±o
        conclusiones_globales = generar_conclusion_global_sensibilidad(all_ticker_stats)
        if conclusiones_globales:
            fig_global = plt.figure(figsize=(10, 10), dpi=72)
            fig_global.suptitle(
                "CONCLUSIONES GLOBALES - RECOMENDACIONES DE CONFIGURACION",
                fontsize=16,
                fontweight="bold",
                y=0.96,
            )

            global_stats = conclusiones_globales["global_stats"]
            pesos_rec = conclusiones_globales["pesos_recomendados"]
            sorted_strats = sorted(
                global_stats.items(),
                key=lambda x: x[1]["sharpe_promedio"],
                reverse=True,
            )

            # Crear 4 subplots verticales (mÃ¡s espacio para evitar solapamientos)
            ax1 = plt.subplot2grid((4, 1), (0, 0))
            ax2 = plt.subplot2grid((4, 1), (1, 0))
            ax3 = plt.subplot2grid((4, 1), (2, 0))
            ax4 = plt.subplot2grid((4, 1), (3, 0))

            for ax in [ax1, ax2, ax3, ax4]:
                ax.axis("off")

            # --- SECCION 1: RANKING ---
            texto1 = (
                f"=== RANKING DE ESTRATEGIAS (Basado en {len(all_ticker_stats)} tickers) ===\n\n"
            )
            for estrat, stats in sorted_strats:
                texto1 += f"- {estrat}:  Sharpe={stats['sharpe_promedio']:.2f}  |  "
                texto1 += f"Robustez={stats['robustez_promedio']:.0%}  |  Validos={stats['n_tickers']}\n"

            ax1.text(
                0.5,
                0.5,
                texto1,
                ha="center",
                va="center",
                fontsize=10,
                family="monospace",
                bbox=dict(boxstyle="round,pad=0.8", fc="#e3f2fd", ec="#1976d2", lw=1.5),
            )

            # --- SECCIÃ“N 2: PARÃMETROS (USADOS vs RECOMENDADOS) ---
            param_labels = {
                "Tendencia": [("Short SMA", "x"), ("Long SMA", "y")],
                "Bollinger": [("Window", "x"), ("Std Dev", "y")],
                "RSI": [
                    ("Window", "fixed"),
                    ("Exit Threshold", "x"),
                    ("Buy Threshold", "y"),
                ],
                "MACD": [
                    ("Fast Period", "x"),
                    ("Slow Period", "y"),
                    ("Signal Period", "fixed"),
                ],
            }

            params_usados_por_estrategia = {
                "Tendencia": {
                    "Short SMA": (params_actuales.get("tendencia") or {}).get("short_window"),
                    "Long SMA": (params_actuales.get("tendencia") or {}).get("long_window"),
                },
                "Bollinger": {
                    "Window": (params_actuales.get("bollinger") or {}).get("window"),
                    "Std Dev": (params_actuales.get("bollinger") or {}).get("num_std_dev"),
                },
                "RSI": {
                    "Window": (params_actuales.get("rsi") or {}).get("window"),
                    "Exit Threshold": (params_actuales.get("rsi") or {}).get("umbral_salida"),
                    "Buy Threshold": (params_actuales.get("rsi") or {}).get("umbral_compra"),
                },
                "MACD": {
                    "Fast Period": (params_actuales.get("macd") or {}).get("fast_period"),
                    "Slow Period": (params_actuales.get("macd") or {}).get("slow_period"),
                    "Signal Period": (params_actuales.get("macd") or {}).get("signal_period"),
                },
            }

            texto2 = "=== PARAMETROS: USADOS vs RECOMENDADOS ===\n\n"
            for estrat in sorted_strats:
                estrat_name = estrat[0]
                stats = estrat[1]
                x_med = stats.get("param_x_median")
                y_med = stats.get("param_y_median")
                fixed_med = stats.get("param_fixed_median")

                param_config = param_labels.get(estrat_name, [])
                param_values = {"x": x_med, "y": y_med, "fixed": fixed_med}
                usados = params_usados_por_estrategia.get(estrat_name, {})

                usados_str = "  |  ".join(
                    [
                        f"{label}={usados.get(label)}"
                        for label, _ in param_config
                        if usados.get(label) is not None
                    ]
                )
                rec_str = "  |  ".join(
                    [
                        f"{label}={param_values[key]}"
                        for label, key in param_config
                        if param_values.get(key) is not None
                    ]
                )

                if not usados_str:
                    usados_str = "N/D"
                if not rec_str:
                    rec_str = "N/D"

                texto2 += f"- {estrat_name}:\n"
                texto2 += f"    Usado       -> {usados_str}\n"
                texto2 += f"    Recomendado -> {rec_str}\n"

            ax2.text(
                0.5,
                0.5,
                texto2,
                ha="center",
                va="center",
                fontsize=9,
                family="monospace",
                bbox=dict(boxstyle="round,pad=0.8", fc="#fff3e0", ec="#f57c00", lw=1.5),
            )

            # --- SECCION 3: PONDERACIONES ---
            texto3 = "=== PONDERACIONES: USADAS vs RECOMENDADAS ===\n\n"
            estrategias_orden = ["tendencia", "bollinger", "rsi", "macd"]
            for estrat in estrategias_orden:
                usado = pesos_actuales.get(estrat, None)
                recomendado = pesos_rec.get(estrat, None)
                if usado is None and recomendado is None:
                    continue
                usado_str = (
                    f"{usado:.3f} ({usado * 100:.1f}%)" if usado is not None else "N/D"
                )
                rec_str = (
                    f"{recomendado:.3f} ({recomendado * 100:.1f}%)"
                    if recomendado is not None
                    else "N/D"
                )
                if usado is not None and recomendado is not None:
                    delta_pp = (recomendado - usado) * 100
                    delta_str = f"{delta_pp:+.1f} pp"
                else:
                    delta_str = "N/D"
                texto3 += (
                    f"  '{estrat}': usado={usado_str}  |  "
                    f"recomendado={rec_str}  |  Delta={delta_str}\n"
                )

            ax3.text(
                0.5,
                0.5,
                texto3,
                ha="center",
                va="center",
                fontsize=9,
                family="monospace",
                bbox=dict(boxstyle="round,pad=0.8", fc="#e8f5e9", ec="#388e3c", lw=1.5),
            )

            # --- SECCION 4: CODIGO PYTHON COMPACTO ---
            usados_items = [
                f"'{estrat}': {pesos_actuales[estrat]:.3f}"
                for estrat in estrategias_orden
                if estrat in pesos_actuales
            ]
            rec_items = [
                f"'{estrat}': {pesos_rec[estrat]:.3f}"
                for estrat in estrategias_orden
                if estrat in pesos_rec
            ]
            texto4 = "=== CODIGO PYTHON (USADO vs RECOMENDADO) ===\n\n"
            texto4 += "PESOS_ESTRATEGIAS_USADOS = {" + ", ".join(usados_items) + "}\n"
            texto4 += "PESOS_ESTRATEGIAS_RECOMENDADOS = {" + ", ".join(rec_items) + "}"

            ax4.text(
                0.5,
                0.5,
                texto4,
                ha="center",
                va="center",
                fontsize=9,
                family="monospace",
                bbox=dict(boxstyle="round,pad=0.7", fc="#f3f4f6", ec="#6b7280", lw=1.3),
            )

            plt.tight_layout(rect=[0.01, 0.01, 0.99, 0.94])
            pdf.savefig(fig_global, dpi=72)
            plt.close(fig_global)
            import gc

            gc.collect()

    print("Informe de Sensibilidad generado con Ã©xito.")

def generar_stress_tests(
    datos_completos,
    tickers,
    params_tendencia,
    params_bollinger,
    params_rsi,
    params_macd,
    pesos_estrategias,
    cost_scenarios,
    execution_delay=1,
    slippage_bps=0.0,
    slippage_atr_mult=0.0,
    slippage_vol_mult=0.0,
    bootstrap_iters=300,
    bootstrap_seed=42,
    fecha_ult="",
):
    if not tickers:
        return

    suffix = f"_{fecha_ult.replace('-', '')}" if fecha_ult else ""
    filename_costes = f"STRESS_COSTES{suffix}.csv"
    filename_boot = f"STRESS_BOOTSTRAP{suffix}.csv"

    rows_costes = []
    rows_boot = []
    for ticker in tickers:
        df_t = datos_completos[
            datos_completos["ticker"].str.lower() == ticker.lower()
        ].copy()
        if df_t.empty:
            continue

        for nombre, coste in cost_scenarios.items():
            try:
                _, met = ejecutar_analisis_completo_individual(
                    df_t,
                    params_tendencia,
                    params_bollinger,
                    params_rsi,
                    params_macd,
                    coste,
                    pesos_estrategias,
                    execution_delay=execution_delay,
                    slippage_bps=slippage_bps,
                    slippage_atr_mult=slippage_atr_mult,
                    slippage_vol_mult=slippage_vol_mult,
                )
                rows_costes.append(
                    {
                        "Ticker": ticker,
                        "Escenario": nombre,
                        "Coste": coste,
                        "CAGR": met.get("CAGR_Combinada", 0),
                        "Sharpe": met.get("Ratio de Sharpe_Combinada", 0),
                        "Max Drawdown": met.get("MÃ¡ximo Drawdown_Combinada", 0),
                    }
                )
            except Exception:
                continue

        try:
            df_viz, _ = ejecutar_analisis_completo_individual(
                df_t,
                params_tendencia,
                params_bollinger,
                params_rsi,
                params_macd,
                list(cost_scenarios.values())[0],
                pesos_estrategias,
                execution_delay=execution_delay,
                slippage_bps=slippage_bps,
                slippage_atr_mult=slippage_atr_mult,
                slippage_vol_mult=slippage_vol_mult,
            )
            comb_returns = df_viz["combinada_cumulative_return"].pct_change().dropna()
            boot = bootstrap_metricas_returns(
                comb_returns, n_iter=bootstrap_iters, seed=bootstrap_seed
            )
            if boot:
                boot["Ticker"] = ticker
                rows_boot.append(boot)
        except Exception:
            continue

    if rows_costes:
        df_costes = pd.DataFrame(rows_costes)
        df_costes.sort_values(by=["Ticker", "Escenario"], inplace=True)
        cols = ["Ticker"] + [c for c in df_costes.columns if c != "Ticker"]
        df_costes = df_costes[cols]
        df_costes.to_csv(filename_costes, index=False, encoding="utf-8")
        print(f"Stress test costes generado: {filename_costes}")

    if rows_boot:
        df_boot = pd.DataFrame(rows_boot)
        df_boot.sort_values(by=["Ticker"], inplace=True)
        cols = ["Ticker"] + [c for c in df_boot.columns if c != "Ticker"]
        df_boot = df_boot[cols]
        df_boot.to_csv(filename_boot, index=False, encoding="utf-8")
        print(f"Stress test bootstrap generado: {filename_boot}")


# ==============================================================================
# FUNCIONES 2A, 2B, 2C: LÃ“GICAS DE ESTRATEGIA
# ==============================================================================


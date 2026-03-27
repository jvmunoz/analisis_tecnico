import numpy as np
import pandas as pd

from .metrics import calcular_slippage_pct, calcular_metricas

def analizar_tendencia(
    df_ticker,
    short_window,
    long_window,
    costes_transaccion,
    execution_delay=1,
    slippage_bps=0.0,
    slippage_atr_mult=0.0,
    slippage_vol_mult=0.0,
):
    df_backtest = df_ticker.copy().set_index("date")
    df_backtest["sma_short"] = (
        df_backtest["close"].rolling(window=short_window, min_periods=1).mean()
    )
    df_backtest["sma_long"] = (
        df_backtest["close"].rolling(window=long_window, min_periods=1).mean()
    )
    df_backtest["signal"] = 0
    df_backtest.loc[df_backtest["sma_short"] > df_backtest["sma_long"], "signal"] = 1
    if execution_delay and execution_delay > 0:
        df_backtest["signal_shifted"] = df_backtest["signal"].shift(execution_delay)
    else:
        df_backtest["signal_shifted"] = df_backtest["signal"]
    df_backtest["signal_shifted"] = df_backtest["signal_shifted"].fillna(0)
    df_backtest["position"] = df_backtest["signal_shifted"].diff().fillna(0)
    slippage = calcular_slippage_pct(
        df_backtest, slippage_bps, slippage_atr_mult, slippage_vol_mult
    )
    costes = abs(df_backtest["position"]) * (costes_transaccion + slippage)
    df_backtest["strategy_return"] = (
        df_backtest["daily_return"] * df_backtest["signal_shifted"]
    ) - costes
    df_backtest.dropna(subset=["strategy_return"], inplace=True)
    df_resultado, metricas = calcular_metricas(df_backtest, "strategy_return")
    return df_resultado.reset_index(), metricas

def analizar_reversion_bollinger(
    df_ticker,
    window,
    num_std_dev,
    costes_transaccion,
    execution_delay=1,
    slippage_bps=0.0,
    slippage_atr_mult=0.0,
    slippage_vol_mult=0.0,
):
    df_backtest = df_ticker.copy().set_index("date")
    df_backtest["sma"] = (
        df_backtest["close"].rolling(window=window, min_periods=1).mean()
    )
    df_backtest["std_dev"] = (
        df_backtest["close"].rolling(window=window, min_periods=1).std()
    )
    df_backtest["banda_superior"] = df_backtest["sma"] + (
        df_backtest["std_dev"] * num_std_dev
    )
    df_backtest["banda_inferior"] = df_backtest["sma"] - (
        df_backtest["std_dev"] * num_std_dev
    )

    buy_signals = (df_backtest["close"] < df_backtest["banda_inferior"]).values
    exit_signals = (df_backtest["close"] > df_backtest["sma"]).values

    signals = []
    position = 0
    for i in range(len(df_backtest)):
        if position == 0 and buy_signals[i]:
            position = 1
        elif position == 1 and exit_signals[i]:
            position = 0
        signals.append(position)

    df_backtest["signal"] = signals
    if execution_delay and execution_delay > 0:
        df_backtest["signal_shifted"] = df_backtest["signal"].shift(execution_delay)
    else:
        df_backtest["signal_shifted"] = df_backtest["signal"]
    df_backtest["signal_shifted"] = df_backtest["signal_shifted"].fillna(0)
    df_backtest["position"] = df_backtest["signal_shifted"].diff().fillna(0)
    slippage = calcular_slippage_pct(
        df_backtest, slippage_bps, slippage_atr_mult, slippage_vol_mult
    )
    costes = abs(df_backtest["position"]) * (costes_transaccion + slippage)
    df_backtest["strategy_return"] = (
        df_backtest["daily_return"] * df_backtest["signal_shifted"]
    ) - costes
    df_backtest.dropna(subset=["strategy_return"], inplace=True)
    df_resultado, metricas = calcular_metricas(df_backtest, "strategy_return")
    return df_resultado.reset_index(), metricas

def analizar_reversion_rsi(
    df_ticker,
    window,
    umbral_compra,
    umbral_salida,
    costes_transaccion,
    execution_delay=1,
    slippage_bps=0.0,
    slippage_atr_mult=0.0,
    slippage_vol_mult=0.0,
):
    df_backtest = df_ticker.copy().set_index("date")
    delta = df_backtest["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    df_backtest["rsi"] = 100 - (100 / (1 + rs))

    buy_signals = (df_backtest["rsi"] < umbral_compra).values
    exit_signals = (df_backtest["rsi"] > umbral_salida).values

    signals = []
    position = 0
    for i in range(len(df_backtest)):
        if position == 0 and buy_signals[i]:
            position = 1
        elif position == 1 and exit_signals[i]:
            position = 0
        signals.append(position)

    df_backtest["signal"] = signals
    if execution_delay and execution_delay > 0:
        df_backtest["signal_shifted"] = df_backtest["signal"].shift(execution_delay)
    else:
        df_backtest["signal_shifted"] = df_backtest["signal"]
    df_backtest["signal_shifted"] = df_backtest["signal_shifted"].fillna(0)
    df_backtest["position"] = df_backtest["signal_shifted"].diff().fillna(0)
    slippage = calcular_slippage_pct(
        df_backtest, slippage_bps, slippage_atr_mult, slippage_vol_mult
    )
    costes = abs(df_backtest["position"]) * (costes_transaccion + slippage)
    df_backtest["strategy_return"] = (
        df_backtest["daily_return"] * df_backtest["signal_shifted"]
    ) - costes
    df_backtest.dropna(subset=["strategy_return"], inplace=True)
    df_resultado, metricas = calcular_metricas(df_backtest, "strategy_return")
    return df_resultado.reset_index(), metricas

def analizar_macd(
    df_ticker,
    fast_period=12,
    slow_period=26,
    signal_period=9,
    costes_transaccion=0.001,
    execution_delay=1,
    slippage_bps=0.0,
    slippage_atr_mult=0.0,
    slippage_vol_mult=0.0,
):
    """
    Estrategia basada en MACD (Moving Average Convergence Divergence).

    SeÃ±ales:
    - Compra: MACD cruza por encima de la lÃ­nea de seÃ±al
    - Venta: MACD cruza por debajo de la lÃ­nea de seÃ±al
    """
    df_backtest = df_ticker.copy().set_index("date")

    # Calcular EMAs
    ema_fast = df_backtest["close"].ewm(span=fast_period, adjust=False).mean()
    ema_slow = df_backtest["close"].ewm(span=slow_period, adjust=False).mean()

    # Calcular MACD y lÃ­nea de seÃ±al
    df_backtest["macd"] = ema_fast - ema_slow
    df_backtest["macd_signal"] = (
        df_backtest["macd"].ewm(span=signal_period, adjust=False).mean()
    )
    df_backtest["macd_histogram"] = df_backtest["macd"] - df_backtest["macd_signal"]

    # Preparar datos para el bucle optimizado
    macd_vals = df_backtest["macd"].values
    signal_vals = df_backtest["macd_signal"].values

    signals = [0]
    position = 0

    for i in range(1, len(df_backtest)):
        macd_prev = macd_vals[i - 1]
        signal_prev = signal_vals[i - 1]
        macd_curr = macd_vals[i]
        signal_curr = signal_vals[i]

        # Cruce alcista (compra)
        if position == 0 and macd_prev <= signal_prev and macd_curr > signal_curr:
            position = 1
        # Cruce bajista (venta)
        elif position == 1 and macd_prev >= signal_prev and macd_curr < signal_curr:
            position = 0

        signals.append(position)

    df_backtest["signal"] = signals
    if execution_delay and execution_delay > 0:
        df_backtest["signal_shifted"] = df_backtest["signal"].shift(execution_delay)
    else:
        df_backtest["signal_shifted"] = df_backtest["signal"]
    df_backtest["signal_shifted"] = df_backtest["signal_shifted"].fillna(0)
    df_backtest["position"] = df_backtest["signal_shifted"].diff().fillna(0)

    # Calcular retornos de la estrategia
    slippage = calcular_slippage_pct(
        df_backtest, slippage_bps, slippage_atr_mult, slippage_vol_mult
    )
    costes = abs(df_backtest["position"]) * (costes_transaccion + slippage)
    df_backtest["strategy_return"] = (
        df_backtest["daily_return"] * df_backtest["signal_shifted"]
    ) - costes

    # Eliminar NaN y calcular mÃ©tricas
    df_backtest.dropna(subset=["strategy_return"], inplace=True)
    df_resultado, metricas = calcular_metricas(df_backtest, "strategy_return")

    return df_resultado.reset_index(), metricas

def _append_signal_records(signal_log, ticker, strategy, df_viz, params):
    if signal_log is None or df_viz is None or df_viz.empty:
        return
    pos_col = f"position_{strategy}"
    if pos_col not in df_viz.columns:
        return
    changes = df_viz[df_viz[pos_col] != 0]
    if changes.empty:
        return

    for fecha, row in changes.iterrows():
        evento = "ENTRADA" if row[pos_col] > 0 else "SALIDA"
        estado = "ACTIVO" if row[pos_col] > 0 else "INACTIVO"
        record = {
            "ticker": ticker,
            "estrategia": strategy.upper(),
            "fecha": fecha.strftime("%Y-%m-%d"),
            "evento": evento,
            "estado_nuevo": estado,
        }
        # Indicadores y umbrales relevantes
        if strategy == "tendencia":
            record.update(
                {
                    "sma_short": row.get("sma_short"),
                    "sma_long": row.get("sma_long"),
                    "short_window": params.get("short_window"),
                    "long_window": params.get("long_window"),
                }
            )
        elif strategy == "bollinger":
            record.update(
                {
                    "close": row.get("close"),
                    "banda_superior": row.get("banda_superior"),
                    "banda_inferior": row.get("banda_inferior"),
                    "window": params.get("window"),
                    "num_std_dev": params.get("num_std_dev"),
                }
            )
        elif strategy == "rsi":
            record.update(
                {
                    "rsi": row.get("rsi"),
                    "umbral_compra": params.get("umbral_compra"),
                    "umbral_salida": params.get("umbral_salida"),
                    "window": params.get("window"),
                }
            )
        elif strategy == "macd":
            record.update(
                {
                    "macd": row.get("macd"),
                    "macd_signal": row.get("macd_signal"),
                    "fast_period": params.get("fast_period"),
                    "slow_period": params.get("slow_period"),
                    "signal_period": params.get("signal_period"),
                }
            )
        signal_log.append(record)

def ejecutar_analisis_completo_individual(
    df_ticker,
    params_tendencia,
    params_bollinger,
    params_rsi,
    params_macd,
    costes_transaccion,
    pesos_estrategias,
    execution_delay=1,
    slippage_bps=0.0,
    slippage_atr_mult=0.0,
    slippage_vol_mult=0.0,
    signal_log=None,
    ticker=None,
):
    """Ejecuta todas las estrategias y la combinada para un ticker y une los resultados."""
    def _ultima_op(metricas, is_entry=True):
        key = "Ultima Entrada" if is_entry else "Ultima Salida"
        return metricas.get(key) or "N/A"

    df_t, met_t = analizar_tendencia(
        df_ticker,
        **params_tendencia,
        costes_transaccion=costes_transaccion,
        execution_delay=execution_delay,
        slippage_bps=slippage_bps,
        slippage_atr_mult=slippage_atr_mult,
        slippage_vol_mult=slippage_vol_mult,
    )
    df_b, met_b = analizar_reversion_bollinger(
        df_ticker,
        **params_bollinger,
        costes_transaccion=costes_transaccion,
        execution_delay=execution_delay,
        slippage_bps=slippage_bps,
        slippage_atr_mult=slippage_atr_mult,
        slippage_vol_mult=slippage_vol_mult,
    )
    df_rsi, met_rsi = analizar_reversion_rsi(
        df_ticker,
        **params_rsi,
        costes_transaccion=costes_transaccion,
        execution_delay=execution_delay,
        slippage_bps=slippage_bps,
        slippage_atr_mult=slippage_atr_mult,
        slippage_vol_mult=slippage_vol_mult,
    )
    df_macd, met_macd = analizar_macd(
        df_ticker,
        **params_macd,
        costes_transaccion=costes_transaccion,
        execution_delay=execution_delay,
        slippage_bps=slippage_bps,
        slippage_atr_mult=slippage_atr_mult,
        slippage_vol_mult=slippage_vol_mult,
    )

    df_t.set_index("date", inplace=True)
    df_b.set_index("date", inplace=True)
    df_rsi.set_index("date", inplace=True)
    df_macd.set_index("date", inplace=True)

    common_index = df_t.index
    common_index = common_index.intersection(df_b.index)
    common_index = common_index.intersection(df_rsi.index)
    common_index = common_index.intersection(df_macd.index)

    df_t = df_t.loc[common_index]
    df_b = df_b.loc[common_index]
    df_rsi = df_rsi.loc[common_index]
    df_macd = df_macd.loc[common_index]

    combined_returns = (
        df_t["strategy_return"] * pesos_estrategias["tendencia"]
        + df_b["strategy_return"] * pesos_estrategias["bollinger"]
        + df_rsi["strategy_return"] * pesos_estrategias["rsi"]
        + df_macd["strategy_return"] * pesos_estrategias["macd"]
    )
    combined_signal_score = (
        df_t["signal_shifted"] * pesos_estrategias["tendencia"]
        + df_b["signal_shifted"] * pesos_estrategias["bollinger"]
        + df_rsi["signal_shifted"] * pesos_estrategias["rsi"]
        + df_macd["signal_shifted"] * pesos_estrategias["macd"]
    )
    # Señal discreta para métricas de trades de la combinada (consenso por peso >= 50%).
    combined_signal = (combined_signal_score >= 0.5).astype(int)

    df_c_temp = pd.DataFrame(
        {
            "combinada_return": combined_returns,
            "daily_return": df_t["daily_return"],
            "signal_shifted": combined_signal,
            "position": combined_signal.diff().fillna(0),
        }
    )

    _, met_c_raw = calcular_metricas(df_c_temp, "combinada_return")
    met_c = {k: v for k, v in met_c_raw.items() if "Mercado" not in k}

    df_viz = pd.DataFrame(index=df_t.index)
    df_viz["close"] = df_t["close"]
    df_viz["high"] = df_t["high"]
    df_viz["low"] = df_t["low"]
    df_viz["volume"] = (
        df_ticker.set_index("date")["volume"] if "volume" in df_ticker.columns else 0
    )
    df_viz["dividends"] = (
        df_ticker.set_index("date")["dividends"]
        if "dividends" in df_ticker.columns
        else 0.0
    )

    # --- CÃLCULOS TÃ‰CNICOS ADICIONALES ---
    # RVOL (Volumen Relativo 20d)
    if "volume" in df_viz.columns:
        vol_avg_20 = df_viz["volume"].rolling(window=20).mean()
        df_viz["rvol"] = df_viz["volume"] / vol_avg_20
    else:
        df_viz["rvol"] = 1.0

    # ATR (14d) y ATR%
    tr1 = df_viz["high"] - df_viz["low"]
    tr2 = abs(df_viz["high"] - df_viz["close"].shift(1))
    tr3 = abs(df_viz["low"] - df_viz["close"].shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df_viz["atr"] = tr.rolling(window=14).mean()
    df_viz["atr_perc"] = (df_viz["atr"] / df_viz["close"]) * 100

    # SMA 200 para Amplitud de Mercado
    df_viz["sma_200"] = df_viz["close"].rolling(window=200).mean()

    # ADX (Fuerza de Tendencia - Simplificado)
    # Usamos una aproximaciÃ³n estÃ¡ndar de 14 periodos
    plus_dm = (df_viz["high"] - df_viz["high"].shift(1)).clip(lower=0)
    minus_dm = (df_viz["low"].shift(1) - df_viz["low"]).clip(lower=0)
    # Solo tomamos el mayor si es positivo
    plus_dm.loc[plus_dm < minus_dm] = 0
    minus_dm.loc[minus_dm < plus_dm] = 0

    tr_smooth = tr.rolling(window=14).mean()
    plus_di = 100 * (plus_dm.rolling(window=14).mean() / tr_smooth)
    minus_di = 100 * (minus_dm.rolling(window=14).mean() / tr_smooth)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df_viz["adx"] = dx.rolling(window=14).mean()

    df_viz["sma_short"] = df_t["sma_short"]
    df_viz["sma_long"] = df_t["sma_long"]
    df_viz["position_tendencia"] = df_t["position"]
    df_viz["sma_bollinger"] = df_b["sma"]
    df_viz["banda_superior"] = df_b["banda_superior"]
    df_viz["banda_inferior"] = df_b["banda_inferior"]
    df_viz["position_bollinger"] = df_b["position"]
    df_viz["rsi"] = df_rsi["rsi"]
    df_viz["position_rsi"] = df_rsi["position"]
    df_viz["macd"] = df_macd["macd"]
    df_viz["macd_signal"] = df_macd["macd_signal"]
    df_viz["macd_histogram"] = df_macd["macd_histogram"]
    df_viz["position_macd"] = df_macd["position"]
    df_viz["market_cumulative_return"] = df_t["market_cumulative_return"]
    df_viz["tendencia_cumulative_return"] = df_t["strategy_cumulative_return"]
    df_viz["bollinger_cumulative_return"] = df_b["strategy_cumulative_return"]
    df_viz["rsi_cumulative_return"] = df_rsi["strategy_cumulative_return"]
    df_viz["macd_cumulative_return"] = df_macd["strategy_cumulative_return"]
    df_viz["combinada_cumulative_return"] = (1 + combined_returns).cumprod()
    df_viz.ffill(inplace=True)
    df_viz.bfill(inplace=True)
    df_viz.infer_objects(copy=False)

    # Trazabilidad de seÃ±ales
    ticker_val = ticker or df_ticker["ticker"].iloc[0]
    _append_signal_records(signal_log, ticker_val, "tendencia", df_viz, params_tendencia)
    _append_signal_records(signal_log, ticker_val, "bollinger", df_viz, params_bollinger)
    _append_signal_records(signal_log, ticker_val, "rsi", df_viz, params_rsi)
    _append_signal_records(signal_log, ticker_val, "macd", df_viz, params_macd)

    metricas_combinadas = {
        "Retorno Mercado": met_t["Retorno Mercado"],
        "CAGR Mercado": met_t["CAGR Mercado"],
        "Sharpe Mercado": met_t["Sharpe Mercado"],
        "Volatilidad Mercado": met_t["Volatilidad Mercado"],
        "MÃ¡ximo Drawdown Mercado": met_t["MÃ¡ximo Drawdown Mercado"],
        "Ratio de Sortino Mercado": met_t["Ratio de Sortino Mercado"],
        "Ratio de Calmar Mercado": met_t["Ratio de Calmar Mercado"],
        "Ulcer Index Mercado": met_t["Ulcer Index Mercado"],
        "VaR 95 Mercado": met_t["VaR 95 Mercado"],
        "CVaR 95 Mercado": met_t["CVaR 95 Mercado"],
        "DuraciÃ³n Drawdown Mercado": met_t["DuraciÃ³n Drawdown Mercado"],
        "Retorno Total_Tendencia": met_t["Retorno Total"],
        "CAGR_Tendencia": met_t["CAGR"],
        "Ratio de Sharpe_Tendencia": met_t["Ratio de Sharpe"],
        "Volatilidad_Tendencia": met_t["Volatilidad"],
        "MÃ¡ximo Drawdown_Tendencia": met_t["MÃ¡ximo Drawdown"],
        "Ratio de Sortino_Tendencia": met_t["Ratio de Sortino"],
        "Ratio de Calmar_Tendencia": met_t["Ratio de Calmar"],
        "Ulcer Index_Tendencia": met_t["Ulcer Index"],
        "VaR 95_Tendencia": met_t["VaR 95"],
        "CVaR 95_Tendencia": met_t["CVaR 95"],
        "DuraciÃ³n Drawdown_Tendencia": met_t["DuraciÃ³n Drawdown"],
        "Trades_Tendencia": met_t["Trades"],
        "Win Rate_Tendencia": met_t["Win Rate"],
        "Profit Factor_Tendencia": met_t["Profit Factor"],
        "Expectancy_Tendencia": met_t["Expectancy"],
        "Avg Win_Tendencia": met_t["Avg Win"],
        "Avg Loss_Tendencia": met_t["Avg Loss"],
        "Time in Market_Tendencia": met_t["Time in Market"],
        "Ultima Entrada_Tendencia": _ultima_op(met_t, is_entry=True),
        "Ultima Salida_Tendencia": _ultima_op(met_t, is_entry=False),
        "Retorno Total_Bollinger": met_b["Retorno Total"],
        "CAGR_Bollinger": met_b["CAGR"],
        "Ratio de Sharpe_Bollinger": met_b["Ratio de Sharpe"],
        "Volatilidad_Bollinger": met_b["Volatilidad"],
        "MÃ¡ximo Drawdown_Bollinger": met_b["MÃ¡ximo Drawdown"],
        "Ratio de Sortino_Bollinger": met_b["Ratio de Sortino"],
        "Ratio de Calmar_Bollinger": met_b["Ratio de Calmar"],
        "Ulcer Index_Bollinger": met_b["Ulcer Index"],
        "VaR 95_Bollinger": met_b["VaR 95"],
        "CVaR 95_Bollinger": met_b["CVaR 95"],
        "DuraciÃ³n Drawdown_Bollinger": met_b["DuraciÃ³n Drawdown"],
        "Trades_Bollinger": met_b["Trades"],
        "Win Rate_Bollinger": met_b["Win Rate"],
        "Profit Factor_Bollinger": met_b["Profit Factor"],
        "Expectancy_Bollinger": met_b["Expectancy"],
        "Avg Win_Bollinger": met_b["Avg Win"],
        "Avg Loss_Bollinger": met_b["Avg Loss"],
        "Time in Market_Bollinger": met_b["Time in Market"],
        "Ultima Entrada_Bollinger": _ultima_op(met_b, is_entry=True),
        "Ultima Salida_Bollinger": _ultima_op(met_b, is_entry=False),
        "Retorno Total_RSI": met_rsi["Retorno Total"],
        "CAGR_RSI": met_rsi["CAGR"],
        "Ratio de Sharpe_RSI": met_rsi["Ratio de Sharpe"],
        "Volatilidad_RSI": met_rsi["Volatilidad"],
        "MÃ¡ximo Drawdown_RSI": met_rsi["MÃ¡ximo Drawdown"],
        "Ratio de Sortino_RSI": met_rsi["Ratio de Sortino"],
        "Ratio de Calmar_RSI": met_rsi["Ratio de Calmar"],
        "Ulcer Index_RSI": met_rsi["Ulcer Index"],
        "VaR 95_RSI": met_rsi["VaR 95"],
        "CVaR 95_RSI": met_rsi["CVaR 95"],
        "DuraciÃ³n Drawdown_RSI": met_rsi["DuraciÃ³n Drawdown"],
        "Trades_RSI": met_rsi["Trades"],
        "Win Rate_RSI": met_rsi["Win Rate"],
        "Profit Factor_RSI": met_rsi["Profit Factor"],
        "Expectancy_RSI": met_rsi["Expectancy"],
        "Avg Win_RSI": met_rsi["Avg Win"],
        "Avg Loss_RSI": met_rsi["Avg Loss"],
        "Time in Market_RSI": met_rsi["Time in Market"],
        "Ultima Entrada_RSI": _ultima_op(met_rsi, is_entry=True),
        "Ultima Salida_RSI": _ultima_op(met_rsi, is_entry=False),
        "Retorno Total_MACD": met_macd["Retorno Total"],
        "CAGR_MACD": met_macd["CAGR"],
        "Ratio de Sharpe_MACD": met_macd["Ratio de Sharpe"],
        "Volatilidad_MACD": met_macd["Volatilidad"],
        "MÃ¡ximo Drawdown_MACD": met_macd["MÃ¡ximo Drawdown"],
        "Ratio de Sortino_MACD": met_macd["Ratio de Sortino"],
        "Ratio de Calmar_MACD": met_macd["Ratio de Calmar"],
        "Ulcer Index_MACD": met_macd["Ulcer Index"],
        "VaR 95_MACD": met_macd["VaR 95"],
        "CVaR 95_MACD": met_macd["CVaR 95"],
        "DuraciÃ³n Drawdown_MACD": met_macd["DuraciÃ³n Drawdown"],
        "Trades_MACD": met_macd["Trades"],
        "Win Rate_MACD": met_macd["Win Rate"],
        "Profit Factor_MACD": met_macd["Profit Factor"],
        "Expectancy_MACD": met_macd["Expectancy"],
        "Avg Win_MACD": met_macd["Avg Win"],
        "Avg Loss_MACD": met_macd["Avg Loss"],
        "Time in Market_MACD": met_macd["Time in Market"],
        "Ultima Entrada_MACD": _ultima_op(met_macd, is_entry=True),
        "Ultima Salida_MACD": _ultima_op(met_macd, is_entry=False),
        "Retorno Total_Combinada": met_c["Retorno Total"],
        "CAGR_Combinada": met_c["CAGR"],
        "Ratio de Sharpe_Combinada": met_c["Ratio de Sharpe"],
        "Volatilidad_Combinada": met_c["Volatilidad"],
        "MÃ¡ximo Drawdown_Combinada": met_c["MÃ¡ximo Drawdown"],
        "Ratio de Sortino_Combinada": met_c["Ratio de Sortino"],
        "Ratio de Calmar_Combinada": met_c["Ratio de Calmar"],
        "Ulcer Index_Combinada": met_c["Ulcer Index"],
        "VaR 95_Combinada": met_c["VaR 95"],
        "CVaR 95_Combinada": met_c["CVaR 95"],
        "DuraciÃ³n Drawdown_Combinada": met_c["DuraciÃ³n Drawdown"],
        "Trades_Combinada": met_c["Trades"],
        "Win Rate_Combinada": met_c["Win Rate"],
        "Profit Factor_Combinada": met_c["Profit Factor"],
        "Expectancy_Combinada": met_c["Expectancy"],
        "Avg Win_Combinada": met_c["Avg Win"],
        "Avg Loss_Combinada": met_c["Avg Loss"],
        "Time in Market_Combinada": met_c["Time in Market"],
    }
    return df_viz, metricas_combinadas


# ==============================================================================
# FUNCIÃ“N 5: ORQUESTADOR DEL ANÃLISIS AGREGADO
# ==============================================================================

def ejecutar_analisis_completo_agregado(
    df_datos,
    params_tendencia,
    params_bollinger,
    params_rsi,
    params_macd,
    costes_transaccion,
    pesos_estrategias,
    execution_delay=1,
    slippage_bps=0.0,
    slippage_atr_mult=0.0,
    slippage_vol_mult=0.0,
    resultados_previos=None,
):
    """Ejecuta todas las estrategias para toda la cartera y agrega los resultados."""
    print("\n--- Analizando rendimiento agregado del portafolio ---")

    all_returns = []

    if resultados_previos:
        print("  Reutilizando cÃ¡lculos previos para el anÃ¡lisis agregado...")
        for item in resultados_previos:
            ticker = item["ticker"]
            if "^" in ticker or "IBEX" in ticker.upper():
                continue
            df_viz = item["df_viz"]
            if df_viz is not None and not df_viz.empty:
                # Extraer retornos de las estrategias calculadas
                # Nota: df_viz tiene los retornos acumulados, necesitamos los diarios
                ticker_returns = pd.DataFrame(
                    {
                        "daily_return": df_viz["daily_return"]
                        if "daily_return" in df_viz.columns
                        else df_viz["close"].pct_change(),
                        "tendencia_return": df_viz[
                            "tendencia_cumulative_return"
                        ].pct_change(),
                        "bollinger_return": df_viz[
                            "bollinger_cumulative_return"
                        ].pct_change(),
                        "rsi_return": df_viz["rsi_cumulative_return"].pct_change(),
                        "macd_return": df_viz["macd_cumulative_return"].pct_change(),
                    },
                    index=df_viz.index,
                ).fillna(0)
                all_returns.append(ticker_returns)
    else:
        tickers_agregado = [
            t
            for t in df_datos["ticker"].unique()
            if "^" not in t and "IBEX" not in t.upper()
        ]
        total_tickers = len(tickers_agregado)
        for idx, ticker in enumerate(tickers_agregado):
            if idx % 5 == 0:
                print(
                    f"  [{idx + 1}/{total_tickers}] Procesando agregado para: {ticker}"
                )
            df_ticker = df_datos[df_datos["ticker"] == ticker].copy()
            df_t, _ = analizar_tendencia(
                df_ticker,
                **params_tendencia,
                costes_transaccion=costes_transaccion,
                execution_delay=execution_delay,
            )
            df_b, _ = analizar_reversion_bollinger(
                df_ticker,
                **params_bollinger,
                costes_transaccion=costes_transaccion,
                execution_delay=execution_delay,
            )
            df_rsi, _ = analizar_reversion_rsi(
                df_ticker,
                **params_rsi,
                costes_transaccion=costes_transaccion,
                execution_delay=execution_delay,
            )
            df_macd, _ = analizar_macd(
                df_ticker,
                **params_macd,
                costes_transaccion=costes_transaccion,
                execution_delay=execution_delay,
            )

            ticker_returns = pd.DataFrame(
                {
                    "daily_return": df_t.set_index("date")["daily_return"],
                    "tendencia_return": df_t.set_index("date")["strategy_return"],
                    "bollinger_return": df_b.set_index("date")["strategy_return"],
                    "rsi_return": df_rsi.set_index("date")["strategy_return"],
                    "macd_return": df_macd.set_index("date")["strategy_return"],
                }
            ).fillna(0)
            all_returns.append(ticker_returns)

    if not all_returns:
        print("  [AVISO] No se pudieron calcular retornos para el agregado.")
        return pd.DataFrame(), {}

    combined_df = pd.concat(all_returns)
    avg_returns = combined_df.groupby(combined_df.index).mean()
    avg_returns["combinada_return"] = (
        avg_returns["tendencia_return"] * pesos_estrategias["tendencia"]
        + avg_returns["bollinger_return"] * pesos_estrategias["bollinger"]
        + avg_returns["rsi_return"] * pesos_estrategias["rsi"]
        + avg_returns["macd_return"] * pesos_estrategias["macd"]
    )

    days_period = (avg_returns.index[-1] - avg_returns.index[0]).days
    years_period = days_period / 365.25 if days_period > 0 else 0

    metricas_agregadas = {}
    for col, name in [
        ("daily_return", "Mercado"),
        ("tendencia_return", "Tendencia"),
        ("bollinger_return", "Bollinger"),
        ("rsi_return", "RSI"),
        ("macd_return", "MACD"),
        ("combinada_return", "Combinada"),
    ]:
        r = avg_returns[col]
        cum_ret = (1 + r).cumprod()
        total_return = cum_ret.iloc[-1] - 1
        metricas_agregadas[f"Retorno Total_{name}"] = total_return
        metricas_agregadas[f"CAGR_{name}"] = (
            (1 + total_return) ** (1 / years_period) - 1 if years_period > 0 else 0
        )
        vol = r.std() * np.sqrt(252)
        metricas_agregadas[f"Volatilidad_{name}"] = vol
        # Para el mercado usamos el nombre simple "Sharpe", para estrategias "Ratio de Sharpe"
        sharpe_prefix = "Sharpe" if name == "Mercado" else "Ratio de Sharpe"
        metricas_agregadas[f"{sharpe_prefix}_{name}"] = (
            metricas_agregadas[f"CAGR_{name}"] / vol if vol != 0 else 0
        )
        peak = cum_ret.cummax()
        metricas_agregadas[f"MÃ¡ximo Drawdown_{name}"] = ((cum_ret - peak) / peak).min()

    df_viz_agregado = pd.DataFrame(
        {
            "market_cumulative_return": (1 + avg_returns["daily_return"]).cumprod(),
            "tendencia_cumulative_return": (
                1 + avg_returns["tendencia_return"]
            ).cumprod(),
            "bollinger_cumulative_return": (
                1 + avg_returns["bollinger_return"]
            ).cumprod(),
            "rsi_cumulative_return": (1 + avg_returns["rsi_return"]).cumprod(),
            "macd_cumulative_return": (1 + avg_returns["macd_return"]).cumprod(),
            "combinada_cumulative_return": (
                1 + avg_returns["combinada_return"]
            ).cumprod(),
        }
    )

    # Mapear a nombres de mÃ©tricas esperados por el reporte PDF
    metricas_finales = {}
    for k, v in metricas_agregadas.items():
        if "Mercado" in k:
            metricas_finales[k.replace("_", " ")] = v
        else:
            metricas_finales[k] = v

    return df_viz_agregado, metricas_finales



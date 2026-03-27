import numpy as np
import pandas as pd



def calcular_duracion_drawdown(cumulative_returns):
    """Calcula la duraciÃ³n mÃ¡xima de un drawdown en dÃ­as."""
    if cumulative_returns is None or cumulative_returns.empty:
        return 0

    peak = cumulative_returns.cummax()
    drawdown = (cumulative_returns / peak) - 1
    in_drawdown = drawdown < 0
    if not in_drawdown.any():
        return 0

    max_duration = 0
    start_date = None
    for fecha, is_dd in in_drawdown.items():
        if is_dd and start_date is None:
            start_date = fecha
        elif not is_dd and start_date is not None:
            duration = (fecha - start_date).days
            max_duration = max(max_duration, duration)
            start_date = None

    if start_date is not None:
        max_duration = max(max_duration, (in_drawdown.index[-1] - start_date).days)

    return max_duration

def calcular_ulcer_index(drawdown_series):
    """Ãndice de Ulcer (cuadrÃ¡tico) a partir de drawdowns en decimal."""
    if drawdown_series is None or drawdown_series.empty:
        return 0
    return np.sqrt(np.mean(np.square(drawdown_series)))

def calcular_var_cvar(returns, alpha=0.05):
    """Calcula VaR y CVaR histÃ³ricos (no paramÃ©tricos)."""
    if returns is None or returns.empty:
        return 0, 0
    clean_returns = returns.replace([np.inf, -np.inf], np.nan).dropna()
    if clean_returns.empty:
        return 0, 0
    var = np.nanpercentile(clean_returns, alpha * 100)
    tail = clean_returns[clean_returns <= var]
    cvar = tail.mean() if not tail.empty else 0
    return var, cvar

def calcular_metricas_trades(df_backtest, returns):
    """Calcula mÃ©tricas de trades basadas en cambios de posiciÃ³n."""
    metricas = {
        "Trades": 0,
        "Win Rate": 0,
        "Profit Factor": 0,
        "Expectancy": 0,
        "Avg Win": 0,
        "Avg Loss": 0,
        "Time in Market": 0,
    }

    if returns is None or returns.empty:
        return metricas

    if "signal_shifted" in df_backtest.columns:
        signal = df_backtest["signal_shifted"].reindex(returns.index).fillna(0)
    elif "signal" in df_backtest.columns:
        signal = df_backtest["signal"].reindex(returns.index).fillna(0)
    else:
        signal = None

    if signal is not None and not signal.empty:
        metricas["Time in Market"] = float((signal > 0).mean())

    if "position" in df_backtest.columns:
        pos_changes = df_backtest["position"].reindex(returns.index).fillna(0)
    elif signal is not None:
        pos_changes = signal.diff().fillna(0)
    else:
        return metricas

    trade_returns = []
    in_trade = False
    trade_ret = 1.0

    if (
        signal is not None
        and not signal.empty
        and signal.iloc[0] > 0
        and pos_changes.iloc[0] == 0
    ):
        in_trade = True
        trade_ret = 1.0

    for fecha in returns.index:
        change = pos_changes.loc[fecha]
        if change == 1 and not in_trade:
            in_trade = True
            trade_ret = 1.0
        if in_trade:
            trade_ret *= 1 + returns.loc[fecha]
        if change == -1 and in_trade:
            trade_returns.append(trade_ret - 1)
            in_trade = False

    if in_trade:
        trade_returns.append(trade_ret - 1)

    trades = len(trade_returns)
    if trades == 0:
        return metricas

    wins = [r for r in trade_returns if r > 0]
    losses = [r for r in trade_returns if r < 0]

    metricas["Trades"] = trades
    metricas["Win Rate"] = len(wins) / trades if trades else 0
    if losses:
        metricas["Profit Factor"] = sum(wins) / abs(sum(losses)) if wins else 0
    else:
        metricas["Profit Factor"] = np.inf if wins else 0
    metricas["Expectancy"] = float(np.mean(trade_returns)) if trades else 0
    metricas["Avg Win"] = float(np.mean(wins)) if wins else 0
    metricas["Avg Loss"] = float(np.mean(losses)) if losses else 0

    return metricas

def calcular_metricas(df_backtest, nombre_estrategia):
    """FunciÃ³n auxiliar para calcular un conjunto estÃ¡ndar de mÃ©tricas. REQUIERE un DatetimeIndex."""
    returns = df_backtest[nombre_estrategia]
    market_returns = df_backtest["daily_return"]
    cumulative_strategy_returns = (1 + returns).cumprod()
    cumulative_market_returns = (1 + market_returns).cumprod()
    total_return_strategy = cumulative_strategy_returns.iloc[-1] - 1
    total_return_market = cumulative_market_returns.iloc[-1] - 1
    vol_strategy = returns.std() * np.sqrt(252)
    vol_market = market_returns.std() * np.sqrt(252)
    sharpe_strategy = (returns.mean() * 252) / vol_strategy if vol_strategy != 0 else 0
    sharpe_market = (market_returns.mean() * 252) / vol_market if vol_market != 0 else 0
    peak_strategy = cumulative_strategy_returns.cummax()
    drawdown_strategy = (cumulative_strategy_returns - peak_strategy) / peak_strategy
    max_drawdown_strategy = drawdown_strategy.min()
    peak_market = cumulative_market_returns.cummax()
    drawdown_market = (cumulative_market_returns - peak_market) / peak_market
    max_drawdown_market = drawdown_market.min()
    trades = df_backtest[df_backtest["position"] != 0]
    last_entry = trades.loc[trades["position"] == 1]
    last_exit = trades.loc[trades["position"] == -1]
    last_entry_date = (
        last_entry.index[-1].strftime("%Y-%m-%d") if not last_entry.empty else "N/A"
    )
    last_exit_date = (
        last_exit.index[-1].strftime("%Y-%m-%d") if not last_exit.empty else "N/A"
    )
    days_period = (df_backtest.index[-1] - df_backtest.index[0]).days
    years_period = days_period / 365.25
    if years_period > 0:
        cagr_strategy = (1 + total_return_strategy) ** (1 / years_period) - 1
        cagr_market = (1 + total_return_market) ** (1 / years_period) - 1
    else:
        cagr_strategy = 0
        cagr_market = 0

    # Usamos CAGR para el Ratio de Sharpe (Sharpe GeomÃ©trico)
    sharpe_strategy = cagr_strategy / vol_strategy if vol_strategy != 0 else 0
    sharpe_market = cagr_market / vol_market if vol_market != 0 else 0

    downside_strategy = returns.copy()
    downside_strategy[downside_strategy > 0] = 0
    downside_dev_strategy = (
        np.sqrt((downside_strategy**2).mean()) * np.sqrt(252) if len(returns) > 0 else 0
    )
    sortino_strategy = (
        cagr_strategy / downside_dev_strategy if downside_dev_strategy != 0 else 0
    )
    calmar_strategy = (
        cagr_strategy / abs(max_drawdown_strategy) if max_drawdown_strategy != 0 else 0
    )
    ulcer_index_strategy = calcular_ulcer_index(drawdown_strategy)
    var_95_strategy, cvar_95_strategy = calcular_var_cvar(returns)
    dd_duration_strategy = calcular_duracion_drawdown(cumulative_strategy_returns)

    downside_market = market_returns.copy()
    downside_market[downside_market > 0] = 0
    downside_dev_market = (
        np.sqrt((downside_market**2).mean()) * np.sqrt(252)
        if len(market_returns) > 0
        else 0
    )
    sortino_market = (
        cagr_market / downside_dev_market if downside_dev_market != 0 else 0
    )
    calmar_market = (
        cagr_market / abs(max_drawdown_market) if max_drawdown_market != 0 else 0
    )
    ulcer_index_market = calcular_ulcer_index(drawdown_market)
    var_95_market, cvar_95_market = calcular_var_cvar(market_returns)
    dd_duration_market = calcular_duracion_drawdown(cumulative_market_returns)

    trade_stats = calcular_metricas_trades(df_backtest, returns)

    metricas = {
        "Retorno Total": total_return_strategy,
        "CAGR": cagr_strategy,
        "Volatilidad": vol_strategy,
        "Ratio de Sharpe": sharpe_strategy,
        "MÃ¡ximo Drawdown": max_drawdown_strategy,
        "Ratio de Sortino": sortino_strategy,
        "Ratio de Calmar": calmar_strategy,
        "Ulcer Index": ulcer_index_strategy,
        "VaR 95": var_95_strategy,
        "CVaR 95": cvar_95_strategy,
        "DuraciÃ³n Drawdown": dd_duration_strategy,
        "Trades": trade_stats["Trades"],
        "Win Rate": trade_stats["Win Rate"],
        "Profit Factor": trade_stats["Profit Factor"],
        "Expectancy": trade_stats["Expectancy"],
        "Avg Win": trade_stats["Avg Win"],
        "Avg Loss": trade_stats["Avg Loss"],
        "Time in Market": trade_stats["Time in Market"],
        "Retorno Mercado": total_return_market,
        "CAGR Mercado": cagr_market,
        "Sharpe Mercado": sharpe_market,
        "Volatilidad Mercado": vol_market,
        "MÃ¡ximo Drawdown Mercado": max_drawdown_market,
        "Ratio de Sortino Mercado": sortino_market,
        "Ratio de Calmar Mercado": calmar_market,
        "Ulcer Index Mercado": ulcer_index_market,
        "VaR 95 Mercado": var_95_market,
        "CVaR 95 Mercado": cvar_95_market,
        "DuraciÃ³n Drawdown Mercado": dd_duration_market,
        "Ultima Entrada": last_entry_date,
        "Ultima Salida": last_exit_date,
    }
    df_backtest["market_cumulative_return"] = cumulative_market_returns
    df_backtest["strategy_cumulative_return"] = cumulative_strategy_returns
    return df_backtest, metricas

def calcular_metricas_desde_returns(returns):
    """Calcula mÃ©tricas bÃ¡sicas a partir de una serie de retornos."""
    if returns is None:
        return {"CAGR": 0, "Sharpe": 0, "Volatilidad": 0, "Max Drawdown": 0}
    clean = returns.replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return {"CAGR": 0, "Sharpe": 0, "Volatilidad": 0, "Max Drawdown": 0}

    cumulative = (1 + clean).cumprod()
    total_return = cumulative.iloc[-1] - 1
    years = len(clean) / 252
    cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    vol = clean.std() * np.sqrt(252)
    sharpe = cagr / vol if vol != 0 else 0
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak
    max_dd = drawdown.min()

    return {"CAGR": cagr, "Sharpe": sharpe, "Volatilidad": vol, "Max Drawdown": max_dd}

def calcular_slippage_pct(
    df_backtest,
    slippage_bps=0.0,
    slippage_atr_mult=0.0,
    slippage_vol_mult=0.0,
    atr_window=14,
    vol_window=20,
):
    """
    Calcula un slippage dinÃ¡mico en porcentaje basado en bps fijos,
    ATR% y/o volatilidad rolling de retornos diarios.
    """
    slippage = pd.Series(0.0, index=df_backtest.index)

    if slippage_bps:
        slippage += float(slippage_bps) / 10000.0

    if slippage_atr_mult:
        if {"high", "low", "close"}.issubset(df_backtest.columns):
            tr1 = df_backtest["high"] - df_backtest["low"]
            tr2 = (df_backtest["high"] - df_backtest["close"].shift(1)).abs()
            tr3 = (df_backtest["low"] - df_backtest["close"].shift(1)).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=atr_window, min_periods=1).mean()
            atr_pct = (
                (atr / df_backtest["close"])
                .replace([np.inf, -np.inf], np.nan)
                .fillna(0)
            )
            slippage += float(slippage_atr_mult) * atr_pct

    if slippage_vol_mult:
        vol = (
            df_backtest["daily_return"]
            .rolling(window=vol_window, min_periods=1)
            .std()
            .fillna(0)
        )
        slippage += float(slippage_vol_mult) * vol

    return slippage

def bootstrap_metricas_returns(returns, n_iter=300, seed=42):
    if returns is None or returns.empty:
        return {}
    clean = returns.replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return {}

    rng = np.random.default_rng(seed)
    metrics = {"CAGR": [], "Sharpe": [], "Max Drawdown": []}
    arr = clean.values
    for i in range(n_iter):
        if i % 100 == 0 and i > 0:
            print(f"    Bootstrap: i={i}/{n_iter}")
        sample = rng.choice(arr, size=len(arr), replace=True)
        sample_series = pd.Series(sample)
        met = calcular_metricas_desde_returns(sample_series)
        metrics["CAGR"].append(met["CAGR"])
        metrics["Sharpe"].append(met["Sharpe"])
        metrics["Max Drawdown"].append(met["Max Drawdown"])

    def pct(vals, p):
        return float(np.nanpercentile(vals, p)) if len(vals) else 0

    return {
        "CAGR P5": pct(metrics["CAGR"], 5),
        "CAGR P50": pct(metrics["CAGR"], 50),
        "CAGR P95": pct(metrics["CAGR"], 95),
        "Sharpe P5": pct(metrics["Sharpe"], 5),
        "Sharpe P50": pct(metrics["Sharpe"], 50),
        "Sharpe P95": pct(metrics["Sharpe"], 95),
        "MaxDD P5": pct(metrics["Max Drawdown"], 5),
        "MaxDD P50": pct(metrics["Max Drawdown"], 50),
        "MaxDD P95": pct(metrics["Max Drawdown"], 95),
    }



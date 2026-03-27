from estrategia.utils import _to_serializable
from estrategia.metrics import calcular_metricas_desde_returns, calcular_metricas
from estrategia.config_runtime import _validar_y_normalizar_config
import pandas as pd


def test_to_serializable_timestamp():
    ts = pd.Timestamp("2026-02-06")
    assert _to_serializable(ts) == "2026-02-06"


def test_metricas_desde_returns_basic():
    returns = pd.Series([0.01, -0.01, 0.02, 0.0])
    out = calcular_metricas_desde_returns(returns)
    assert set(out.keys()) == {"CAGR", "Sharpe", "Volatilidad", "Max Drawdown"}


def test_config_runtime_normaliza_pesos_y_benchmarks():
    cfg = {
        "benchmarks": ["^IBEX", " ", "^IBEX", "SPY"],
        "pesos_estrategias": {
            "tendencia": 10,
            "bollinger": 10,
            "rsi": 10,
            "macd": 10,
        },
        "slippage": {"bps": -5, "atr_mult": -1, "vol_mult": -0.1},
        "execution_delay": -2,
        "data_cache": {
            "enabled": 1,
            "force_refresh": 0,
            "clear_on_start": 1,
            "max_age_days": "7",
            "max_tickers_per_run": "11",
            "exclude_tickers": ["  spy ", "Ibe.mc", "SPY"],
        },
    }
    out = _validar_y_normalizar_config(cfg)
    assert out["benchmarks"] == ["^IBEX", "SPY"]
    assert abs(sum(out["pesos_estrategias"].values()) - 1.0) < 1e-12
    assert out["execution_delay"] == 0
    assert out["slippage"]["bps"] == 0.0
    assert out["data_cache"]["enabled"] is True
    assert out["data_cache"]["force_refresh"] is False
    assert out["data_cache"]["clear_on_start"] is True
    assert out["data_cache"]["max_age_days"] == 7
    assert out["data_cache"]["max_tickers_per_run"] == 11
    assert out["data_cache"]["exclude_tickers"] == ["SPY", "IBE.MC"]


def test_calcular_metricas_usa_claves_canonicas_ultima_operacion():
    df = pd.DataFrame(
        {
            "strategy_return": [0.0, 0.01, -0.005, 0.0],
            "daily_return": [0.0, 0.008, -0.004, 0.0],
            "position": [0, 1, 0, -1],
        },
        index=pd.date_range("2026-01-01", periods=4, freq="D"),
    )
    _, metricas = calcular_metricas(df, "strategy_return")

    assert "Ultima Entrada" in metricas
    assert "Ultima Salida" in metricas
    assert "Última Entrada" not in metricas
    assert "Última Salida" not in metricas


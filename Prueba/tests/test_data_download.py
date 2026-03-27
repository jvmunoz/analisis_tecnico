import pandas as pd
import numpy as np

from estrategia.data import obtener_datos_historicos


def test_obtener_datos_historicos_mock(monkeypatch):
    idx = pd.date_range("2026-01-01", periods=3, freq="D")
    cols = pd.MultiIndex.from_product(
        [["Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends"], ["AAA"]]
    )
    data = pd.DataFrame(
        [
            [10, 11, 9, 10, 10, 1000, 0.0],
            [10.5, 11.5, 10, 10.5, 10.5, 1200, 0.0],
            [10.2, 11.0, 10, 10.2, 10.2, 1100, 0.1],
        ],
        index=idx,
        columns=cols,
    )

    def fake_download(*args, **kwargs):
        return data

    monkeypatch.setattr("estrategia.data.yf.download", fake_download)

    df = obtener_datos_historicos(["AAA"], "2026-01-01", "2026-01-10")
    assert not df.empty
    assert set(["ticker", "date", "close", "daily_return"]).issubset(df.columns)
    assert df["ticker"].nunique() == 1


def test_end_date_hoy_se_recorta_a_sesion_cerrada(monkeypatch):
    idx = pd.date_range("2026-01-01", periods=3, freq="D")
    cols = pd.MultiIndex.from_product(
        [["Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends"], ["AAA"]]
    )
    data = pd.DataFrame(
        [
            [10, 11, 9, 10, 10, 1000, 0.0],
            [10.5, 11.5, 10, 10.5, 10.5, 1200, 0.0],
            [10.2, 11.0, 10, 10.2, 10.2, 1100, 0.1],
        ],
        index=idx,
        columns=cols,
    )
    calls = []

    def fake_download(*args, **kwargs):
        calls.append(kwargs.copy())
        return data

    monkeypatch.setattr("estrategia.data.yf.download", fake_download)

    today_str = pd.Timestamp.now().normalize().strftime("%Y-%m-%d")
    df = obtener_datos_historicos(["AAA"], "2026-01-01", today_str)

    assert not df.empty
    assert calls, "Se esperaba al menos una llamada a yfinance"
    assert calls[0]["end"] == today_str

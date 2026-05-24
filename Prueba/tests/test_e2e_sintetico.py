import pandas as pd

from estrategia import app
from estrategia.data import obtener_datos_historicos
from estrategia.enriched import (
    calcular_analisis_enriquecido,
    exportar_explicabilidad_senales,
)
from estrategia.portfolio import gestionar_journal_operaciones


def _cache_sintetica(ticker, start="2026-01-01", periods=45):
    fechas = pd.bdate_range(start, periods=periods)
    precios = [100 + (i * 0.15) for i in range(periods)]
    rows = []
    for fecha, close in zip(fechas, precios):
        rows.append(
            {
                "ticker": ticker,
                "date": fecha,
                "open": close * 0.995,
                "high": close * 1.01,
                "low": close * 0.99,
                "close": close,
                "volume": 100000,
                "dividends": 0.0,
            }
        )
    return pd.DataFrame(rows)


def _df_viz_sintetico(ticker="AAA.MC"):
    fechas = pd.bdate_range("2026-01-01", periods=130)
    closes = [100 - min(i, 80) * 0.03 for i in range(130)]
    rows = []
    for i, (fecha, close) in enumerate(zip(fechas, closes)):
        rows.append(
            {
                "date": fecha,
                "close": close,
                "high": close * 1.03,
                "low": close * 0.995,
                "volume": 100000 + i,
                "dividends": 0.0,
                "atr_perc": 1.5,
                "rsi": 34.0,
                "adx": 22.0,
                "macd_histogram": 0.08,
                "sma_short": close + 2,
                "sma_long": close,
                "sma_200": close - 1,
                "rvol": 0.35,
            }
        )
    return pd.DataFrame(rows).set_index("date")


def test_e2e_sintetico_cache_analisis_journal_y_export(monkeypatch):
    downloads = []

    def fake_read_cache(cache_dir, ticker, max_age_days=None):
        return _cache_sintetica(ticker)

    def fake_download_single_ticker(*args, **kwargs):
        downloads.append((args, kwargs))
        raise AssertionError("No deberia descargarse si la cache cubre la ventana")

    monkeypatch.setattr("estrategia.data._read_cache", fake_read_cache)
    monkeypatch.setattr("estrategia.data._download_single_ticker", fake_download_single_ticker)
    monkeypatch.setattr("estrategia.data._write_cache", lambda *args, **kwargs: None)

    datos = obtener_datos_historicos(
        ["AAA.MC"],
        "2026-01-01",
        "2026-02-20",
        cache_config={"enabled": True, "force_refresh": False},
    )

    assert downloads == []
    assert datos is not None
    assert not datos.empty
    assert set(["ticker", "date", "close", "daily_return"]).issubset(datos.columns)

    analisis = calcular_analisis_enriquecido(
        [{"ticker": "AAA.MC", "df_viz": _df_viz_sintetico()}]
    )
    assert len(analisis) == 1
    assert analisis[0]["Ticker"] == "AAA.MC"
    assert "Motivo_Semaforo" in analisis[0]

    captured_csv = {}

    def fake_to_csv(self, filename, index=False, encoding=None, **kwargs):
        captured_csv[str(filename).split("\\")[-1].split("/")[-1]] = self.copy()

    monkeypatch.setattr(pd.DataFrame, "to_csv", fake_to_csv)

    senales = [
        {
            "Ticker": "AAA.MC",
            "Semaforo": "VERDE",
            "Setup": "Pullback",
            "Entrada": 100.0,
            "Stop": 96.0,
            "T1": 104.0,
            "T2": 108.0,
            "Precio": 100.5,
        },
        {
            "Ticker": "BBB.MC",
            "Semaforo": "VERDE",
            "Setup": "Pullback",
            "Entrada": 100.0,
            "Stop": 96.0,
            "T1": 104.0,
            "T2": 108.0,
            "Precio": 104.0,
        },
    ]
    gestionar_journal_operaciones(
        senales,
        fecha_v="2026-05-12",
        rules_config={"max_apertura_sobre_entrada_pct": 1.5},
    )
    exportar_explicabilidad_senales(analisis, fecha_v="2026-05-12")

    captured_md = {}

    class FakeFile:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def write(self, text):
            captured_md["text"] = captured_md.get("text", "") + text

    def fake_open(filename, mode="r", encoding=None):
        captured_md["filename"] = filename
        captured_md["encoding"] = encoding
        return FakeFile()

    def fake_cargar_csv(filename):
        return captured_csv.get(filename, pd.DataFrame())

    monkeypatch.setattr("builtins.open", fake_open)
    monkeypatch.setattr(app, "_cargar_csv_si_existe", fake_cargar_csv)
    resumen = app._generar_resumen_ejecutivo_md(
        fecha_v="2026-05-12",
        summary={
            "tickers_objetivo": 1,
            "tickers_procesados": 1,
            "tickers_con_resultado": 1,
            "duration_seconds": 1.23,
        },
        error_log=[],
        enriched_result={
            "breadth": 100.0,
            "exposure": 80.0,
            "data_enriquecida": analisis,
        },
        signal_log=[],
    )

    journal = captured_csv["journal_operaciones_hasta_20260512.csv"]
    eventos = captured_csv["journal_eventos_hasta_20260512.csv"]
    explicabilidad = captured_csv["EXPLICABILIDAD_SENALES_20260512.csv"]
    resumen_text = captured_md["text"]

    assert resumen == "RESUMEN_EJECUTIVO_20260512.md"
    assert journal["Ticker"].tolist() == ["AAA.MC"]
    assert "BBB.MC" not in journal["Ticker"].tolist()
    assert eventos.loc[0, "Tipo_Evento"] == "APERTURA"
    assert "Operacion_ID" not in eventos.columns
    assert "Motivo_Semaforo" in explicabilidad.columns
    assert "# Resumen ejecutivo - 2026-05-12" in resumen_text
    assert "- Nuevas aperturas: 1" in resumen_text

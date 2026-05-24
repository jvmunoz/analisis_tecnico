import pandas as pd

from estrategia import app


def test_generar_resumen_ejecutivo_md(monkeypatch):
    captured = {}

    class FakeFile:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def write(self, text):
            captured["text"] = captured.get("text", "") + text

    def fake_open(filename, mode="r", encoding=None):
        captured["filename"] = filename
        captured["mode"] = mode
        captured["encoding"] = encoding
        return FakeFile()

    def fake_cargar_csv(filename):
        if filename.startswith("journal_eventos"):
            return pd.DataFrame(
                [
                    {
                        "Tipo_Evento": "APERTURA",
                        "Ticker": "IBE.MC",
                        "Setup": "Pullback",
                        "Estado_Nuevo": "ABIERTA",
                        "Motivo": "Nueva senal VERDE",
                        "Precio": 10.5,
                        "P&L_%": 0.0,
                    },
                    {
                        "Tipo_Evento": "ALERTA",
                        "Ticker": "SAN.MC",
                        "Setup": "Breakout",
                        "Estado_Nuevo": "VIGILANCIA (T1)",
                        "Motivo": "Proximidad a T1",
                        "Precio": 6.2,
                        "P&L_%": 3.1,
                    },
                ]
            )
        return pd.DataFrame()

    monkeypatch.setattr("builtins.open", fake_open)
    monkeypatch.setattr(app, "_cargar_csv_si_existe", fake_cargar_csv)

    filename = app._generar_resumen_ejecutivo_md(
        fecha_v="2026-05-12",
        summary={
            "tickers_objetivo": 35,
            "tickers_procesados": 34,
            "tickers_con_resultado": 33,
            "duration_seconds": 12.34,
        },
        error_log=[],
        enriched_result={
            "breadth": 62.5,
            "exposure": 80.0,
            "data_enriquecida": [
                {
                    "Ticker": "IBE.MC",
                    "Semaforo": "VERDE",
                    "Estado": "EJECUTAR",
                    "Setup": "Pullback",
                    "Score": 8.1,
                    "Entrada": 10.0,
                    "Stop": 9.5,
                    "Motivo_Semaforo": "VERDE: cumple criterios de Pullback",
                    "Checks_Fallidos": "",
                }
            ],
        },
        signal_log=[{"ticker": "IBE.MC"}],
    )

    text = captured["text"]
    assert filename == "RESUMEN_EJECUTIVO_20260512.md"
    assert captured["encoding"] == "utf-8"
    assert "# Resumen ejecutivo - 2026-05-12" in text
    assert "- Nuevas aperturas: 1" in text
    assert "- Alertas T1/T2: 1" in text
    assert "- IBE.MC: VERDE / EJECUTAR / Pullback" in text
    assert "- Senales trazadas: 1" in text

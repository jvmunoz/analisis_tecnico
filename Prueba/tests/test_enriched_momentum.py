import pandas as pd

from estrategia.enriched import (
    calcular_analisis_enriquecido,
    exportar_explicabilidad_senales,
)
from estrategia.levels import ajustar_targets_por_resistencias


def _df_viz(closes, macd_hist=-0.1):
    rows = []
    for i, close in enumerate(closes):
        rows.append(
            {
                "date": pd.Timestamp("2026-01-01") + pd.Timedelta(days=i),
                "close": close,
                "low": close * 0.998,
                "high": close * 1.2,
                "atr_perc": 2.6,
                "rsi": 32.0,
                "adx": 21.0,
                "macd_histogram": macd_hist,
                "sma_short": 105.0,
                "sma_long": 100.0,
                "rvol": 0.34,
            }
        )
    return pd.DataFrame(rows)


def _analizar(df_viz, rules_config=None):
    return calcular_analisis_enriquecido(
        [{"ticker": "AENA.MC", "df_viz": df_viz}], rules_config=rules_config
    )[0]


def test_pullback_con_caida_fuerte_reciente_no_es_verde():
    df_viz = _df_viz(
        [
            101.0,
            100.8,
            100.5,
            100.2,
            100.0,
            99.5,
            98.0,
            96.5,
            95.0,
            94.0,
        ]
    )

    out = _analizar(df_viz)

    assert out["Setup"] == "Pullback"
    assert out["Semaforo"] == "AMARILLO"
    assert out["Estado"] == "VIGILAR"
    assert out["Inputs"]["caida_reciente_fuerte"] is True
    assert out["Motivo_Semaforo"] == "AMARILLO: faltan condiciones para VERDE"
    assert "Caida reciente fuerte" in out["Checks_Fallidos"]
    assert out["Motivo_No_Apertura"].startswith("No abre:")


def test_pullback_sin_caida_fuerte_reciente_puede_ser_verde():
    df_viz = _df_viz(
        [
            100.0,
            99.8,
            99.6,
            99.4,
            99.2,
            99.0,
            98.8,
            98.6,
            98.4,
            98.2,
        ],
        macd_hist=0.1,
    )

    out = _analizar(df_viz)

    assert out["Setup"] == "Pullback"
    assert out["Semaforo"] == "VERDE"
    assert out["Estado"] == "EJECUTAR"
    assert out["Motivo_Semaforo"] == "VERDE: cumple criterios de Pullback"
    assert "Cerca de soporte" in out["Checks_Verdes"]
    assert out["Motivo_No_Apertura"] == ""
    assert out["Inputs"]["caida_reciente_fuerte"] is False
    assert "Soporte_20" in out
    assert "Resistencia_120" in out
    assert "Dist_Soporte_60_%" in out


def test_reglas_enriquecidas_permiten_endurecer_rvol_minimo():
    df_viz = _df_viz(
        [
            100.0,
            99.8,
            99.6,
            99.4,
            99.2,
            99.0,
            98.8,
            98.6,
            98.4,
            98.2,
        ],
        macd_hist=0.1,
    )

    out = _analizar(df_viz, rules_config={"rvol_min": 0.50})

    assert out["Setup"] == "Pullback"
    assert out["Semaforo"] == "AMARILLO"
    assert out["Estado"] == "VIGILAR"
    assert out["Inputs"]["reglas_enriquecidas"]["rvol_min"] == 0.50
    assert "RVOL insuficiente" in out["Checks_Fallidos"]


def test_pullback_rompiendo_soporte_20_con_macd_bajista_no_es_verde():
    df_viz = _df_viz(
        [
            100.0,
            100.2,
            100.1,
            100.3,
            100.2,
            100.1,
            100.0,
            100.2,
            100.1,
            98.0,
        ],
        macd_hist=-0.1,
    )

    out = _analizar(df_viz)

    assert out["Setup"] == "Pullback"
    assert out["Semaforo"] == "AMARILLO"
    assert out["Estado"] == "VIGILAR"
    assert out["Inputs"]["ruptura_soporte_20"] is True


def test_targets_se_ajustan_a_resistencias_si_encajan_en_rango_riesgo():
    t1, t2, metodo_t1, metodo_t2 = ajustar_targets_por_resistencias(
        entrada=100.0,
        stop=95.0,
        niveles_sr={
            "Resistencia_20": 104.8,
            "Resistencia_60": 110.2,
            "Resistencia_120": 118.0,
        },
    )

    assert t1 == 104.8
    assert t2 == 110.2
    assert metodo_t1 == "Resistencia"
    assert metodo_t2 == "Resistencia"


def test_targets_mantienen_riesgo_si_no_hay_resistencia_valida():
    t1, t2, metodo_t1, metodo_t2 = ajustar_targets_por_resistencias(
        entrada=100.0,
        stop=95.0,
        niveles_sr={
            "Resistencia_20": 102.0,
            "Resistencia_60": 130.0,
            "Resistencia_120": 140.0,
        },
    )

    assert t1 == 105.0
    assert t2 == 110.0
    assert metodo_t1 == "Riesgo"
    assert metodo_t2 == "Riesgo"


def test_exporta_csv_explicabilidad_senales(monkeypatch):
    df_viz = _df_viz(
        [
            100.0,
            99.8,
            99.6,
            99.4,
            99.2,
            99.0,
            98.8,
            98.6,
            98.4,
            98.2,
        ],
        macd_hist=0.1,
    )
    out = _analizar(df_viz)
    captured = {}

    def fake_to_csv(self, filename, index=False, encoding=None):
        captured["filename"] = filename
        captured["index"] = index
        captured["encoding"] = encoding
        captured["df"] = self.copy()

    monkeypatch.setattr(pd.DataFrame, "to_csv", fake_to_csv)

    filename = exportar_explicabilidad_senales([out], fecha_v="2026-05-12")
    exported = captured["df"]

    assert filename == "EXPLICABILIDAD_SENALES_20260512.csv"
    assert captured["filename"] == filename
    assert captured["index"] is False
    assert captured["encoding"] == "utf-8-sig"
    assert exported.loc[0, "Ticker"] == "AENA.MC"
    assert exported.loc[0, "Motivo_Semaforo"] == "VERDE: cumple criterios de Pullback"
    assert "Checks_Fallidos" in exported.columns

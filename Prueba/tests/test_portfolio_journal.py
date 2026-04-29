import pandas as pd

from estrategia.portfolio import (
    columnas_exportacion_eventos,
    normalizar_y_deduplicar_eventos,
    reconstruir_eventos_desde_snapshots,
)


EVENTOS_COLS = [
    "Fecha_Evento",
    "Operacion_ID",
    "Fecha_Deteccion",
    "Ticker",
    "Setup",
    "Estado_Previo",
    "Estado_Nuevo",
    "Tipo_Evento",
    "Motivo",
    "Precio_Entrada",
    "Stop_Inicial",
    "T1",
    "T2",
    "Precio",
    "P&L_%",
]


def _snapshot(rows):
    defaults = {
        "Fecha_Deteccion": "2026-03-01",
        "Fecha_Actualizacion": "",
        "Fecha_Cierre": "",
        "Setup": "Pullback",
        "Precio_Entrada": 9.0,
        "Stop_Inicial": 8.0,
        "T1": 10.0,
        "T2": 11.0,
        "Precio_Ultimo": 10.0,
        "P&L_%": 0.0,
    }
    return pd.DataFrame([{**defaults, **row} for row in rows])


def test_reconstruye_eventos_entre_snapshots():
    rows_16 = [
        {"Ticker": "FER.MC", "Fecha_Deteccion": "2026-03-06", "Estado_Actual": "ABIERTA"},
        {"Ticker": "CABK.MC", "Fecha_Deteccion": "2026-03-03", "Estado_Actual": "ABIERTA"},
        {"Ticker": "ITX.MC", "Fecha_Deteccion": "2026-03-30", "Estado_Actual": "ABIERTA"},
        {"Ticker": "GRF.MC", "Fecha_Deteccion": "2026-03-27", "Estado_Actual": "ABIERTA"},
        {"Ticker": "IAG.MC", "Fecha_Deteccion": "2026-03-20", "Estado_Actual": "ABIERTA"},
        {"Ticker": "SAN.MC", "Fecha_Deteccion": "2026-03-13", "Estado_Actual": "ABIERTA"},
        {"Ticker": "ACX.MC", "Fecha_Deteccion": "2026-03-13", "Estado_Actual": "ABIERTA"},
        {"Ticker": "BBVA.MC", "Fecha_Deteccion": "2026-03-12", "Estado_Actual": "ABIERTA"},
    ]
    rows_17 = [
        {**row, "Estado_Actual": "VIGILANCIA (T2)"}
        if row["Ticker"] in {"FER.MC", "CABK.MC"}
        else {**row, "Estado_Actual": "CERRADA (TARGET)"}
        for row in rows_16
    ]

    eventos = reconstruir_eventos_desde_snapshots(
        [
            (pd.Timestamp("2026-04-17"), _snapshot(rows_17)),
            (pd.Timestamp("2026-04-16"), _snapshot(rows_16)),
        ],
        EVENTOS_COLS,
    )
    cambios_17 = eventos[eventos["Fecha_Evento"] == "2026-04-17"]

    assert len(cambios_17) == 8
    assert "Fecha_Deteccion" in cambios_17.columns
    assert "Operacion_ID" in cambios_17.columns
    assert "20260306|FER.MC|Pullback" in set(cambios_17["Operacion_ID"])
    assert set(cambios_17["Ticker"]) == {
        "FER.MC",
        "CABK.MC",
        "ITX.MC",
        "GRF.MC",
        "IAG.MC",
        "SAN.MC",
        "ACX.MC",
        "BBVA.MC",
    }
    assert set(
        cambios_17[cambios_17["Estado_Nuevo"] == "VIGILANCIA (T2)"]["Tipo_Evento"]
    ) == {"ALERTA"}
    assert set(
        cambios_17[cambios_17["Estado_Nuevo"] == "CERRADA (TARGET)"]["Tipo_Evento"]
    ) == {"CIERRE"}


def test_reconstruccion_no_inventa_cierre_si_primer_snapshot_ya_esta_cerrado():
    eventos = reconstruir_eventos_desde_snapshots(
        [
            (
                pd.Timestamp("2026-04-17"),
                _snapshot(
                    [
                        {
                            "Ticker": "ITX.MC",
                            "Fecha_Deteccion": "2026-03-30",
                            "Estado_Actual": "CERRADA (TARGET)",
                        }
                    ]
                ),
            )
        ],
        EVENTOS_COLS,
    )

    assert eventos.empty


def test_deduplicacion_trata_estado_previo_vacio_y_nan_como_mismo_evento():
    eventos = pd.DataFrame(
        [
            {
                "Fecha_Evento": "2026-04-17",
                "Ticker": "AENA.MC",
                "Setup": "Pullback",
                "Estado_Previo": pd.NA,
                "Estado_Nuevo": "ABIERTA",
                "Tipo_Evento": "APERTURA",
                "Motivo": "Nueva señal VERDE",
                "Precio_Entrada": 10.0,
                "Stop_Inicial": 9.0,
                "T1": 11.0,
                "T2": 12.0,
                "Precio": 10.0,
                "P&L_%": 0.0,
            },
            {
                "Fecha_Evento": "2026-04-17",
                "Ticker": "AENA.MC",
                "Setup": "Pullback",
                "Estado_Previo": "",
                "Estado_Nuevo": "ABIERTA",
                "Tipo_Evento": "APERTURA",
                "Motivo": "Nueva señal VERDE",
                "Precio_Entrada": 10.0,
                "Stop_Inicial": 9.0,
                "T1": 11.0,
                "T2": 12.0,
                "Precio": 10.0,
                "P&L_%": 0.0,
            },
        ]
    )

    out = normalizar_y_deduplicar_eventos(eventos, EVENTOS_COLS)

    assert len(out) == 1


def test_operacion_id_distingue_varias_aperturas_mismo_ticker_setup():
    rows_18 = [
        {
            "Ticker": "MAP.MC",
            "Fecha_Deteccion": "2026-02-11",
            "Estado_Actual": "ABIERTA",
        },
        {
            "Ticker": "MAP.MC",
            "Fecha_Deteccion": "2026-02-12",
            "Estado_Actual": "ABIERTA",
        },
    ]
    rows_19 = [
        {**row, "Estado_Actual": "VIGILANCIA (T1)"}
        for row in rows_18
    ]

    eventos = reconstruir_eventos_desde_snapshots(
        [
            (pd.Timestamp("2026-02-18"), _snapshot(rows_18)),
            (pd.Timestamp("2026-02-19"), _snapshot(rows_19)),
        ],
        EVENTOS_COLS,
    )
    cambios = eventos[eventos["Fecha_Evento"] == "2026-02-19"]

    assert set(cambios["Operacion_ID"]) == {
        "20260211|MAP.MC|Pullback",
        "20260212|MAP.MC|Pullback",
    }
    assert set(cambios["Fecha_Deteccion"]) == {"2026-02-11", "2026-02-12"}


def test_operacion_id_es_interno_y_no_se_exporta_en_journal_eventos():
    assert "Operacion_ID" in EVENTOS_COLS
    assert "Operacion_ID" not in columnas_exportacion_eventos(EVENTOS_COLS)
    assert "Precio_Entrada" in columnas_exportacion_eventos(EVENTOS_COLS)
    assert "Stop_Inicial" in columnas_exportacion_eventos(EVENTOS_COLS)
    assert "T1" in columnas_exportacion_eventos(EVENTOS_COLS)
    assert "T2" in columnas_exportacion_eventos(EVENTOS_COLS)


def test_evento_incluye_precio_entrada_y_precio_evento():
    eventos = reconstruir_eventos_desde_snapshots(
        [
            (
                pd.Timestamp("2026-02-18"),
                _snapshot(
                    [
                        {
                            "Ticker": "MAP.MC",
                            "Fecha_Deteccion": "2026-02-11",
                            "Estado_Actual": "ABIERTA",
                            "Precio_Entrada": 8.0,
                            "Stop_Inicial": 7.0,
                            "T1": 9.0,
                            "T2": 10.0,
                            "Precio_Ultimo": 8.5,
                        }
                    ]
                ),
            ),
            (
                pd.Timestamp("2026-02-19"),
                _snapshot(
                    [
                        {
                            "Ticker": "MAP.MC",
                            "Fecha_Deteccion": "2026-02-11",
                            "Estado_Actual": "VIGILANCIA (T1)",
                            "Precio_Entrada": 8.0,
                            "Stop_Inicial": 7.0,
                            "T1": 9.0,
                            "T2": 10.0,
                            "Precio_Ultimo": 9.0,
                        }
                    ]
                ),
            ),
        ],
        EVENTOS_COLS,
    )

    cambio = eventos[eventos["Fecha_Evento"] == "2026-02-19"].iloc[0]
    assert cambio["Precio_Entrada"] == 8.0
    assert cambio["Stop_Inicial"] == 7.0
    assert cambio["T1"] == 9.0
    assert cambio["T2"] == 10.0
    assert cambio["Precio"] == 9.0

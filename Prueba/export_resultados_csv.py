import json
import pandas as pd

INPUT_JSON = "RESULTADOS_20260206.json"
OUT_METRICAS = "RESULTADOS_20260206_metricas.csv"
OUT_OPERACIONES = "RESULTADOS_20260206_operaciones.csv"
OUT_VIZ = "RESULTADOS_20260206_viz.csv"
OUT_METRICAS_PARQUET = "RESULTADOS_20260206_metricas.parquet"
OUT_OPERACIONES_PARQUET = "RESULTADOS_20260206_operaciones.parquet"
OUT_VIZ_PARQUET = "RESULTADOS_20260206_viz.parquet"
ULTIMA_ENTRADA = "Última Entrada"
ULTIMA_SALIDA = "Última Salida"
ULTIMA_ENTRADA_LEGACY = ULTIMA_ENTRADA.encode("utf-8").decode("latin1")
ULTIMA_SALIDA_LEGACY = ULTIMA_SALIDA.encode("utf-8").decode("latin1")


def _get_first_value(d, keys, default=None):
    if not isinstance(d, dict):
        return default
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return default


def main():
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    tickers = data.get("tickers", [])

    # 1) Metricas (una fila por ticker)
    rows_metricas = []
    for t in tickers:
        row = {
            "ticker": t.get("ticker"),
            "ganadora": t.get("ganadora"),
            "precio_actual": t.get("precio_actual"),
        }
        metricas = t.get("metricas", {})
        row.update(metricas)
        rows_metricas.append(row)
    if rows_metricas:
        df_metricas = pd.DataFrame(rows_metricas)
        df_metricas.to_csv(OUT_METRICAS, index=False, encoding="utf-8")
        df_metricas.to_parquet(OUT_METRICAS_PARQUET, index=False)

    # 2) Operaciones (una fila por estrategia/ticker)
    rows_ops = []
    for t in tickers:
        for op in t.get("operaciones", []) or []:
            rows_ops.append(
                {
                    "ticker": t.get("ticker"),
                    "estrategia": op.get("Estrategia"),
                    "estado": op.get("Estado"),
                    "ultima_entrada": _get_first_value(
                        op, ("Ultima Entrada", ULTIMA_ENTRADA, ULTIMA_ENTRADA_LEGACY)
                    ),
                    "ultima_salida": _get_first_value(
                        op, ("Ultima Salida", ULTIMA_SALIDA, ULTIMA_SALIDA_LEGACY)
                    ),
                }
            )
    if rows_ops:
        df_ops = pd.DataFrame(rows_ops)
        df_ops.to_csv(OUT_OPERACIONES, index=False, encoding="utf-8")
        df_ops.to_parquet(OUT_OPERACIONES_PARQUET, index=False)

    # 3) df_viz (serie completa en formato largo)
    rows_viz = []
    for t in tickers:
        for rec in t.get("df_viz", []) or []:
            rec = dict(rec)
            rec["ticker"] = t.get("ticker")
            rows_viz.append(rec)
    if rows_viz:
        df_viz = pd.DataFrame(rows_viz)
        if "dividends" in df_viz.columns:
            df_viz["dividends"] = pd.to_numeric(
                df_viz["dividends"]
                .astype(str)
                .str.replace(r"[^0-9.\-]", "", regex=True),
                errors="coerce",
            )
        df_viz.to_csv(OUT_VIZ, index=False, encoding="utf-8")
        df_viz.to_parquet(OUT_VIZ_PARQUET, index=False)

    print("CSV + Parquet generados:")
    print(f"- {OUT_METRICAS}")
    print(f"- {OUT_OPERACIONES}")
    print(f"- {OUT_VIZ}")
    print(f"- {OUT_METRICAS_PARQUET}")
    print(f"- {OUT_OPERACIONES_PARQUET}")
    print(f"- {OUT_VIZ_PARQUET}")


if __name__ == "__main__":
    main()

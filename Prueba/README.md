# EstrategiaCombinadaRSI

Sistema de analisis cuantitativo y backtesting con estrategias combinadas (Tendencia, Bollinger, RSI, MACD), reportes PDF y exportacion estructurada.

## Requisitos
- Python 3.13+
- Dependencias principales: pandas, numpy, yfinance, matplotlib, plotly, scipy, reportlab
- Para parquet: pyarrow
- Para tests: pytest

## Ejecucion rapida
```powershell
python EstrategiaCombinadaRSI.py --batch
```

Modo interactivo con pregunta de fecha fin:
```powershell
python EstrategiaCombinadaRSI.py --interactive
```

## Ejemplo de configuracion (minimo)
```json
{
  "ask_end_date": true,
  "benchmarks": ["^IBEX"],
  "data_quality_report": true,
  "data_validation": {
    "enabled": true,
    "min_rows_per_ticker": 252,
    "max_missing_close_pct": 0.05,
    "max_zero_volume_pct": 0.5
  }
}
```

## Flujo recomendado
1) Ejecuta `--interactive` y define fecha fin.
2) Revisa `DATA_QUALITY_*` y `DATA_VALIDATION_*`.
3) Abre `INFORME_*` y `DASHBOARD_*`.
4) Si necesitas integracion, usa `RESULTADOS_*` o `RESULTADOS_VIZ_*`.

## Configuracion
Archivo principal: `config.json` (ver `config.example.json`).

Claves utiles:
- `ask_end_date`: si `true`, siempre pregunta la fecha fin.
- `benchmarks`: lista de tickers benchmark (ej: ["^IBEX","SPY"]).
- `data_quality_report`: genera `DATA_QUALITY_*.csv`.
- `data_validation`: valida y descarta tickers.
- `export_results`: exporta JSON y Parquet.
- `signal_trace`: exporta trazas de senales.
- `reproducibilidad`: semilla + snapshot.
- `error_summary`: resumen de errores.
- `performance`: limites de ticks procesados.

## Estructura del proyecto
- `EstrategiaCombinadaRSI.py`: runner
- `estrategia/`: modulos
  - `app.py`: orquestacion
  - `config_runtime.py`: config, watchdog, runtime
  - `data.py`: descarga/limpieza
  - `metrics.py`: metricas
  - `strategies.py`: estrategias
  - `analysis.py`: walk-forward, sensibilidad, stress
  - `reports_matplotlib.py`: PDFs matplotlib
  - `reports_reportlab.py`: PDFs reportlab
  - `enriched.py`: analisis enriquecido
  - `portfolio.py`: cartera/journal
  - `utils.py`: helpers

## Salidas principales
- PDFs: `INFORME_*`, `DASHBOARD_*`, `INFORME_SENSIBILIDAD_*`
- CSV: `DATA_QUALITY_*`, `DATA_VALIDATION_*`, `STRESS_*`, `WALK_FORWARD_*`
- JSON/Parquet: `RESULTADOS_*`, `RESULTADOS_VIZ_*`
- Trazas: `SENIALES_*`
- Snapshot: `RUN_SNAPSHOT_*`
- Errores: `ERROR_RESUMEN_*`

## Resolucion de problemas
- Si no responde: revisa `heartbeat_seconds` y `runtime_limit_minutes`.
- Si falta Parquet: instala `pyarrow`.
- Si hay errores por ticker: revisa `ERROR_RESUMEN_*`.

## Tests
```powershell
pytest -q
```

## Exportar resultados a CSV/Parquet
Script auxiliar:
```powershell
python export_resultados_csv.py
```

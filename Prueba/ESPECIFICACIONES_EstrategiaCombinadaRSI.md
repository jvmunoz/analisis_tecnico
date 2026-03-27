# Especificacion de Requisitos de Software (SRS)
# Sistema: EstrategiaCombinadaRSI

## 1. Introduccion
### 1.1 Proposito
Este documento define los requisitos funcionales y no funcionales del script `EstrategiaCombinadaRSI.py`, que ejecuta analisis cuantitativo de acciones, backtesting de estrategias tecnicas y generacion de reportes.

### 1.2 Alcance
El sistema obtiene datos historicos de mercado, integra una cartera personal, ejecuta estrategias (Tendencia, Bollinger, RSI, MACD) y una combinacion ponderada, calcula metricas de rendimiento, realiza analisis avanzados (walk-forward, sensibilidad y stress tests) y produce informes PDF/PNG/CSV. El foco operativo principal es el IBEX 35, con soporte para tickers adicionales.

### 1.3 Definiciones, acronimos y abreviaturas
- CAGR: Tasa de crecimiento anual compuesta.
- VaR/CVaR: Valor en Riesgo / Valor en Riesgo Condicional.
- IBEX: Indice bursatil principal de Espana.
- OHLC: Open, High, Low, Close.
- SRS: Software Requirements Specification.

### 1.4 Referencias
- Archivo del sistema: `Prueba/EstrategiaCombinadaRSI.py`.

### 1.5 Vision general
El documento describe: contexto de operacion, interfaces, requisitos funcionales, requisitos no funcionales, restricciones y criterios de aceptacion.

## 2. Descripcion general
### 2.1 Perspectiva del producto
El sistema es un script de analisis cuantitativo monolitico que combina descarga de datos, procesamiento, backtesting, analisis avanzado y reporting en una ejecucion batch.

### 2.2 Funciones del producto
- Descargar y normalizar datos historicos de mercado.
- Integrar datos de cartera personal desde CSV.
- Ajustar datos por dividendos y splits huerfanos.
- Ejecutar estrategias tecnicas y una estrategia combinada.
- Calcular metricas de rendimiento y estadisticas de trades.
- Ejecutar analisis avanzados (walk-forward, sensibilidad, stress tests).
- Generar informes y dashboards en PDF/PNG/CSV.

### 2.3 Caracteristicas de los usuarios
- Usuario tecnico con conocimientos basicos de finanzas y ejecucion de scripts Python.
- Usuario con acceso local al entorno de ejecucion y archivos de entrada.

### 2.4 Entorno operativo
- Python 3.x.
- Dependencias: pandas, numpy, yfinance, matplotlib, plotly, scipy, reportlab, requests.
- Sistema operativo compatible con Python (Windows confirmado por rutas locales).

### 2.5 Restricciones
- Dependencia de Yahoo Finance para precios y dividendos.
- Uso de `cartera.csv` e `ibex_constituents_history.csv` si existen.
- El analisis avanzado puede limitarse por rendimiento en grandes universos de tickers.

### 2.6 Suposiciones y dependencias
- Los datos de mercado pueden contener faltantes; el sistema incluye saneamiento basico.
- La deteccion de splits huerfanos es heuristica.
- El usuario provee formatos correctos en CSV de cartera.

## 3. Requisitos de interfaces externas
### 3.1 Interfaces de usuario
- Entrada interactiva por consola para seleccionar fecha fin del backtest.
- Salidas por consola con progreso y avisos.

### 3.2 Interfaces de hardware
- No aplica.

### 3.3 Interfaces de software
- API de Yahoo Finance via `yfinance`.
- Librerias de graficos y PDF: matplotlib, plotly, reportlab.
- Sistema de archivos local para lectura/escritura de CSV/PNG/PDF.
- Archivo de configuracion externo (`config.json` o `config.yaml`) para parametros y modo de ejecucion.
- Exportacion estructurada de resultados (`RESULTADOS_*.json`, `RESULTADOS_*.parquet`, `RESULTADOS_VIZ_*.parquet`).
- Reportes de calidad y validacion de datos (`DATA_QUALITY_*.csv`, `DATA_VALIDATION_*.csv`).
- Trazabilidad de senales (`SENIALES_*.csv`/`SENIALES_*.json`).
- Snapshot de ejecucion reproducible (`RUN_SNAPSHOT_*.json`).

### 3.4 Interfaces de comunicacion
- HTTP(s) para descarga de datos de Yahoo Finance (via yfinance).

## 4. Requisitos funcionales
### 4.1 Ingestion de datos
RF-1: El sistema debe descargar datos historicos de precios y dividendos para una lista de tickers en un rango de fechas configurado.
RF-2: El sistema debe ajustar OHLC usando el factor `Adj Close / Close` para preservar dividendos.
RF-3: El sistema debe soportar descarga de un solo ticker y multiples tickers con estructura MultiIndex.
RF-4: El sistema debe crear la columna `dividends` si no existe en los datos obtenidos.

### 4.2 Saneamiento y normalizacion
RF-5: El sistema debe detectar splits huerfanos mediante caidas abruptas (>50%) y estabilidad posterior.
RF-6: El sistema debe normalizar los precios previos cuando detecte un split huerfano con ratio estimado valido (2 a 20).
RF-7: El sistema debe calcular `daily_return` por ticker y excluir filas sin retorno diario.

### 4.3 Cartera personal
RF-8: El sistema debe cargar `cartera.csv` cuando exista y validar columnas requeridas.
RF-9: El sistema debe calcular posiciones netas y precio medio ponderado para tickers con neto positivo.
RF-10: El sistema debe ajustar la fecha de inicio del backtest usando el primer movimiento de cartera.

### 4.4 Ejecucion de estrategias
RF-11: El sistema debe ejecutar estrategias individuales: Tendencia, Bollinger, RSI, MACD.
RF-12: El sistema debe ejecutar una estrategia combinada con pesos configurables.
RF-13: El sistema debe aplicar costes de transaccion, delay de ejecucion y slippage configurables.

### 4.5 Metricacion
RF-14: El sistema debe calcular metricas de rendimiento (CAGR, volatilidad, Sharpe, Sortino, Calmar).
RF-15: El sistema debe calcular max drawdown, Ulcer Index, VaR y CVaR.
RF-16: El sistema debe calcular estadisticas de trades (win rate, profit factor, expectancy).
RF-17: El sistema debe registrar fechas de ultima entrada y salida por estrategia.

### 4.6 Analisis avanzado
RF-18: El sistema debe ejecutar walk-forward con parametros configurables de entrenamiento y test.
RF-19: El sistema debe generar analisis de sensibilidad por rejillas de parametros.
RF-20: El sistema debe ejecutar stress tests con escenarios de costes y bootstrap.

### 4.7 Reporting
RF-21: El sistema debe generar informes PDF individuales y agregados.
RF-22: El sistema debe generar dashboards tecnicos y reportes de cambios de estado.
RF-23: El sistema debe generar un informe de ganadores por ticker.
RF-24: El sistema debe generar heatmaps sectoriales y graficos 3D cuando aplique.
RF-25: El sistema debe consolidar y guardar journals en CSV cuando aplique.
RF-26: El sistema debe cargar una configuracion externa (JSON/YAML) cuando exista y aplicar los parametros definidos.
RF-27: El sistema debe soportar modo batch sin prompts interactivos, controlado por configuracion y/o flags de ejecucion.
RF-28: El sistema debe generar un reporte de calidad de datos por ticker.
RF-29: El sistema debe validar datos contra umbrales y excluir tickers que no cumplan.
RF-30: El sistema debe exportar resultados estructurados en JSON y Parquet.
RF-31: El sistema debe exportar trazabilidad de senales por ticker/estrategia.
RF-32: El sistema debe generar un snapshot de ejecucion para reproducibilidad.
RF-33: El sistema debe generar un resumen de errores y continuar el procesamiento.
RF-34: El sistema debe permitir multiples benchmarks configurables.

## 5. Requisitos no funcionales
RNF-1: El sistema debe finalizar la ejecucion sin bloquearse en ausencia de archivos opcionales.
RNF-2: El sistema debe ser tolerante a datos faltantes o inconsistentes de la fuente externa.
RNF-3: Los reportes deben generarse con codificacion compatible con Excel (UTF-8 con BOM cuando se requiera).
RNF-4: El rendimiento debe ser configurable desactivando analisis avanzados.
RNF-5: Las salidas por consola deben incluir mensajes de progreso y avisos de datos anomales.

## 6. Criterios de aceptacion
CA-1: Con un conjunto de tickers valido, el sistema genera al menos un PDF de resultados y un reporte de estado.
CA-2: Con `cartera.csv` valido, el sistema integra tickers de cartera y ajusta la fecha de inicio.
CA-3: La ausencia de `cartera.csv` e `ibex_constituents_history.csv` no detiene la ejecucion.
CA-4: El sistema calcula y muestra metricas clave para estrategia combinada y mercado.
CA-5: El sistema registra eventos recientes de entradas/salidas por estrategia.

## 7. Trazabilidad (requisitos -> modulos/funciones)
- RF-1..RF-4: `obtener_datos_historicos`, bloque principal (definicion de fechas y tickers).
- RF-5..RF-7: `obtener_datos_historicos` (motor de saneamiento y `daily_return`).
- RF-8..RF-10: `cargar_cartera`, bloque principal (ajuste de `FECHA_INICIO`).
- RF-11..RF-13: pipeline de estrategias y combinada en `ejecutar_analisis_completo_individual` / `ejecutar_analisis_completo_agregado`.
- RF-14..RF-17: `calcular_metricas`, `calcular_metricas_trades`.
- RF-18..RF-20: `generar_informe_walk_forward`, `generar_sensibilidad_parametros`, `generar_stress_tests`.
- RF-21..RF-25: `crear_informe_pdf`, `generar_pdf_*`, `generar_grafico_3d_activos`, `generar_heatmap_sectores`, `consolidar_journal_y_alertas`.
- RF-26..RF-27: `cargar_configuracion`, `_parse_cli_flags`, bloque principal (seleccion de fecha y batch mode).
- RF-28..RF-29: `generar_reporte_calidad_datos`, `validar_datos`.
- RF-30: export en `app.py` (JSON/Parquet).
- RF-31: `signal_trace` y `_append_signal_records`.
- RF-32: `RUN_SNAPSHOT_*.json` en `app.py`.
- RF-33: `error_summary` en `app.py`.
- RF-34: `benchmarks` en `app.py`.

## 8. Plan de pruebas (minimo)
- PT-1 (Datos): Ejecutar con 1 ticker valido y verificar `daily_return` no vacio.
- PT-2 (Cartera): Proveer `cartera.csv` valido y comprobar inclusion de tickers y ajuste de `FECHA_INICIO`.
- PT-3 (Robustez): Ejecutar sin `cartera.csv` ni `ibex_constituents_history.csv`; el script debe finalizar sin excepcion.
- PT-4 (Estrategias): Verificar que se calculan metricas para Tendencia, Bollinger, RSI, MACD y Combinada.
- PT-5 (Reportes): Verificar generacion de PDF(s) y PNG(s) esperados.
- PT-6 (Avanzado): Activar/desactivar `ENABLE_*` y comprobar tiempos/artefactos.

## 9. Diagrama de flujo (texto)
1) Cargar historial IBEX -> construir tickers -> cargar cartera.
2) Calcular fechas (inicio/fin) y parametros.
3) Descargar y sanear datos historicos.
4) Loop por ticker: ejecutar estrategias, metricas, estados y eventos.
5) Analisis avanzado opcional (walk-forward, sensibilidad, stress).
6) Generar reportes y dashboards.

## 10. Restricciones y riesgos
- Dependencia de la disponibilidad y calidad de Yahoo Finance.
- Heuristica de splits huerfanos puede producir falsos positivos.
- Analisis avanzado puede incrementar tiempos de ejecucion en universos grandes.

## 11. Parametros configurables (resumen)
- Fechas: `FECHA_INICIO_SISTEMA`, `FECHA_FIN`.
- Costes/ejecucion: `COSTES_TRANSACCION`, `EXECUTION_DELAY`, `SLIPPAGE_BPS`, `SLIPPAGE_ATR_MULT`, `SLIPPAGE_VOL_MULT`.
- Estrategias: parametros de Tendencia, Bollinger, RSI, MACD.
- Pesos combinados: `PESOS_ESTRATEGIAS`.
- Analisis avanzado: `ENABLE_WALK_FORWARD`, `ENABLE_SENSITIVITY`, `ENABLE_STRESS_TESTS`, `MAX_TICKERS_AVANZADO`.
- Configuracion externa: `config.json`/`config.yaml` y variable `CONFIG_PATH`.
- Flags CLI: `--config`, `--batch`, `--interactive`.
- Validacion datos: `data_validation.*`.
- Calidad datos: `data_quality_report`.
- Export resultados: `export_results.*`.
- Trazabilidad: `signal_trace.*`.
- Reproducibilidad: `reproducibilidad.*`.
- Benchmarks: `benchmarks`.

## 12. Ubicacion
- `Prueba/EstrategiaCombinadaRSI.py`

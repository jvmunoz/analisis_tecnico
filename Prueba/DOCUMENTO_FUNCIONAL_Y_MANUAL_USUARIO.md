# Documento funcional y manual de usuario

Proyecto: `EstrategiaCombinadaRSI`  
Ruta principal: `Prueba/EstrategiaCombinadaRSI.py`  
Fecha del documento: 2026-05-24  
Tipo de aplicacion: sistema local de analisis tecnico, backtesting, seguimiento de senales y generacion de informes.

## 1. Proposito del documento

Este documento describe funcionalmente la aplicacion y sirve como referencia de uso para explotarla de manera eficiente y efectiva. Esta pensado para dos perfiles:

- Usuario operativo: quiere ejecutar la aplicacion, leer los informes y tomar decisiones de seguimiento.
- Usuario avanzado: quiere entender reglas, configuracion, salidas, trazabilidad y limites del sistema.

El documento no es una recomendacion de inversion. La aplicacion produce analisis cuantitativo basado en historicos y reglas tecnicas; no garantiza resultados futuros.

## 2. Resumen ejecutivo

`EstrategiaCombinadaRSI` es una aplicacion Python que analiza activos financieros, principalmente valores del IBEX y activos incluidos en una cartera personal. El sistema descarga datos diarios, calcula estrategias tecnicas, compara rendimiento contra mercado, genera informes PDF/HTML/CSV/JSON/Parquet y mantiene journals historicos de oportunidades y eventos.

La aplicacion combina dos capas:

- Capa cuantitativa historica: backtesting de estrategias de Tendencia, Bollinger, RSI, MACD y una estrategia combinada ponderada.
- Capa operativa enriquecida: clasificacion semaforica, setups Pullback/Breakout, soportes y resistencias, entrada, stop, T1/T2, seguimiento de operaciones y eventos.

El flujo esta disenado para trabajar con sesiones cerradas. Si se solicita hoy como fecha fin, el sistema recorta los datos a la ultima sesion cerrada para evitar usar velas incompletas.

## 3. Objetivos funcionales

La aplicacion cubre estos objetivos:

1. Analizar un universo de activos con datos historicos diarios.
2. Calcular indicadores tecnicos y senales por estrategia.
3. Medir rentabilidad, riesgo, drawdown y estadisticas de trades.
4. Comparar estrategias por activo y contra benchmark.
5. Generar informes visuales y tabulares.
6. Identificar oportunidades de tipo Pullback y Breakout.
7. Gestionar un journal de operaciones potenciales y sus eventos.
8. Relacionar stops con soportes y objetivos T1/T2 con resistencias.
9. Evaluar robustez mediante walk-forward, sensibilidad de parametros y stress tests.
10. Integrar una cartera personal para seguimiento de posiciones reales.
11. Exportar resultados estructurados para analisis externo.

## 4. Arquitectura funcional

La entrada principal es:

```text
Prueba/EstrategiaCombinadaRSI.py
```

Este archivo solo invoca:

```python
from estrategia.app import main
```

La logica esta modularizada en `Prueba/estrategia/`.

### 4.1 Modulos principales

| Modulo | Responsabilidad |
|---|---|
| `app.py` | Orquestacion completa del run: configuracion, datos, analisis, informes y exportes. |
| `config_runtime.py` | Carga de `config.json`, flags CLI, defaults, watchdog y limites de runtime. |
| `data.py` | Descarga con `yfinance`, cache local, saneamiento de datos, calidad y validacion. |
| `ibex.py` | Universo IBEX, historial de componentes y filtrado por pertenencia historica. |
| `strategies.py` | Estrategias base: Tendencia, Bollinger, RSI, MACD y combinada. |
| `metrics.py` | Metricas de rendimiento, riesgo, trades, slippage y bootstrap. |
| `analysis.py` | Walk-forward, optimizacion por grid, sensibilidad y stress tests. |
| `enriched.py` | Analisis enriquecido: semaforo, Pullback/Breakout, entrada, stop, T1/T2. |
| `levels.py` | Soportes, resistencias, distancias y ajuste mixto de objetivos. |
| `portfolio.py` | Lectura de cartera, journal de operaciones y journal de eventos. |
| `reports_matplotlib.py` | Informes PDF/HTML basados en Matplotlib/Plotly. |
| `reports_reportlab.py` | Informes PDF tabulares con ReportLab. |
| `utils.py` | Helpers de conclusiones, heatmaps y utilidades. |

## 5. Entradas del sistema

## 5.1 `config.json`

Archivo principal de configuracion.

Ruta:

```text
Prueba/config.json
```

Contiene:

- Fechas de analisis.
- Parametros de estrategias.
- Pesos de la estrategia combinada.
- Costes, slippage y delay de ejecucion.
- Configuracion de cache.
- Exportaciones.
- Validacion de datos.
- Analisis avanzado.
- Reproducibilidad.
- Benchmarks.

Ejemplo de claves relevantes:

```json
{
  "batch_mode": true,
  "fecha_inicio_sistema": "2020-01-01",
  "fecha_fin": "hoy",
  "ask_end_date": true,
  "benchmarks": ["^IBEX"],
  "costes_transaccion": 0.001,
  "execution_delay": 1
}
```

## 5.2 `cartera.csv`

Archivo de movimientos de cartera.

Ruta habitual:

```text
Prueba/cartera.csv
```

Columnas requeridas:

| Columna | Significado |
|---|---|
| `Ticker` | Codigo del activo. Ejemplo: `IBE.MC`. |
| `Tipo` | Movimiento: `COMPRA` o `VENTA`. |
| `Cantidad` | Numero de acciones o unidades. |
| `Precio` | Precio de ejecucion del movimiento. |
| `Fecha` | Fecha del movimiento. |

El sistema calcula posiciones netas, precio medio y, si hay datos suficientes, P&L y dividendos.

## 5.3 Universo de tickers

El universo se construye a partir de:

- Historial IBEX si esta disponible.
- Lista de respaldo de componentes IBEX.
- Tickers presentes en la cartera.
- Benchmarks configurados, por defecto `^IBEX`.

## 5.4 Datos de mercado

La fuente actual es `yfinance`.

El sistema descarga:

- OHLC diario.
- Volumen.
- Dividendos si estan disponibles.
- Splits si estan disponibles.

Los datos se guardan en cache local:

```text
Prueba/cache/market_data/
```

La cache puede ser Parquet o CSV, segun disponibilidad de dependencias.

## 6. Flujo funcional completo

## 6.1 Inicio

Al ejecutar, el sistema:

1. Carga configuracion.
2. Inicializa runtime y watchdog.
3. Fija semilla de reproducibilidad si esta habilitada.
4. Carga universo de tickers.
5. Carga cartera personal.
6. Calcula `FECHA_INICIO`.
7. Solicita o determina `FECHA_FIN`.
8. Crea carpeta de salida.
9. Activa log de ejecucion.

## 6.2 Fecha fin y sesiones cerradas

La aplicacion evita usar la sesion en curso. Si el usuario pide hoy, `data.py` recorta a ayer o a la ultima fecha cerrada disponible.

Motivo:

- La vela diaria intradia no esta cerrada.
- Indicadores como RSI, MACD, ATR, soportes y resistencias podrian cambiar.
- El journal podria abrir operaciones con informacion provisional.

## 6.3 Descarga y saneamiento de datos

La funcion `obtener_datos_historicos`:

1. Lee cache local si esta habilitada.
2. Descarga incrementos pendientes.
3. Une cache, backfill e incrementos.
4. Elimina duplicados por fecha.
5. Ajusta precios usando `Adj Close` si aplica.
6. Rellena dividendos ausentes con 0.
7. Detecta posibles splits no ajustados con caidas masivas estables.
8. Calcula `daily_return`.
9. Exporta informes de calidad y omitidos si procede.

## 6.4 Validacion de datos

Si `data_validation.enabled` esta activo, el sistema descarta tickers que incumplen criterios como:

- Menos filas que `min_rows_per_ticker`.
- Exceso de cierres ausentes.
- Exceso de volumen cero.

Salidas:

```text
DATA_QUALITY_YYYYMMDD.csv
DATA_VALIDATION_YYYYMMDD.csv
TICKERS_OMITIDOS_YYYYMMDD.csv
```

## 6.5 Analisis por ticker

Para cada activo:

1. Se ejecuta Tendencia.
2. Se ejecuta Bollinger.
3. Se ejecuta RSI.
4. Se ejecuta MACD.
5. Se construye estrategia combinada.
6. Se calculan metricas.
7. Se guardan datos para informes.
8. Se registran cambios recientes de estado.

## 6.6 Estrategias base

### Tendencia

Regla:

```text
Compra/activo si SMA corta > SMA larga.
Fuera si SMA corta <= SMA larga.
```

Parametros actuales en `config.json`:

```json
"tendencia": {"short_window": 50, "long_window": 200}
```

Uso:

- Captura tendencias amplias.
- Evita estar comprado cuando la media corta cae bajo la larga.
- Puede reaccionar tarde en giros bruscos.

### Bollinger

Regla:

```text
Entrada si close < banda inferior.
Salida si close > media central.
```

Parametros:

```json
"bollinger": {"window": 30, "num_std_dev": 2}
```

Uso:

- Estrategia de reversion a la media.
- Busca compras tras desviaciones bajistas.
- Riesgo: una caida fuerte puede seguir cayendo.

### RSI

Regla:

```text
Entrada si RSI < umbral_compra.
Salida si RSI > umbral_salida.
```

Parametros:

```json
"rsi": {"window": 14, "umbral_compra": 30, "umbral_salida": 60}
```

Uso:

- Busca sobreventa o debilidad extrema.
- Riesgo: comprar activos estructuralmente debiles.

### MACD

Regla:

```text
Entrada si MACD cruza por encima de la linea de senal.
Salida si MACD cruza por debajo.
```

Parametros:

```json
"macd": {"fast_period": 8, "slow_period": 20, "signal_period": 9}
```

Uso:

- Captura cambios de momentum.
- Puede generar falsas senales en lateralidad.

## 6.7 Execution delay, costes y slippage

El backtest desplaza senales mediante:

```json
"execution_delay": 1
```

Esto significa que una senal generada en una sesion se ejecuta en la siguiente, reduciendo sesgos de anticipacion.

Costes:

```json
"costes_transaccion": 0.001
```

Slippage:

```json
"slippage": {
  "bps": 5.0,
  "atr_mult": 0.0,
  "vol_mult": 0.05
}
```

El coste total aplicado por cambio de posicion combina coste fijo y slippage estimado.

## 6.8 Estrategia combinada

La estrategia combinada pondera las senales de las cuatro estrategias.

Pesos actuales:

```json
"pesos_estrategias": {
  "tendencia": 0.357,
  "bollinger": 0.272,
  "rsi": 0.240,
  "macd": 0.131
}
```

La senal combinada se activa si la suma ponderada de senales es al menos `0.5`.

Interpretacion:

- No exige unanimidad.
- Da mas peso a Tendencia.
- Permite que una combinacion de estrategias active exposicion.

## 7. Analisis enriquecido

El analisis enriquecido convierte indicadores y niveles en una lectura operativa.

Campos principales:

| Campo | Significado |
|---|---|
| `Ticker` | Activo analizado. |
| `Precio` | Ultimo cierre analizado. |
| `Semaforo` | `VERDE`, `AMARILLO` o `ROJO`. |
| `Estado` | `EJECUTAR`, `VIGILAR` o `NO EJECUTAR`. |
| `Setup` | `Pullback` o `Breakout`. |
| `Score` | Puntuacion tecnica sintetica. |
| `Entrada` | Precio tecnico de entrada. |
| `Stop` | Stop inicial. |
| `T1` | Primer objetivo. |
| `T2` | Segundo objetivo. |
| `Trailing_Stop` | Stop dinamico de referencia. |
| `Soporte_20/60/120` | Soportes por ventana. |
| `Resistencia_20/60/120` | Resistencias por ventana. |
| `Dist_Soporte_*_%` | Distancia al soporte. |
| `Dist_Resistencia_*_%` | Distancia a resistencia. |

## 7.1 Pullback

Un Pullback es una oportunidad basada en retroceso hacia soporte.

La aplicacion tiende a clasificar como Pullback cuando:

```text
distancia a soporte <= 5%
o RSI <= 45
o RSI en sobreventa
```

Para que sea `VERDE`, exige:

- Cercania a soporte.
- ADX en `Trend` o `Neutral`.
- RSI bajo/moderado.
- Volumen relativo suficiente.
- Ausencia de caida reciente fuerte.
- No ruptura de soporte 20 con MACD bajista.

Entrada Pullback:

```text
Entrada = soporte estimado + 0.5 * ATR
Stop = soporte estimado - 1.0 * ATR
```

Lectura:

- Se intenta entrar cerca de una zona de apoyo.
- El stop queda bajo el soporte.
- T1/T2 buscan rebote hacia resistencias o multiplos de riesgo.

## 7.2 Breakout

Un Breakout es una oportunidad basada en ruptura o proximidad a resistencia.

La aplicacion tiende a clasificar como Breakout cuando:

- Tendencia por SMA es alcista.
- MACD es alcista.
- La resistencia esta cerca.

Para que sea `VERDE`, exige:

- Tendencia alcista.
- MACD alcista.
- ADX `Trend` o `Neutral`.
- Distancia a resistencia reducida.
- RSI no sobrecomprado.
- Volumen relativo suficiente.

Entrada Breakout:

```text
Entrada = resistencia estimada + 0.25 * ATR
Stop = resistencia estimada - 1.0 * ATR
```

Lectura:

- Se intenta comprar fuerza.
- Se evita comprar una ruptura demasiado alejada del nivel.
- El stop se situa bajo la zona rota.

## 7.3 Semaforo

### VERDE

El activo cumple filtros suficientes para considerarse operativo segun su setup.

No significa compra obligatoria. Significa:

```text
Candidato valido segun reglas tecnicas actuales.
```

### AMARILLO

El activo tiene elementos interesantes pero no cumple todos los requisitos.

Uso:

- Vigilancia.
- Esperar mejor precio, confirmacion o mejora de momentum.

### ROJO

El activo presenta deterioro tecnico.

Regla principal:

```text
SMA bajista y MACD bajista.
```

Uso:

- No ejecutar nuevas operaciones.
- Revisar salidas si hay posicion abierta.

## 7.4 Filtro de apertura por precio escapado

El journal aplica un filtro adicional antes de abrir nuevas operaciones:

```text
No abrir si Precio actual esta mas de 1.5% por encima de Precio_Entrada.
```

Motivo:

- Evitar abrir una oportunidad cuando el precio ya se ha alejado demasiado del punto tecnico previsto.
- Mantener coherencia riesgo/beneficio.
- Reducir compras tardias en Pullbacks que ya han rebotado demasiado.

Este filtro afecta al journal de nuevas operaciones, no necesariamente al semaforo tecnico del informe.

## 7.5 Soportes y resistencias

El sistema calcula soportes y resistencias en ventanas:

```text
20 sesiones
60 sesiones
120 sesiones
```

Soporte:

```text
Minimo de low en la ventana.
```

Resistencia:

```text
Maximo de high en la ventana.
```

Distancia a soporte:

```text
(Precio / Soporte - 1) * 100
```

Distancia a resistencia:

```text
(Resistencia / Precio - 1) * 100
```

Uso:

- 20 sesiones: referencia corta.
- 60 sesiones: referencia base del setup.
- 120 sesiones: referencia estructural.

## 7.6 Relacion entre Stop y soporte

En Pullback, el stop se relaciona directamente con el soporte:

```text
Stop = soporte estimado - 1 ATR
```

Esto significa que si el precio pierde con claridad la zona de soporte, la idea de rebote deja de ser valida.

En Breakout, el stop se coloca bajo la resistencia estimada:

```text
Stop = resistencia estimada - 1 ATR
```

La idea es que una ruptura valida no deberia perder rapidamente la zona rota.

## 7.7 Relacion entre T1/T2 y resistencias

El sistema usa un modelo mixto:

1. Calcula objetivos por riesgo:

```text
R = Entrada - Stop
T1_riesgo = Entrada + 1R
T2_riesgo = Entrada + 2R
```

2. Busca resistencias relevantes de 20/60/120 sesiones.
3. Si una resistencia encaja dentro de un rango razonable de multiplos de riesgo, ajusta T1 o T2 a esa resistencia.

Rangos:

- T1 puede ajustarse a resistencia entre `0.7R` y `1.5R`.
- T2 puede ajustarse a resistencia entre `1.3R` y `2.8R`.

Metodos:

- `Riesgo`: objetivo por multiplo de riesgo.
- `Resistencia`: objetivo ajustado a resistencia.

## 8. Journal de operaciones

El journal conserva la memoria operativa.

Archivos:

```text
journal_operaciones_hasta_YYYYMMDD.csv
journal_eventos_hasta_YYYYMMDD.csv
```

## 8.1 `journal_operaciones_hasta_*.csv`

Una fila por operacion consolidada.

Columnas principales:

| Campo | Significado |
|---|---|
| `Fecha_Deteccion` | Dia en que se detecto la senal. |
| `Fecha_Actualizacion` | Ultimo dia en que se actualizo el estado. |
| `Fecha_Cierre` | Dia de cierre si se cerro. |
| `Ticker` | Activo. |
| `Setup` | Pullback/Breakout. |
| `Precio_Entrada` | Entrada tecnica. |
| `Stop_Inicial` | Stop inicial. |
| `T1` | Primer objetivo. |
| `T2` | Segundo objetivo. |
| `Estado_Actual` | Estado consolidado. |
| `Tipo` | Lectura visual del estado. |
| `Icono` | Icono del estado. |
| `Precio_Ultimo` | Ultimo precio usado. |
| `P&L_%` | Evolucion porcentual contra Precio_Entrada. |

Estados:

- `ABIERTA`.
- `VIGILANCIA (T1)`.
- `VIGILANCIA (T2)`.
- `CERRADA (STOP)`.
- `CERRADA (TARGET)`.
- `CERRADA (DETERIORO)`.

## 8.2 `journal_eventos_hasta_*.csv`

Una fila por evento de cambio de estado.

Columnas:

| Campo | Significado |
|---|---|
| `Fecha_Evento` | Dia del evento. |
| `Fecha_Deteccion` | Fecha original de la operacion. |
| `Ticker` | Activo. |
| `Setup` | Pullback/Breakout. |
| `Estado_Previo` | Estado antes del evento. |
| `Estado_Nuevo` | Estado tras el evento. |
| `Tipo_Evento` | `APERTURA`, `ALERTA`, `REACTIVACION`, `CIERRE`. |
| `Motivo` | Explicacion del cambio. |
| `Precio_Entrada` | Entrada tecnica original. |
| `Stop_Inicial` | Stop original. |
| `T1` | Objetivo 1. |
| `T2` | Objetivo 2. |
| `Precio` | Precio del evento. |
| `P&L_%` | Variacion contra entrada. |

Orden:

- El CSV se muestra con eventos mas recientes arriba.
- Para leer la secuencia cronologica de una misma fecha, puede ser natural leer de abajo hacia arriba.

## 8.3 Calculo de `P&L_%`

Formula:

```text
P&L_% = (Precio / Precio_Entrada - 1) * 100
```

En una fila de apertura puede aparecer `0.0` porque representa la creacion formal de la oportunidad. En eventos posteriores refleja la evolucion frente a la entrada tecnica.

## 9. Informes generados

Cada ejecucion crea una carpeta:

```text
Prueba/runs/YYYYMMDD/
```

Dentro se generan artefactos.

## 9.1 Informes de datos

| Archivo | Uso |
|---|---|
| `DATA_QUALITY_YYYYMMDD.csv` | Calidad de datos por ticker. |
| `DATA_VALIDATION_YYYYMMDD.csv` | Resultado de filtros KEEP/DROP. |
| `TICKERS_OMITIDOS_YYYYMMDD.csv` | Tickers sin datos o fuera de ventana. |

## 9.2 Informes de estrategia

| Archivo | Uso |
|---|---|
| `INFORME_INDIVIDUAL_YYYYMMDD.pdf` | Graficos y metricas por activo. |
| `INFORME_AGREGADO_YYYYMMDD.pdf` | Vision agregada de cartera/universo. |
| `INFORME_DETALLADO_METRICAS_YYYYMMDD.pdf` | Metricas detalladas y estados por ticker. |
| `INFORME_RESUMEN_GANADORES_YYYYMMDD.pdf` | Mejor estrategia por ticker segun Sharpe. |
| `INFORME_CAMBIOS_ESTADO_YYYYMMDD.pdf` | Cambios recientes de entrada/salida. |

## 9.3 Informes enriquecidos

| Archivo | Uso |
|---|---|
| `Analisis_tecnico_tabla_completa_enriquecido_YYYYMMDD.pdf` | Tabla completa de semaforos, setups, niveles, stops y objetivos. |
| `Asignacion_por_riesgo_enriquecido_YYYYMMDD.pdf` | Propuesta de asignacion por riesgo. |
| `heatmap_sectores.png` | Mapa sectorial de estado tecnico. |
| `INFORME_MI_CARTERA_YYYYMMDD.pdf` | Estado de cartera personal. |

## 9.4 Dashboard tecnico

| Archivo | Uso |
|---|---|
| `DASHBOARD_INDICADORES_TECNICOS_YYYYMMDD.pdf` | Vista operativa de indicadores. |
| `dashboard_data_YYYYMMDD.csv` | Dataset base para Excel/BI/analisis externo. |

Incluye soportes y resistencias:

```text
S20, R20, %S20, %R20
S60, R60, %S60, %R60
S120, R120, %S120, %R120
```

## 9.5 Analisis avanzado

| Archivo | Uso |
|---|---|
| `WALK_FORWARD_OOS_YYYYMMDD.csv` | Resultados fuera de muestra por split. |
| `WALK_FORWARD_RESUMEN_YYYYMMDD.csv` | Resumen walk-forward por ticker. |
| `INFORME_SENSIBILIDAD_YYYYMMDD.pdf` | Sensibilidad de parametros. |
| `STRESS_COSTES_YYYYMMDD.csv` | Escenarios de costes. |
| `STRESS_BOOTSTRAP_YYYYMMDD.csv` | Bootstrap de retornos. |

## 9.6 Exportes de integracion

| Archivo | Uso |
|---|---|
| `RESULTADOS_YYYYMMDD.json` | Datos completos para integracion. |
| `RESULTADOS_YYYYMMDD.parquet` | Metricas tabulares. |
| `RESULTADOS_VIZ_YYYYMMDD.parquet` | Series por ticker. |
| `SENIALES_YYYYMMDD.csv` | Trazas de senales por estrategia. |
| `ERROR_RESUMEN_YYYYMMDD.csv/json` | Errores del run. |
| `RUN_SNAPSHOT_YYYYMMDD.json` | Configuracion y universo del run. |
| `RUN_SUMMARY_YYYYMMDD.json` | Resumen operativo del run. |
| `ARTIFACTS_INDEX_YYYYMMDD.json` | Inventario de artefactos. |
| `runs/latest_run.json` | Ultimo run conocido. |

## 10. Metricas principales

| Metrica | Interpretacion |
|---|---|
| `Retorno Total` | Rentabilidad acumulada del periodo. |
| `CAGR` | Crecimiento anual compuesto. |
| `Volatilidad` | Desviacion anualizada de retornos. |
| `Ratio de Sharpe` | Rentabilidad ajustada por volatilidad. |
| `Maximo Drawdown` | Peor caida desde maximo previo. |
| `Sortino` | Rentabilidad frente a volatilidad bajista. |
| `Calmar` | CAGR dividido por drawdown maximo. |
| `Ulcer Index` | Severidad de drawdowns. |
| `VaR 95` | Perdida diaria historica en percentil 5%. |
| `CVaR 95` | Media de perdidas en la cola peor. |
| `Duracion Drawdown` | Maximo tiempo en drawdown. |
| `Trades` | Numero de operaciones. |
| `Win Rate` | Porcentaje de trades ganadores. |
| `Profit Factor` | Ganancias brutas / perdidas brutas. |
| `Expectancy` | Retorno medio por trade. |
| `Time in Market` | Porcentaje del tiempo con posicion activa. |

## 11. Configuracion funcional detallada

## 11.1 Fecha y modo

| Clave | Uso |
|---|---|
| `batch_mode` | Modo no interactivo general. |
| `fecha_inicio_sistema` | Inicio minimo del historico. |
| `fecha_fin` | Fecha final deseada. |
| `ask_end_date` | Si `true`, pregunta fecha fin al usuario. |

## 11.2 Datos

| Clave | Uso |
|---|---|
| `data_quality_report` | Activa informe de calidad. |
| `data_validation.enabled` | Activa filtro de calidad. |
| `data_validation.min_rows_per_ticker` | Minimo historico exigido. |
| `data_validation.max_missing_close_pct` | Maximo de cierres ausentes. |
| `data_validation.max_zero_volume_pct` | Maximo volumen cero. |

## 11.3 Cache

| Clave | Uso |
|---|---|
| `data_cache.enabled` | Usa cache local. |
| `data_cache.force_refresh` | Fuerza descarga completa. |
| `data_cache.clear_on_start` | Limpia cache al inicio. |
| `data_cache.max_age_days` | Caducidad de cache. |
| `data_cache.max_tickers_per_run` | Limita tickers. |
| `data_cache.exclude_tickers` | Excluye tickers. |

## 11.4 Estrategias

| Clave | Uso |
|---|---|
| `params.tendencia` | Ventanas SMA. |
| `params.bollinger` | Ventana y desviaciones. |
| `params.rsi` | Ventana y umbrales. |
| `params.macd` | Periodos MACD. |
| `pesos_estrategias` | Pesos de combinada. |

## 11.5 Costes

| Clave | Uso |
|---|---|
| `costes_transaccion` | Coste por cambio de posicion. |
| `execution_delay` | Sesiones de retraso para ejecutar senales. |
| `slippage.bps` | Slippage base. |
| `slippage.atr_mult` | Slippage ligado a ATR. |
| `slippage.vol_mult` | Slippage ligado a volumen/volatilidad. |

## 11.6 Analisis avanzado

| Clave | Uso |
|---|---|
| `enable_walk_forward` | Activa walk-forward. |
| `enable_sensitivity` | Activa sensibilidad. |
| `enable_stress_tests` | Activa stress tests. |
| `solo_cartera` | Limita avanzado a cartera. |
| `max_tickers` | Limita tickers avanzados. |
| `walk_forward.train_years` | Anios train. |
| `walk_forward.test_years` | Anios test. |
| `walk_forward.step_years` | Paso entre splits. |
| `bootstrap.iters` | Iteraciones bootstrap. |

## 12. Apendice: manual de usuario

## 12.1 Requisitos

- Windows con PowerShell.
- Python 3.13 o superior.
- Dependencias instaladas: `pandas`, `numpy`, `yfinance`, `matplotlib`, `plotly`, `scipy`, `reportlab`, `pytest`.
- Opcional: `pyarrow` para Parquet.

## 12.2 Ejecucion rapida

Desde:

```powershell
cd C:\dev\opencode\Prueba
```

Ejecutar en modo batch:

```powershell
python EstrategiaCombinadaRSI.py --batch
```

Ejecutar en modo interactivo:

```powershell
python EstrategiaCombinadaRSI.py --interactive
```

Ejecutar con configuracion especifica:

```powershell
python EstrategiaCombinadaRSI.py --config config.json --batch
```

## 12.3 Rutina diaria recomendada

1. Asegurarse de que `config.json` apunta a la configuracion deseada.
2. Actualizar `cartera.csv` si hubo compras o ventas.
3. Ejecutar la aplicacion.
4. Abrir la carpeta `Prueba/runs/YYYYMMDD`.
5. Revisar `run.log`.
6. Revisar `DATA_VALIDATION_YYYYMMDD.csv`.
7. Revisar `journal_eventos_hasta_YYYYMMDD.csv`.
8. Revisar `journal_operaciones_hasta_YYYYMMDD.csv`.
9. Revisar `Analisis_tecnico_tabla_completa_enriquecido_YYYYMMDD.pdf`.
10. Revisar `DASHBOARD_INDICADORES_TECNICOS_YYYYMMDD.pdf`.
11. Revisar `INFORME_MI_CARTERA_YYYYMMDD.pdf` si se usa cartera.

## 12.4 Rutina semanal recomendada

1. Revisar `WALK_FORWARD_RESUMEN_YYYYMMDD.csv`.
2. Revisar `INFORME_SENSIBILIDAD_YYYYMMDD.pdf`.
3. Revisar `STRESS_COSTES_YYYYMMDD.csv`.
4. Revisar `STRESS_BOOTSTRAP_YYYYMMDD.csv`.
5. Detectar parametros inestables.
6. Evitar cambiar reglas por una sola sesion.

## 12.5 Como leer una oportunidad

Para cada candidato:

1. Revisar `Semaforo`.
2. Revisar `Setup`.
3. Revisar `Precio`.
4. Revisar `Entrada`.
5. Revisar diferencia entre `Precio` y `Entrada`.
6. Confirmar que no supera el limite de 1.5% sobre entrada.
7. Revisar `Stop`.
8. Revisar T1/T2.
9. Revisar soportes/resistencias 20/60/120.
10. Revisar `journal_eventos` para ver si la operacion ya venia de antes.

## 12.6 Como leer `journal_eventos`

Preguntas utiles:

- Que acaba de abrirse?
- Que ha pasado a vigilancia?
- Que ha cerrado por stop?
- Que ha cerrado por target?
- Que ha cerrado por deterioro?
- Hay reactivaciones?
- El mismo ticker tiene varias operaciones de fechas distintas?

Interpretacion de eventos:

| Tipo | Lectura |
|---|---|
| `APERTURA` | Nueva senal verde registrada. |
| `ALERTA` | Se acerca a T1 o T2. |
| `REACTIVACION` | Sale de vigilancia y vuelve a abierta. |
| `CIERRE` | Stop, target o deterioro. |

## 12.7 Como leer `journal_operaciones`

Preguntas utiles:

- Que operaciones siguen abiertas?
- Cuales estan en vigilancia?
- Cuales estan cerradas?
- Cual es el P&L contra entrada tecnica?
- Donde esta el stop?
- Donde estan T1/T2?

Estados operativos:

- `ABIERTA`: oportunidad viva sin alerta actual.
- `VIGILANCIA (T1)`: precio cerca del primer objetivo.
- `VIGILANCIA (T2)`: precio cerca del segundo objetivo.
- `CERRADA (STOP)`: precio llego al stop.
- `CERRADA (TARGET)`: precio llego a T2.
- `CERRADA (DETERIORO)`: semaforo paso a rojo.

## 12.8 Como usar informes sin duplicar esfuerzo

Lectura minima diaria:

1. `journal_eventos`.
2. `journal_operaciones`.
3. `Analisis_tecnico_tabla_completa_enriquecido`.
4. `INFORME_MI_CARTERA`.

Lectura de diagnostico:

1. `DASHBOARD_INDICADORES_TECNICOS`.
2. `INFORME_DETALLADO_METRICAS`.
3. `INFORME_INDIVIDUAL`.

Lectura de robustez:

1. `WALK_FORWARD_RESUMEN`.
2. `INFORME_SENSIBILIDAD`.
3. `STRESS_*`.

## 12.9 Como actuar ante senales frecuentes

### Nueva `APERTURA`

Comprobar:

- Precio actual frente a entrada.
- Distancia a stop.
- Ratio potencial T1/T2.
- Soportes/resistencias cercanos.
- Si ya habia una operacion antigua del mismo ticker.

### `VIGILANCIA (T1)`

Comprobar:

- Si el precio esta muy cerca de T1.
- Si conviene tomar beneficio parcial.
- Si hay resistencia cercana.
- Si el momentum sigue favorable.

### `VIGILANCIA (T2)`

Comprobar:

- Si el objetivo final esta cerca.
- Si el precio esta extendido.
- Si conviene cerrar o ajustar trailing stop.

### `CERRADA (STOP)`

Comprobar:

- Si la perdida es coherente con el riesgo previsto.
- Si hubo gap o deterioro brusco.
- Si otras operaciones similares estan amenazadas.

### `CERRADA (TARGET)`

Comprobar:

- Si la operacion cumplio objetivo.
- Si hay nuevas oportunidades o conviene esperar.

### `CERRADA (DETERIORO)`

Comprobar:

- Si el semaforo rojo se debe a tendencia, MACD o ruptura.
- Si hay impacto en cartera real.

## 12.10 Playbook de decision eficiente

Para cada candidato verde:

1. Si `Precio > Entrada * 1.015`, descartar apertura nueva.
2. Si `Stop` esta demasiado cerca para la volatilidad del activo, vigilar.
3. Si T1 esta demasiado cerca y T2 no compensa, vigilar.
4. Si el activo esta en resistencia fuerte, revisar breakout/falsa ruptura.
5. Si hay caida reciente fuerte, revisar riesgo de deterioro.
6. Si el activo ya esta en cartera, priorizar gestion de posicion existente.
7. Si hay varios candidatos del mismo sector, controlar concentracion.

## 12.11 Buenas practicas

- No ejecutar sobre datos intradia como si fueran cierre oficial.
- No cambiar parametros por una sola senal mala.
- Guardar cada run en su carpeta y conservar `RUN_SNAPSHOT`.
- Revisar errores antes de leer informes.
- Usar `journal_eventos` para novedades y `journal_operaciones` para estado.
- Leer soportes/resistencias junto con stop y T1/T2.
- Comparar semaforo con contexto sectorial.
- Priorizar operaciones con buen encaje precio/entrada.

## 12.12 Resolucion de problemas

### No se generan informes

Revisar:

- `run.log`.
- `ERROR_RESUMEN_YYYYMMDD.csv`.
- Dependencias instaladas.
- Permisos de escritura en `Prueba/runs`.

### Faltan tickers

Revisar:

- `TICKERS_OMITIDOS_YYYYMMDD.csv`.
- `DATA_VALIDATION_YYYYMMDD.csv`.
- Cache de datos.
- Si el ticker esta excluido por configuracion.

### La ejecucion tarda demasiado

Opciones:

- Limitar `performance.max_tickers`.
- Limitar `data_cache.max_tickers_per_run`.
- Reducir `analisis_avanzado.max_tickers`.
- Desactivar temporalmente walk-forward, sensibilidad o stress.

### Los PDF son muy grandes o muchos

Usar los CSV/Parquet para analisis rapido y reservar PDF para revision cualitativa.

### Veo operaciones duplicadas por ticker

Puede haber varias operaciones del mismo ticker y setup si fueron detectadas en fechas distintas. Revisar `Fecha_Deteccion`.

## 12.13 Checklist antes de usar resultados

- El run termino sin errores criticos.
- La fecha de datos es la esperada.
- La validacion de datos no elimino tickers importantes.
- La cartera esta actualizada.
- La senal no esta alejada mas de 1.5% de entrada.
- El stop es entendible frente al soporte/resistencia.
- T1/T2 tienen sentido frente a resistencias.
- La exposicion sectorial es razonable.

## 13. Limitaciones funcionales

- Depende de datos externos y de su calidad.
- Trabaja principalmente con cierre diario.
- El backtest es historico y no garantiza futuro.
- Las senales son reglas deterministas, no juicio discrecional.
- Las aperturas del journal son oportunidades tecnicas, no ordenes reales.
- La cartera se interpreta a partir de CSV local.
- Los informes pueden requerir tiempo si el universo y los analisis avanzados son amplios.

## 14. Glosario breve

| Termino | Significado |
|---|---|
| ATR | Rango medio verdadero, medida de volatilidad. |
| ADX | Indicador de fuerza de tendencia. |
| MACD | Indicador de momentum basado en medias exponenciales. |
| RSI | Oscilador de fuerza relativa. |
| SMA | Media movil simple. |
| Pullback | Retroceso hacia soporte. |
| Breakout | Ruptura de resistencia. |
| T1 | Primer objetivo. |
| T2 | Segundo objetivo. |
| Stop | Nivel de invalidacion de la operacion. |
| RVOL | Volumen relativo. |
| OOS | Fuera de muestra. |


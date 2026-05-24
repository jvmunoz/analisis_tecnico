# Valoracion tecnica y propuestas de mejora

Proyecto: `EstrategiaCombinadaRSI`  
Fecha del documento: 2026-05-24  
Alcance: revision tecnica de arquitectura, calidad, mantenibilidad, riesgos y evolucion.

## 1. Resumen ejecutivo

La aplicacion tiene un valor funcional alto: descarga datos, ejecuta backtests, calcula metricas, genera informes ricos, mantiene un journal operativo y permite analisis avanzado de robustez. Para un uso personal o semi-profesional, el sistema ya cubre un ciclo completo de investigacion, seguimiento y documentacion de oportunidades.

Tecnicamente, el proyecto ha evolucionado desde un script hacia una aplicacion modular. Esa evolucion es positiva, pero tambien deja algunas zonas de deuda:

- Orquestacion central extensa en `app.py`.
- Reglas de negocio distribuidas entre `enriched.py`, `levels.py` y `portfolio.py`.
- Journals persistidos en CSV con reconstruccion historica compleja.
- Configuracion potente pero aun poco tipada.
- Falta de una capa formal de dominio para operaciones, senales y eventos.
- Dependencia de ficheros como fuente de verdad.
- Ausencia de pruebas end-to-end completas de un run.

La recomendacion principal es evolucionar hacia una arquitectura mas explicita: modelos de dominio, servicios de datos, motor de senales, motor de journal, capa de informes y capa de persistencia separadas. No hace falta reescribir todo; se puede hacer incrementalmente.

## 2. Fortalezas actuales

## 2.1 Modularizacion razonable

El proyecto ya esta separado en modulos:

- Datos.
- Estrategias.
- Metricas.
- Analisis avanzado.
- Informes.
- Analisis enriquecido.
- Portfolio/journal.
- Configuracion.

Esto facilita localizar responsabilidades y reduce el riesgo de tener toda la logica en un unico script.

## 2.2 Cobertura funcional amplia

La aplicacion no se limita a generar senales. Incluye:

- Backtesting.
- Costes y slippage.
- Metricas avanzadas.
- Walk-forward.
- Sensibilidad.
- Stress tests.
- Informes PDF.
- Exportaciones estructuradas.
- Journal consolidado.
- Cartera personal.
- Soportes/resistencias.
- Targets mixtos.

Pocos scripts personales llegan a este nivel de cobertura.

## 2.3 Uso de sesiones cerradas

El recorte de `fecha_fin` a ultima sesion cerrada es una decision tecnicamente sana.

Beneficios:

- Evita contaminacion intradia.
- Hace los runs reproducibles.
- Reduce cambios de senal por vela incompleta.
- Protege el journal de operaciones provisionales.

## 2.4 Control de reproducibilidad

El sistema genera:

- `RUN_SNAPSHOT`.
- `RUN_SUMMARY`.
- `ARTIFACTS_INDEX`.
- `run.log`.
- Semilla de reproducibilidad.

Esto es una base muy buena para auditoria y depuracion.

## 2.5 Cache de datos

La cache reduce tiempos y dependencia de red.

La descarga incremental permite evitar descargar todo el historico en cada run.

## 2.6 Analisis de calidad de datos

La presencia de:

- `DATA_QUALITY`.
- `DATA_VALIDATION`.
- `TICKERS_OMITIDOS`.
- Saneamiento de splits anomalos.

es una fortaleza importante. Muchos errores en sistemas cuantitativos vienen de datos, no de estrategia.

## 2.7 Journal de eventos

Separar:

- estado actual (`journal_operaciones`);
- cambios historicos (`journal_eventos`);

es una buena decision funcional. Permite responder tanto "que tengo vivo" como "que ha pasado".

## 2.8 Tests existentes

Hay pruebas sobre:

- Descarga/datos.
- Momentum enriquecido.
- Journal.
- Deduccion de eventos.
- Campos exportados.
- Filtros recientes.

Aunque la cobertura puede crecer, ya existe una red de seguridad.

## 3. Riesgos tecnicos principales

## 3.1 `app.py` concentra demasiada orquestacion

`app.py` coordina:

- Configuracion.
- Universo.
- Cartera.
- Descarga.
- Validacion.
- Loop por ticker.
- Benchmarks.
- Informes.
- Analisis avanzado.
- Exportaciones.
- Snapshots.

Riesgo:

- Dificulta pruebas unitarias.
- Aumenta probabilidad de regresiones.
- Complica ejecutar solo una parte del flujo.
- Hace dificil introducir UI/API en el futuro.

Mejora:

Separar en servicios:

- `RunContext`.
- `UniverseService`.
- `MarketDataService`.
- `AnalysisService`.
- `ReportService`.
- `ExportService`.
- `JournalService`.

## 3.2 Reglas de negocio dispersas

Ejemplos:

- Semaforo en `enriched.py`.
- Soportes/resistencias en `levels.py`.
- Filtros de apertura en `portfolio.py`.
- Estados y eventos en `portfolio.py`.
- Targets mixtos en `levels.py`.

Riesgo:

- Es facil cambiar una regla sin comprender su impacto.
- La documentacion puede quedar desalineada.
- Dificulta explicar por que una senal aparece o no.

Mejora:

Crear un modulo de dominio:

```text
estrategia/domain/
  signals.py
  operations.py
  levels.py
  rules.py
  events.py
```

## 3.3 Persistencia en CSV como fuente de verdad

Los CSV son transparentes y faciles de revisar, pero fragiles como base de estado.

Problemas:

- Tipos ambiguos.
- Encoding.
- Deducciones historicas complejas.
- Riesgo de edicion manual.
- Riesgo de duplicados.
- Reglas de reconstruccion no triviales.

Mejora:

Mantener CSV como export, pero usar una persistencia primaria:

- SQLite.
- DuckDB.
- Parquet particionado.

Modelo recomendado:

```text
operations
operation_events
run_snapshots
signals
market_data_quality
```

## 3.4 Identidad de operaciones

Actualmente se usa internamente:

```text
Fecha_Deteccion | Ticker | Setup
```

Ventaja:

- Simple y estable.

Riesgo:

- Si en el futuro se permite mas de una operacion del mismo ticker/setup en la misma fecha, colisionara.
- No captura version de reglas.
- No captura entrada/stop/targets.

Mejora:

Generar `Operacion_ID` estable con hash:

```text
fecha + ticker + setup + entrada + stop + version_reglas
```

Mantenerlo interno o exportarlo opcionalmente.

## 3.5 Configuracion sin esquema formal

`config.json` es potente, pero no esta validado por un esquema tipado formal.

Riesgo:

- Errores silenciosos por claves mal escritas.
- Tipos incorrectos.
- Parametros fuera de rango.

Mejora:

Usar:

- `pydantic`.
- `dataclasses` con validadores.
- JSON Schema.

Validaciones recomendadas:

- Pesos suman 1 o se normalizan explicitamente.
- Ventanas positivas.
- `short_window < long_window`.
- Umbral RSI salida > entrada.
- Costes no negativos.
- Fechas validas.
- `max_tickers` nulo o positivo.

## 3.6 Encoding y caracteres

Se observan textos con mojibake en algunos documentos y comentarios antiguos.

Riesgo:

- PDF/CSV pueden mostrar caracteres rotos.
- Tests de texto pueden ser fragiles.
- Dificulta mantenimiento.

Mejora:

- Estandarizar UTF-8.
- Revisar archivos con caracteres corruptos.
- Mantener `encoding="utf-8-sig"` solo donde Excel lo requiera.
- Documentar criterio de encoding.

## 3.7 Informes acoplados al flujo

Los informes se generan dentro del run principal.

Riesgo:

- Si falla un informe, puede afectar la percepcion del run.
- Dificulta regenerar solo informes desde resultados ya calculados.
- Repite computos.

Mejora:

Separar:

```text
compute run -> guardar dataset canonico
render reports -> leer dataset canonico
```

Esto permitiria:

- Regenerar PDF sin descargar datos.
- Probar informes con fixtures.
- Generar subconjuntos.
- Crear una UI futura.

## 3.8 Rendimiento

El sistema procesa muchos tickers y muchos informes.

Riesgos:

- Runs largos.
- Dificultad para depurar cuellos de botella.
- Generacion de PDF costosa.
- Analisis avanzado caro.

Mejoras:

- Perfilado con `cProfile` o `pyinstrument`.
- Paralelizar analisis por ticker.
- Cachear resultados intermedios por ticker/fecha/config.
- Separar modo rapido y modo completo.
- Generar informes bajo demanda.

## 3.9 Tests insuficientes para flujos completos

Hay tests utiles, pero faltan:

- End-to-end con universo pequeno.
- Golden files de journals.
- Tests de configuracion invalida.
- Tests de regeneracion de informes.
- Tests de compatibilidad de CSV antiguos.
- Tests de no contaminacion futura.

Mejora:

Crear fixtures pequenos:

```text
AAA.MC con tendencia limpia
BBB.MC con pullback
CCC.MC con breakout
DDD.MC con stop
EEE.MC con target
```

Y probar el run completo contra salidas esperadas.

## 4. Valoracion por areas

## 4.1 Datos

Valoracion: buena base, mejorable en robustez.

Fortalezas:

- Cache.
- Backfill.
- Validacion.
- Calidad.
- Ajuste de precios.
- Dividendos.

Debilidades:

- Dependencia unica de `yfinance`.
- Sin capa de proveedor abstracta.
- El calendario de mercado no esta modelado formalmente.
- Posibles diferencias entre Yahoo y datos oficiales.

Mejoras:

1. Crear interfaz `MarketDataProvider`.
2. Anadir proveedor alternativo.
3. Incorporar calendario de BME.
4. Separar datos diarios oficiales de datos intradia de monitorizacion.
5. Guardar metadatos de fuente, descarga y version.

## 4.2 Estrategias

Valoracion: clara y comprensible.

Fortalezas:

- Estrategias clasicas.
- Execution delay.
- Costes.
- Slippage.
- Combinada ponderada.

Debilidades:

- Solo posiciones long.
- Sin tamanos de posicion en backtest.
- Sin cash management.
- Sin exposicion maxima.
- Sin stops reales dentro del backtest base.

Mejoras:

1. Introducir position sizing.
2. Incluir stops/targets en backtest enriquecido.
3. Permitir exposicion maxima por sector.
4. Incorporar reglas de salida por trailing stop.
5. Medir turnover y capacidad.

## 4.3 Analisis enriquecido

Valoracion: muy util operativamente.

Fortalezas:

- Semaforo.
- Pullback/Breakout.
- Soportes/resistencias.
- T1/T2 mixtos.
- Filtros de deterioro.
- Filtro de precio escapado.

Debilidades:

- Reglas no parametrizadas en `config.json`.
- Score no esta calibrado estadisticamente.
- El semaforo y el journal pueden divergir.
- El usuario necesita explicaciones por ticker.

Mejoras:

1. Parametrizar umbrales:
   - distancia soporte.
   - distancia resistencia.
   - RSI.
   - RVOL.
   - caida reciente.
   - precio maximo sobre entrada.
2. Exportar una columna `Motivo_Semaforo`.
3. Exportar una columna `Motivo_No_Apertura`.
4. Anadir explicacion por ticker en CSV/JSON.
5. Registrar version de reglas.

## 4.4 Journal

Valoracion: funcionalmente potente, tecnicamente delicado.

Fortalezas:

- Estado y eventos separados.
- Dedupe interno.
- Orden de eventos.
- Campos de entrada, stop, T1/T2 y P&L.
- Limpieza historica posible.

Debilidades:

- Reconstruccion desde CSV historicos compleja.
- Riesgo de inconsistencias por edicion manual.
- No hay transacciones.
- No hay esquema de datos.

Mejoras:

1. Mover journal a SQLite.
2. Mantener CSV como export.
3. Crear migraciones.
4. Registrar `Rule_Version`.
5. Anadir `Motivo_No_Apertura`.
6. Anadir `Estado_Maximo_Alcanzado` separado de `Estado_Actual`.

## 4.5 Informes

Valoracion: amplios y utiles.

Fortalezas:

- Buena variedad.
- PDF para lectura humana.
- CSV/JSON/Parquet para analisis externo.
- Dashboard tecnico.
- Informes de cartera.

Debilidades:

- Muchos artefactos por run.
- Dificil saber por donde empezar.
- PDF no siempre es ideal para comparacion intensiva.
- Regenerar informes implica ejecutar bastante flujo.

Mejoras:

1. Crear indice HTML por run.
2. Crear resumen ejecutivo unico.
3. Priorizar informes por perfil de usuario.
4. Generar dashboards interactivos HTML.
5. Separar renderizado de calculo.

## 4.6 Analisis avanzado

Valoracion: buena orientacion a robustez.

Fortalezas:

- Walk-forward.
- Sensibilidad.
- Stress de costes.
- Bootstrap.

Debilidades:

- Puede ser costoso.
- El grid puede ser pequeno o arbitrario.
- No hay control fuerte de multiple testing.
- Riesgo de sobreoptimizacion.

Mejoras:

1. Reportar estabilidad de parametros.
2. Penalizar parametros inestables.
3. Comparar contra benchmark naive.
4. Guardar mejores parametros por split.
5. Incluir intervalos de confianza.

## 5. Mejoras prioritarias

## 5.1 Prioridad alta

### 1. Parametrizar reglas enriquecidas

Mover a `config.json`:

```json
"enriched_rules": {
  "max_apertura_sobre_entrada_pct": 1.5,
  "pullback_max_dist_soporte_pct": 5.0,
  "breakout_max_dist_resistencia_pct": 2.0,
  "rvol_min": 0.15,
  "rsi_pullback_max": 45,
  "caida_fuerte_5d_pct": -5.0,
  "caida_fuerte_10d_pct": -8.0
}
```

Beneficio:

- Menos cambios de codigo.
- Mas trazabilidad.
- Mayor control por usuario.

### 2. Exportar explicabilidad de senales

Anadir campos:

```text
Motivo_Semaforo
Motivo_Setup
Motivo_No_Apertura
Checks_Verdes
Checks_Fallidos
```

Beneficio:

- El usuario entiende por que hay o no hay apertura.
- Reduce analisis manual.
- Facilita auditoria.

### 3. Crear resumen ejecutivo por run

Un archivo:

```text
RESUMEN_EJECUTIVO_YYYYMMDD.md
```

Contenido:

- Fecha efectiva de datos.
- Tickers procesados.
- Errores.
- Nuevas aperturas.
- Cierres.
- Alertas T1/T2.
- Top oportunidades.
- Riesgos destacados.
- Cambios frente al run anterior.

Beneficio:

- Ruta de lectura clara.
- Menos dependencia de abrir muchos PDF.

### 4. End-to-end test pequeno

Crear dataset sintetico y probar:

- Descarga omitida.
- Analisis.
- Journal.
- Eventos.
- Filtro 1.5%.
- Export basico.

Beneficio:

- Evita regresiones en reglas delicadas.

## 5.2 Prioridad media

### 5. Persistencia estructurada para journal

Usar SQLite o DuckDB.

Tablas:

```text
runs
operations
operation_events
signals
blocked_signals
```

Beneficio:

- Consultas robustas.
- Mejor deduplicacion.
- Migraciones.
- CSV solo como salida.

### 6. Versionado de reglas

Anadir:

```text
RULE_VERSION
```

En:

- `RUN_SNAPSHOT`.
- `journal_operaciones`.
- `journal_eventos`.
- `RESULTADOS`.

Beneficio:

- Saber con que reglas se genero cada senal.
- Gestionar cambios historicos.

### 7. Regeneracion controlada de informes

Comando propuesto:

```powershell
python EstrategiaCombinadaRSI.py --render-only --run 20260522
```

Beneficio:

- No descargar datos.
- No recalcular estrategias.
- Solo rehacer PDF/CSV desde resultados.

### 8. Proveedor de datos abstracto

Interfaz:

```python
class MarketDataProvider:
    def download_daily(self, ticker, start, end): ...
```

Implementaciones:

- Yahoo/yfinance.
- CSV local.
- Proveedor premium futuro.

Beneficio:

- Menos dependencia de una fuente.
- Tests mas faciles.

## 5.3 Prioridad baja

### 9. UI ligera

Opciones:

- Streamlit.
- Panel.
- Dash.
- HTML estatico por run.

Beneficio:

- Menos dependencia de PDF.
- Filtrado interactivo.

### 10. Integracion con broker

Solo tras estabilizar reglas.

Primero como modo lectura/watchlist, no ejecucion automatica.

### 11. Monitor intradia separado

Usar datos intradia solo para:

- Precio actual.
- Distancia a entrada.
- Distancia a stop.
- Distancia a T1/T2.

No recalcular semaforo diario con intradia.

## 6. Propuesta de arquitectura objetivo

## 6.1 Capas

```text
config/
  settings.py

data/
  providers.py
  cache.py
  validation.py

domain/
  indicators.py
  strategies.py
  enriched_rules.py
  levels.py
  operations.py
  events.py

services/
  universe_service.py
  analysis_service.py
  journal_service.py
  report_service.py
  export_service.py

reports/
  pdf_reportlab.py
  pdf_matplotlib.py
  html_dashboard.py

cli/
  main.py
```

## 6.2 Flujo objetivo

```text
LoadConfig
BuildUniverse
LoadMarketData
ValidateData
ComputeIndicators
RunStrategies
ComputeMetrics
RunEnrichedRules
UpdateJournal
PersistCanonicalResults
RenderReports
ExportArtifacts
```

## 6.3 Dataset canonico

Guardar un dataset estable por run:

```text
run_metadata.json
market_data.parquet
indicators.parquet
strategy_metrics.parquet
enriched_signals.parquet
operations.parquet/sqlite
events.parquet/sqlite
```

Los informes deberian leer de estos artefactos, no recalcular.

## 7. Mejora de explicabilidad

Para cada ticker, exportar:

```text
Check_Trend_SMA
Check_MACD
Check_ADX
Check_RSI
Check_RVOL
Check_Dist_Soporte
Check_Dist_Resistencia
Check_Caida_Reciente
Check_Ruptura_Soporte
Check_Precio_Entrada
Motivo_Final
```

Ejemplo:

```text
Ticker: IBE.MC
Setup: Pullback
Semaforo: VERDE
No apertura journal: Precio actual 4.21% sobre entrada, limite 1.5%
```

Esto resolveria muchas preguntas recurrentes.

## 8. Mejora del journal

## 8.1 Campos recomendados

Anadir:

```text
Operacion_ID
Rule_Version
Run_ID
Estado_Maximo_Alcanzado
Motivo_Apertura
Motivo_Bloqueo
Precio_Apertura_Teorica
Precio_Actual_En_Apertura
Distancia_A_Entrada_%
Metodo_T1
Metodo_T2
```

## 8.2 Journal de senales bloqueadas

Crear:

```text
journal_senales_bloqueadas_hasta_YYYYMMDD.csv
```

Campos:

```text
Fecha
Ticker
Setup
Semaforo
Precio
Entrada
Distancia_Entrada_%
Motivo_Bloqueo
```

Beneficio:

- El usuario ve oportunidades descartadas.
- Permite ajustar umbrales con evidencia.

## 9. Calidad y pruebas

## 9.1 Tests recomendados

| Area | Test |
|---|---|
| Datos | Descarga simulada, cache, backfill, fechas cerradas. |
| Indicadores | RSI/MACD/ATR con fixtures conocidos. |
| Estrategias | Senales esperadas por patron sintetico. |
| Metricas | Drawdown, CAGR, Sharpe, trades. |
| Enriquecido | Pullback, Breakout, ROJO, filtro caida. |
| Levels | Soportes/resistencias 20/60/120. |
| Targets | Ajuste por resistencias. |
| Journal | Apertura, alerta, cierre, dedupe, orden. |
| Regeneracion | No contaminacion por snapshots futuros. |
| CLI | Batch, interactive simulado, config alternativa. |

## 9.2 Golden files

Crear fixtures de salida esperada:

```text
tests/golden/journal_eventos_expected.csv
tests/golden/journal_operaciones_expected.csv
```

Comparar con tolerancias para decimales.

## 10. Seguridad operativa

## 10.1 Riesgo financiero

El sistema no debe presentarse como asesor automatico. Debe mantener disclaimer:

```text
Herramienta de analisis, no recomendacion financiera.
```

## 10.2 Riesgo de datos

Debe quedar claro:

- Fuente de datos.
- Fecha efectiva.
- Si faltan tickers.
- Si hubo errores.

## 10.3 Riesgo de ejecucion

Si en el futuro hay integracion con broker:

- Modo paper primero.
- Confirmacion manual.
- Logs inmutables.
- Limites de riesgo.
- Kill switch.

## 11. Observaciones sobre mantenibilidad

## 11.1 Nombres y estilo

El proyecto usa nombres en espanol, lo cual es coherente con el usuario. Conviene mantenerlo.

Recomendacion:

- Estandarizar nombres de columnas.
- Evitar mezclar nombres con acentos en columnas criticas.
- Documentar diccionario de columnas.

## 11.2 Comentarios

Hay comentarios utiles, pero algunas reglas de negocio deberian vivir tambien en documentacion o tests.

## 11.3 Dependencias

Conviene crear:

```text
requirements.txt
pyproject.toml
```

Con versiones aproximadas.

## 11.4 Entorno

Conviene documentar:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## 12. Roadmap recomendado

## 12.1 Corto plazo

1. Parametrizar reglas enriquecidas.
2. Crear `Motivo_No_Apertura`.
3. Crear resumen ejecutivo markdown.
4. Mejorar tests end-to-end.
5. Documentar columnas del journal.

## 12.2 Medio plazo

1. Persistencia SQLite/DuckDB para journal.
2. Separar calculo y renderizado.
3. Crear proveedor de datos abstracto.
4. Crear modo `render-only`.
5. Crear dashboard HTML interactivo.

## 12.3 Largo plazo

1. UI completa.
2. Multi-proveedor de datos.
3. Optimizacion robusta con penalizacion por inestabilidad.
4. Motor de reglas versionado.
5. Monitor intradia operativo separado.

## 13. Valoracion global

| Dimension | Valoracion |
|---|---|
| Cobertura funcional | Alta |
| Utilidad operativa | Alta |
| Modularidad | Media-alta |
| Mantenibilidad | Media |
| Robustez de datos | Media-alta |
| Robustez de reglas | Media |
| Testabilidad | Media |
| Escalabilidad | Media |
| Trazabilidad | Alta en runs, media en reglas |
| Preparacion para producto | Media-baja |

Conclusion:

La aplicacion es fuerte como herramienta local avanzada de analisis tecnico y seguimiento. El mayor valor esta en la combinacion de backtesting, informes, analisis enriquecido y journal. Para evolucionarla de manera segura, el foco deberia estar en explicabilidad, parametrizacion, persistencia del journal y separacion entre calculo y renderizado.


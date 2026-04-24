# Manual De Referencia - Aplicacion De Analisis Tecnico

Version: 2026-04-24  
Proyecto: `Prueba/EstrategiaCombinadaRSI.py`

## 1. Objetivo Del Documento
Este manual sirve como referencia operativa para usuarios finales de la aplicacion. Cubre:
- Que hace el sistema.
- Como ejecutarlo.
- Que significan sus salidas.
- Como transformar esas salidas en decisiones operativas.

## 2. Que Hace La Aplicacion
La aplicacion ejecuta un flujo completo de analisis cuantitativo sobre activos (principalmente IBEX):
- Descarga datos historicos diarios.
- Calcula 4 estrategias base: Tendencia, Bollinger, RSI, MACD.
- Calcula una estrategia combinada ponderada.
- Evalua rendimiento y riesgo.
- Genera informes PDF/HTML y exportaciones CSV/JSON/Parquet.
- Genera analisis avanzados (walk-forward, sensibilidad, stress).
- Genera un flujo enriquecido de señales y seguimiento (`journal_*`).

## 3. Estructura Funcional Del Sistema
Entrada principal:
- `EstrategiaCombinadaRSI.py` -> lanza `estrategia.app.main()`.

Modulos principales:
- `estrategia/app.py`: orquestacion completa del run.
- `estrategia/config_runtime.py`: carga/saneado de configuracion y runtime.
- `estrategia/data.py`: descarga, calidad y validacion de datos.
- `estrategia/strategies.py`: calculo de señales y curvas de cada estrategia.
- `estrategia/metrics.py`: metricas de performance/riesgo.
- `estrategia/reports_matplotlib.py`: informes PDF (matplotlib) y HTML 3D.
- `estrategia/reports_reportlab.py`: informes PDF tabulares (reportlab).
- `estrategia/analysis.py`: walk-forward, sensibilidad y stress tests.
- `estrategia/enriched.py`: analisis enriquecido, perfiles y cartera/journal.
- `estrategia/portfolio.py`: lectura de cartera y consolidacion de journals.

## 4. Requisitos Previos
- Python 3.13+.
- Dependencias: `pandas`, `numpy`, `yfinance`, `matplotlib`, `plotly`, `scipy`, `reportlab`.
- Opcional para Parquet: `pyarrow`.
- Opcional para pruebas: `pytest`.

## 5. Archivos De Entrada Clave
## 5.1 `config.json`
Configura parametros de ejecucion, estrategias, exportaciones y analisis avanzado.

## 5.2 `cartera.csv`
Movimientos de cartera del usuario. Columnas requeridas:
- `Ticker`
- `Tipo` (`COMPRA` / `VENTA`)
- `Cantidad`
- `Precio`
- `Fecha`

## 5.3 Historial de componentes
El sistema puede usar historial de IBEX para filtrar periodos donde un ticker aun no cotizaba o no era elegible.

## 6. Como Ejecutar La Aplicacion
Desde `Prueba/`:

```powershell
python EstrategiaCombinadaRSI.py --interactive
```

```powershell
python EstrategiaCombinadaRSI.py --batch
```

```powershell
python EstrategiaCombinadaRSI.py --config config.json --batch
```

Comportamiento de fecha fin:
- En modo interactivo, pregunta `Fecha Fin` (por defecto: ayer).
- Si se fija `fecha_fin` en config y `ask_end_date=false`, ejecuta sin pregunta.

Carpeta de salida:
- Cada run guarda artefactos en `Prueba/runs/YYYYMMDD`.
- `YYYYMMDD` se toma de la `Fecha Fin` efectiva del run.

## 7. Flujo De Ejecucion (Paso A Paso)
1. Carga configuracion y normaliza valores (pesos, limites, etc.).
2. Prepara carpeta de salida y `run.log`.
3. Carga universo de tickers (IBEX + cartera + benchmarks).
4. Descarga historicos (`obtener_datos_historicos`).
5. Genera `DATA_QUALITY_*` y aplica `DATA_VALIDATION_*` si esta habilitado.
6. Ejecuta analisis individual por ticker.
7. Genera informes principales.
8. Ejecuta analisis enriquecido (alertas, asignacion y journal).
9. Ejecuta analisis avanzados (walk-forward, sensibilidad, stress) si estan activos.
10. Exporta resultados estructurados (`RESULTADOS_*`, señales, errores, snapshot).
11. Genera resumen de run (`RUN_SUMMARY_*`, `ARTIFACTS_INDEX_*`, `latest_run.json`).

## 8. Configuracion Relevante (Guia Rapida)
Valores por defecto actuales (runtime):
- Tendencia: `short_window=50`, `long_window=200`.
- Bollinger: `window=30`, `num_std_dev=2`.
- RSI: `window=14`, `umbral_compra=30`, `umbral_salida=60`.
- MACD: `fast=8`, `slow=20`, `signal=9`.
- Pesos combinada: `tendencia=0.357`, `bollinger=0.272`, `rsi=0.240`, `macd=0.131`.

Claves de configuracion que mas usan los usuarios:
- `ask_end_date`: prompt interactivo de fecha fin.
- `fecha_inicio_sistema`: fecha inicial de descarga.
- `benchmarks`: benchmarks (ej. `^IBEX`).
- `data_validation.enabled`: activa filtro de calidad por ticker.
- `data_validation.min_rows_per_ticker`: minimo de filas por ticker.
- `data_cache.*`: cache local de datos y refresco.
- `export_results.*`: export JSON/Parquet.
- `signal_trace.*`: export de trazas de señales.
- `error_summary.*`: export de resumen de errores.
- `analisis_avanzado.enable_walk_forward`.
- `analisis_avanzado.enable_sensitivity`.
- `analisis_avanzado.enable_stress_tests`.
- `analisis_avanzado.solo_cartera`.
- `analisis_avanzado.max_tickers`.

## 9. Catalogo De Salidas Y Como Interpretarlas
## 9.1 Validacion y calidad de datos
- `DATA_QUALITY_YYYYMMDD.csv`  
  Qué es: estadistica de datos brutos descargados.  
  Uso: detectar huecos, volumen cero, registros anómalos.

- `DATA_VALIDATION_YYYYMMDD.csv`  
  Qué es: resultado del filtro de calidad por ticker (`KEEP` / `DROP`).  
  Uso: justificar por que un ticker no participa en el analisis.

## 9.2 Informes nucleares (estrategias)
- `INFORME_INDIVIDUAL_YYYYMMDD.pdf`  
  Qué es: analisis por ticker con grafico de precio/señales, equity y tabla de metricas.  
  Uso: validar coherencia visual de señales y comportamiento historico.

- `INFORME_AGREGADO_YYYYMMDD.pdf`  
  Qué es: analisis consolidado del portafolio agregado.  
  Uso: ver riesgo/rentabilidad global del conjunto.

- `INFORME_DETALLADO_METRICAS_YYYYMMDD.pdf`  
  Qué es: ficha por ticker con 4 bloques:
  - Rendimiento acumulado.
  - Riesgo avanzado y cola.
  - Estadisticas de trades.
  - Estado actual y ultimas operaciones.
  Uso: documento principal de lectura técnica completa.

- `DASHBOARD_INDICADORES_TECNICOS_YYYYMMDD.pdf`  
  Qué es: tablero operativo con estado de indicadores de cada activo.
  Uso: priorizacion diaria de vigilancia y oportunidades.

- `dashboard_data_YYYYMMDD.csv`  
  Qué es: dataset del dashboard.
  Uso: analisis externo (Excel/BI/IA).

- `INFORME_RESUMEN_GANADORES_YYYYMMDD.pdf`  
  Qué es: estrategia “ganadora” por ticker (mejor Sharpe historico).
  Uso: mapa rapido de que estrategia domina por activo.

- `INFORME_CAMBIOS_ESTADO_YYYYMMDD.pdf`  
  Qué es: entradas/salidas recientes por ticker y estrategia.
  Uso: seguimiento de actividad de señales en ultimas fechas.

## 9.3 Informes de inversion y asignacion
- `Inversion_Estrategica_Largo_Plazo_YYYYMMDD.pdf`  
  Qué es: seleccion de activos de alta conviccion estructural.
  Uso: visión medio/largo plazo con filtros de calidad histórica.

- `INFORME_RECOMENDACION_PERFILES_YYYYMMDD.pdf`  
  Qué es: propuestas por perfil (Conservador/Neutral/Agresivo).  
  Uso: traduccion de metricas a asignaciones de capital.

- `INFORME_MI_CARTERA_YYYYMMDD.pdf`  
  Qué es: control de cartera real, P&L y dividendos.
  Uso: seguimiento patrimonial de posiciones activas.

## 9.4 Analisis enriquecido operacional
- `Analisis_tecnico_tabla_completa_enriquecido_YYYYMMDD.pdf`  
  Qué es: tabla completa con semaforo, setup, niveles y alertas de entrada/salida.

- `Asignacion_por_riesgo_enriquecido_YYYYMMDD.pdf`  
  Qué es: asignacion por riesgo con control de exposición y mapa sectorial.

- `journal_operaciones_hasta_YYYYMMDD.csv`  
  Qué es: diario consolidado de oportunidades/posiciones y estado actual.

- `journal_eventos_hasta_YYYYMMDD.csv`  
  Qué es: log de eventos de estado (apertura, alerta, cierre, reactivacion).

- `heatmap_sectores.png`  
  Qué es: estado técnico por sector.

## 9.5 Analisis avanzado
- `WALK_FORWARD_OOS_YYYYMMDD.csv`  
  Qué es: detalle por split (train/test) y resultados IS/OOS.

- `WALK_FORWARD_RESUMEN_YYYYMMDD.csv`  
  Qué es: resumen por ticker del walk-forward.

- `INFORME_SENSIBILIDAD_YYYYMMDD.pdf`  
  Qué es: sensibilidad de parametros por ticker + conclusiones globales.

- `STRESS_COSTES_YYYYMMDD.csv`  
  Qué es: impacto de distintos escenarios de costes.

- `STRESS_BOOTSTRAP_YYYYMMDD.csv`  
  Qué es: dispersion de metricas via bootstrap de retornos.

## 9.6 Visualizacion interactiva
- `ANALISIS_3D_INTERACTIVO_YYYYMMDD.html`  
  Qué es: mapa 3D de activos (volatilidad, Sharpe, drawdown).
  Uso: identificar “clusters” de eficiencia/riesgo.

## 9.7 Exportes de integracion y control de run
- `RESULTADOS_YYYYMMDD.json`
- `RESULTADOS_YYYYMMDD.parquet`
- `RESULTADOS_VIZ_YYYYMMDD.parquet`
- `SENIALES_YYYYMMDD.csv` (y opcional `.json`)
- `ERROR_RESUMEN_YYYYMMDD.csv` / `.json`
- `RUN_SNAPSHOT_YYYYMMDD.json`
- `RUN_SUMMARY_YYYYMMDD.json`
- `ARTIFACTS_INDEX_YYYYMMDD.json`
- `runs/latest_run.json`

## 10. Diccionario De Metricas (Interpretacion Practica)
Principales métricas de rendimiento:
- `CAGR`: crecimiento anual compuesto.
- `Volatilidad`: dispersion anualizada de retornos.
- `Sharpe`: retorno ajustado por volatilidad.
- `Max Drawdown`: peor caida desde máximo previo.

Riesgo avanzado:
- `Sortino`: similar a Sharpe, penaliza solo caidas.
- `Calmar`: retorno frente al drawdown maximo.
- `Ulcer Index`: severidad de drawdowns (profundidad + duracion).
- `VaR 95`: perdida esperable en un dia “malo” (percentil 5%).
- `CVaR 95`: media de perdidas en el 5% peor cola.
- `DD Max (d)`: duracion maxima de drawdown en dias.

Trades:
- `Trades`: numero de operaciones cerradas.
- `Win %`: porcentaje de operaciones ganadoras.
- `Profit Factor`: ganancias totales / perdidas totales.
- `Expectancy`: expectativa media por trade.
- `Avg Win`, `Avg Loss`: media de ganancia y perdida por trade.
- `Time in Mkt`: porcentaje de tiempo con posicion activa.

## 11. Como Usar Las Salidas En La Practica (Playbook)
Rutina diaria recomendada:
1. Ejecutar run con fecha fin cerrada.
2. Revisar `DATA_VALIDATION_*` para confirmar universo válido.
3. Revisar `DASHBOARD_*` para situación técnica general.
4. Revisar `Analisis_tecnico_tabla_completa_enriquecido_*`:
- Alertas de Entrada -> candidatos a vigilancia/ejecución.
- Alertas de Salida -> posiciones a reducir/cerrar.
5. Revisar `journal_operaciones_hasta_*` y `journal_eventos_hasta_*` para seguimiento.
6. Revisar `INFORME_RECOMENDACION_PERFILES_*` para asignación táctica.
7. Revisar `INFORME_MI_CARTERA_*` para control de P&L real.

Rutina semanal/mensual:
1. Revisar `WALK_FORWARD_*` (robustez OOS).
2. Revisar `INFORME_SENSIBILIDAD_*` (estabilidad de parámetros).
3. Revisar `STRESS_*` (resistencia a costes/cola).
4. Ajustar parámetros/pesos solo si la evidencia es consistente y repetida.

## 12. Mensajes Frecuentes Y Su Significado
- `YFPricesMissingError`: no hay datos para el rango solicitado (no siempre implica ticker inválido).
- `rows<...` en validación: ticker descartado por histórico insuficiente.
- `N/A` en métricas de `Mercado` dentro de tabla de trades: esperado (no hay “trades” en buy&hold puro).
- `journal_eventos_hasta_*.csv` vacío: posible si no hubo cambios de estado en el periodo.

## 13. Buenas Practicas De Formacion A Usuarios
- Explicar primero el flujo completo, luego entrar en cada informe.
- No empezar por métricas avanzadas sin contexto de señales y estado.
- Separar claramente “análisis de mercado” vs “análisis de estrategia combinada”.
- Reforzar que una métrica aislada no decide por sí sola.
- Trabajar con casos reales de tickers del último run para que el aprendizaje sea transferible.

## 14. Limitaciones Y Aviso
- El sistema analiza históricos y genera señales cuantitativas; no garantiza resultados futuros.
- Los datos pueden variar por proveedor y revisiones.
- Este material no constituye asesoramiento financiero.

## 15. Checklist De Clase (Para El Formador)
Antes de la sesión:
- Verificar `config.json`.
- Ejecutar un run de prueba y validar que se generan artefactos.
- Confirmar que `run.log` no tiene errores críticos.

Durante la sesión:
- Mostrar recorrido de carpetas `runs/YYYYMMDD`.
- Explicar 1 ticker de extremo “bueno” y 1 ticker de extremo “malo”.
- Comparar una decisión basada en una sola métrica vs decisión multicriterio.

Después de la sesión:
- Entregar este manual.
- Entregar presentación.
- Entregar ejemplo de `config.json` para práctica.

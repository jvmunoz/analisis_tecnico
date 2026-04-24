# Presentacion Curso Usuarios - Aplicacion De Analisis Tecnico

Formato: guion de diapositivas en Markdown  
Duracion sugerida: 90-120 minutos

---

## Diapositiva 1 - Titulo
Curso de uso de la aplicacion de analisis tecnico y reporting cuantitativo.

Objetivo de hoy:
- Entender funcionalidades.
- Ejecutar correctamente.
- Interpretar salidas.
- Convertir salidas en decisiones operativas.

---

## Diapositiva 2 - Agenda
1. Vision general de la aplicacion.
2. Flujo de ejecucion.
3. Configuracion clave.
4. Informes y archivos de salida.
5. Interpretacion de metricas.
6. Taller practico.
7. FAQ y buenas practicas.

---

## Diapositiva 3 - Que Problema Resuelve
La aplicacion unifica en un solo run:
- Descarga de datos.
- Estrategias técnicas (Tendencia, Bollinger, RSI, MACD).
- Combinacion de estrategias.
- Evaluacion de rendimiento/riesgo.
- Recomendaciones y seguimiento operativo.

Resultado: un set completo de informes para analisis, decision y control.

---

## Diapositiva 4 - Arquitectura Funcional
Entrada:
- `EstrategiaCombinadaRSI.py`

Orquestador:
- `estrategia/app.py`

Capas:
- Datos y validacion.
- Estrategias y metricas.
- Informes.
- Analisis avanzado.
- Flujo enriquecido y journal.

---

## Diapositiva 5 - Ejecucion Basica
Comandos:

```powershell
python EstrategiaCombinadaRSI.py --interactive
python EstrategiaCombinadaRSI.py --batch
python EstrategiaCombinadaRSI.py --config config.json --batch
```

Idea clave:
- En `interactive` se pide fecha fin.
- En `batch` toma la configuracion.

---

## Diapositiva 6 - Fecha Fin Y Carpeta De Run
Fecha fin:
- Por defecto: ayer (sesion cerrada).
- Puede fijarse manualmente.

Salida:
- `Prueba/runs/YYYYMMDD` (donde `YYYYMMDD` = fecha fin efectiva).

Mensaje esperado:
- Ruta de artefactos y `run.log`.

---

## Diapositiva 7 - Flujo End-To-End
1. Carga config y semillas.
2. Construye universo de tickers.
3. Descarga datos.
4. Quality + Validation.
5. Analisis por ticker.
6. Informes principales.
7. Flujo enriquecido.
8. Analisis avanzado.
9. Exportaciones y resumen final.

---

## Diapositiva 8 - Configuracion Critica Para Usuarios
Bloques que mas impactan:
- `params.*` (parametros de estrategias).
- `pesos_estrategias`.
- `data_validation`.
- `analisis_avanzado`.
- `export_results` y `signal_trace`.

Defaults actuales:
- Tendencia 50/200.
- Bollinger 30/2.
- RSI 14 (30/60).
- MACD 8/20/9.
- Pesos 0.357 / 0.272 / 0.240 / 0.131.

---

## Diapositiva 9 - Salidas De Control De Datos
Archivos:
- `DATA_QUALITY_*.csv`
- `DATA_VALIDATION_*.csv`

Para que sirven:
- Detectar calidad deficiente.
- Entender por que un ticker se mantiene (`KEEP`) o se excluye (`DROP`).

Mensaje para usuarios:
- No analizar conclusiones de un ticker que no paso validacion.

---

## Diapositiva 10 - Informes Nucleares
Archivos:
- `INFORME_INDIVIDUAL_*.pdf`
- `INFORME_AGREGADO_*.pdf`
- `INFORME_DETALLADO_METRICAS_*.pdf`
- `DASHBOARD_INDICADORES_TECNICOS_*.pdf`
- `dashboard_data_*.csv`

Uso:
- Individual: detalle por activo.
- Agregado: visión de cartera.
- Detallado: performance + riesgo + trades + estado.
- Dashboard: monitor operativo diario.

---

## Diapositiva 11 - Informes De Seleccion Y Asignacion
Archivos:
- `INFORME_RESUMEN_GANADORES_*.pdf`
- `INFORME_CAMBIOS_ESTADO_*.pdf`
- `Inversion_Estrategica_Largo_Plazo_*.pdf`
- `INFORME_RECOMENDACION_PERFILES_*.pdf`
- `INFORME_MI_CARTERA_*.pdf`

Uso:
- Ranking de estrategias por ticker.
- Seguimiento de entradas/salidas recientes.
- Seleccion estructural de activos.
- Reparto por perfil de riesgo.
- Control de cartera real.

---

## Diapositiva 12 - Flujo Enriquecido
Archivos:
- `Analisis_tecnico_tabla_completa_enriquecido_*.pdf`
- `Asignacion_por_riesgo_enriquecido_*.pdf`
- `journal_operaciones_hasta_*.csv`
- `journal_eventos_hasta_*.csv`
- `heatmap_sectores.png`

Valor operativo:
- Señales accionables.
- Alertas de entrada y salida.
- Seguimiento continuo del estado de operaciones.

---

## Diapositiva 13 - Analisis Avanzado
Archivos:
- `WALK_FORWARD_OOS_*.csv`
- `WALK_FORWARD_RESUMEN_*.csv`
- `INFORME_SENSIBILIDAD_*.pdf`
- `STRESS_COSTES_*.csv`
- `STRESS_BOOTSTRAP_*.csv`
- `ANALISIS_3D_INTERACTIVO_*.html`

Para que se usan:
- Validar robustez fuera de muestra.
- Medir estabilidad de parametros.
- Cuantificar fragilidad a costes y cola.

---

## Diapositiva 14 - Como Leer Las Metricas (Parte 1)
Rendimiento:
- `CAGR`: crecimiento anual compuesto.
- `Volatilidad`: variabilidad de retornos.
- `Sharpe`: retorno por unidad de riesgo total.
- `Max Drawdown`: peor caída histórica.

Regla didactica:
- Nunca evaluar una sola métrica aislada.

---

## Diapositiva 15 - Como Leer Las Metricas (Parte 2)
Riesgo avanzado:
- `Sortino`: castiga solo retornos negativos.
- `Calmar`: retorno frente a drawdown.
- `Ulcer`: severidad de drawdowns.
- `VaR 95` y `CVaR 95`: riesgo de cola.
- `DD Max (d)`: máxima duración de drawdown en días.

---

## Diapositiva 16 - Como Leer Las Metricas (Parte 3)
Trades:
- `Trades`
- `Win %`
- `Profit Factor`
- `Expectancy`
- `Avg Win` / `Avg Loss`
- `Time in Mkt`

Interpretacion base:
- Alta tasa de acierto no siempre implica mejor estrategia.
- `Profit Factor` y `Expectancy` suelen ser mejores guías de calidad operativa.

---

## Diapositiva 17 - Playbook Diario Recomendado
1. Revisar `DATA_VALIDATION`.
2. Revisar `DASHBOARD`.
3. Revisar alertas en `Analisis_tecnico_tabla_completa_enriquecido`.
4. Actualizar seguimiento en `journal_operaciones` y `journal_eventos`.
5. Contrastar con `INFORME_RECOMENDACION_PERFILES`.
6. Verificar impacto en `INFORME_MI_CARTERA`.

---

## Diapositiva 18 - Taller Practico (30 Min)
Ejercicio:
1. Ejecutar un run con fecha fija.
2. Identificar 2 tickers `KEEP` y 1 `DROP`.
3. Elegir 1 oportunidad de entrada y 1 alerta de salida.
4. Justificar decisión con al menos 3 métricas.
5. Proponer asignacion para perfil Conservador y Neutral.

Resultado esperado:
- Los usuarios conectan salida tecnica con decisión operativa.

---

## Diapositiva 19 - Errores Frecuentes Y Respuesta
- `YFPricesMissingError`: revisar rango de fechas y disponibilidad histórica.
- `DROP` por `rows<...`: el ticker no tiene historial suficiente para ese corte.
- `N/A` en mercado dentro tabla de trades: esperado.
- `journal_eventos` vacío: posible si no hubo cambios de estado.

---

## Diapositiva 20 - Buenas Practicas
- Trabajar siempre con sesión cerrada.
- No tocar parámetros sin evidencia multi-informe.
- Guardar trazabilidad (`RUN_SUMMARY`, `RUN_SNAPSHOT`, `ERROR_RESUMEN`).
- Explicar siempre diferencia entre:
- Métricas de mercado (activo).
- Métricas de combinada (estrategia operativa).

---

## Diapositiva 21 - Cierre
Mensajes clave:
- La herramienta no es solo “señales”; es un sistema de decisión completo.
- Calidad de datos y robustez importan tanto como la rentabilidad.
- El valor está en la disciplina de lectura y seguimiento de los reportes.

Siguientes pasos sugeridos para el equipo:
1. Estandarizar un checklist diario de 10 minutos.
2. Revisar semanalmente walk-forward/sensibilidad.
3. Definir un protocolo interno de cambios de parámetros.

---

## Anexo - Guion Del Formador (Notas Rapidas)
Bloque 1 (20 min): Visión general + ejecución.  
Bloque 2 (30 min): Informes y lectura de métricas.  
Bloque 3 (20 min): Flujo enriquecido y journals.  
Bloque 4 (20 min): Taller guiado con un run real.  
Bloque 5 (10 min): Preguntas y checklist final.

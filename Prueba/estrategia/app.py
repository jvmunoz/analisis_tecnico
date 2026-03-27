
import os
import pandas as pd
import random
from datetime import datetime, timedelta
from pathlib import Path
import time
import sys
import atexit

from .config_runtime import init_runtime, cargar_configuracion, _start_watchdog
from .ibex import (
    HISTORIAL_IBEX_FILE,
    obtener_componentes_ibex,
    cargar_historial_ibex,
    construir_dicc_tickers_desde_historial,
    construir_mapa_historial,
    filtrar_datos_por_historial,
)
from .portfolio import cargar_cartera
from .data import (
    obtener_datos_historicos,
    generar_reporte_calidad_datos,
    validar_datos,
    limpiar_cache_mercado,
)
from .analysis import (
    seleccionar_tickers_avanzado,
    generar_informe_walk_forward,
    generar_sensibilidad_parametros,
    generar_stress_tests,
)
from .reports_reportlab import generar_pdf_detalles_estado
from .reports_matplotlib import (
    crear_informe_pdf,
    generar_pdf_resumen_ganadores,
    generar_pdf_cambios_estado,
    generar_pdf_dashboard_tecnico,
    generar_informe_estrategico_largo_plazo,
    generar_grafico_3d_activos,
)
from .enriched import ejecutar_flujo_enriquecido_completo, generar_recomendacion_perfiles
from .strategies import ejecutar_analisis_completo_individual, ejecutar_analisis_completo_agregado
from .metrics import calcular_metricas_desde_returns
from .utils import _to_serializable
import json

def _project_base_dir():
    return Path(__file__).resolve().parents[1]


def _prepare_output_directory(base_dir, run_suffix=None):
    if run_suffix is None:
        run_suffix = datetime.now().strftime("%Y%m%d")
    out_dir = base_dir / "runs" / run_suffix
    out_dir.mkdir(parents=True, exist_ok=True)
    os.chdir(out_dir)
    return out_dir


class _TeeStream:
    def __init__(self, *streams):
        self._streams = streams

    def write(self, data):
        for s in self._streams:
            try:
                s.write(data)
            except Exception:
                pass
        return len(data)

    def flush(self):
        for s in self._streams:
            try:
                s.flush()
            except Exception:
                pass

    def isatty(self):
        return False


def _activar_run_log(out_dir):
    log_path = Path(out_dir) / "run.log"
    fh = open(log_path, "a", encoding="utf-8")
    orig_stdout = sys.stdout
    orig_stderr = sys.stderr
    sys.stdout = _TeeStream(orig_stdout, fh)
    sys.stderr = _TeeStream(orig_stderr, fh)

    def _cleanup():
        try:
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr
        finally:
            try:
                fh.flush()
                fh.close()
            except Exception:
                pass

    atexit.register(_cleanup)
    return str(log_path)


def _get_metric_value(metricas, keys, default="N/A"):
    if not isinstance(metricas, dict):
        return default
    for k in keys:
        v = metricas.get(k)
        if v not in (None, ""):
            return v
    return default


def _get_last_event(metricas, estrategia, is_entry=True):
    key = "Ultima Entrada" if is_entry else "Ultima Salida"
    keys = [f"{key}_{estrategia}"]
    return _get_metric_value(metricas, keys, default="N/A")


def _exportar_error_summary(error_log, suffix, err_cfg):
    if not err_cfg.get("enabled", True):
        return
    payload = error_log or []
    if err_cfg.get("csv", True):
        try:
            pd.DataFrame(payload).to_csv(
                f"ERROR_RESUMEN_{suffix}.csv", index=False, encoding="utf-8"
            )
        except Exception as e:
            print(f"[AVISO] No se pudo exportar resumen de errores CSV: {e}")
    if err_cfg.get("json", True):
        try:
            with open(f"ERROR_RESUMEN_{suffix}.json", "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, default=_to_serializable)
        except Exception as e:
            print(f"[AVISO] No se pudo exportar resumen de errores JSON: {e}")


def _guardar_run_summary(
    fecha_v,
    lista_tickers,
    tickers_procesados,
    ganadores_por_ticker,
    error_log,
    started_at_ts,
):
    try:
        finished_at = time.time()
        summary_filename = f"RUN_SUMMARY_{fecha_v.replace('-', '')}.json"
        summary = {
            "fecha_ultima": fecha_v,
            "run_started_at": datetime.fromtimestamp(started_at_ts).isoformat(),
            "run_finished_at": datetime.fromtimestamp(finished_at).isoformat(),
            "duration_seconds": round(finished_at - started_at_ts, 2),
            "tickers_objetivo": len(lista_tickers or []),
            "tickers_procesados": int(tickers_procesados or 0),
            "tickers_con_resultado": len(ganadores_por_ticker or {}),
            "errores": len(error_log or []),
            "output_dir": str(Path.cwd()),
            "summary_file": summary_filename,
        }
        with open(summary_filename, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, default=_to_serializable)
        return summary
    except Exception as e:
        print(f"[AVISO] No se pudo guardar RUN_SUMMARY: {e}")
        return None


def _actualizar_latest_run(base_dir, summary):
    if not summary:
        return
    try:
        runs_dir = Path(base_dir) / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        latest_payload = {
            "updated_at": datetime.now().isoformat(),
            **summary,
        }
        with open(runs_dir / "latest_run.json", "w", encoding="utf-8") as f:
            json.dump(latest_payload, f, ensure_ascii=False, default=_to_serializable)
    except Exception as e:
        print(f"[AVISO] No se pudo actualizar latest_run.json: {e}")


def _guardar_artifacts_index(fecha_v):
    try:
        suffix = fecha_v.replace("-", "")
        index_file = f"ARTIFACTS_INDEX_{suffix}.json"
        artifacts = []
        for p in sorted(Path.cwd().iterdir(), key=lambda x: x.name.lower()):
            if not p.is_file():
                continue
            stat = p.stat()
            artifacts.append(
                {
                    "name": p.name,
                    "path": str(p.resolve()),
                    "size_bytes": int(stat.st_size),
                    "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )
        payload = {
            "fecha_ultima": fecha_v,
            "output_dir": str(Path.cwd()),
            "files_count": len(artifacts),
            "files": artifacts,
        }
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, default=_to_serializable)
        return index_file
    except Exception as e:
        print(f"[AVISO] No se pudo guardar ARTIFACTS_INDEX: {e}")
        return None


def main():
    started_at_ts = time.time()
    init_runtime()
    pd.set_option("future.no_silent_downcasting", True)
    CONFIG = cargar_configuracion()
    _start_watchdog(CONFIG)
    base_dir = _project_base_dir()
    rep_cfg = CONFIG.get("reproducibilidad", {})
    if rep_cfg.get("enabled", True):
        seed = rep_cfg.get("seed", 42)
        random.seed(seed)
        try:
            import numpy as np

            np.random.seed(seed)
        except Exception:
            pass
    print("\n" + "=" * 50, flush=True)
    print("INICIANDO EJECUCIÃ“N DEL SCRIPT", flush=True)
    print("=" * 50 + "\n", flush=True)
    # --- PARÃMETROS DE ENTRADA ---
    historial_ibex_path = str(base_dir / HISTORIAL_IBEX_FILE)
    HISTORIAL_IBEX = cargar_historial_ibex(historial_ibex_path)
    if HISTORIAL_IBEX:
        DICT_TICKERS = construir_dicc_tickers_desde_historial(HISTORIAL_IBEX)
    else:
        DICT_TICKERS = obtener_componentes_ibex()
        if not DICT_TICKERS:
            lista_respaldo = [
                "ANA.MC",
                "ANE.MC",
                "ACX.MC",
                "ACS.MC",
                "AENA.MC",
                "AMS.MC",
                "MTS.MC",
                "SAN.MC",
                "SAB.MC",
                "BKT.MC",
                "BBVA.MC",
                "CABK.MC",
                "CLNX.MC",
                "ENG.MC",
                "ELE.MC",
                "FER.MC",
                "FDR.MC",
                "GRF.MC",
                "IAG.MC",
                "IBE.MC",
                "ITX.MC",
                "IDR.MC",
                "COL.MC",
                "LOG.MC",
                "MAP.MC",
                "MRL.MC",
                "NTGY.MC",
                "PUIG.MC",
                "RED.MC",
                "REP.MC",
                "ROVI.MC",
                "SCYR.MC",
                "SLR.MC",
                "TEF.MC",
                "UNI.MC",
            ]
            DICT_TICKERS = {t: t for t in lista_respaldo}

    benchmarks = CONFIG.get("benchmarks") or ["^IBEX"]
    benchmarks = list(dict.fromkeys(benchmarks))
    for b in benchmarks:
        if b not in DICT_TICKERS:
            DICT_TICKERS[b] = b

    # Cargar Cartera Personal
    cartera_path = str(base_dir / "cartera.csv")
    df_cartera, tickers_cartera, fecha_inicio_cartera, df_log_completo = cargar_cartera(
        cartera_path
    )

    # Ajustar FECHA_INICIO segÃºn el primer movimiento de la cartera (para captar dividendos)
    FECHA_INICIO_SISTEMA = CONFIG.get("fecha_inicio_sistema", "2020-01-01")
    if fecha_inicio_cartera is not None:
        str_fecha_cartera = (fecha_inicio_cartera - timedelta(days=5)).strftime(
            "%Y-%m-%d"
        )
        FECHA_INICIO = min(FECHA_INICIO_SISTEMA, str_fecha_cartera)
    else:
        FECHA_INICIO = FECHA_INICIO_SISTEMA

    # Fusionar tickers de la cartera con la lista principal
    tickers_sin_indice = sorted([t for t in DICT_TICKERS.keys() if t not in benchmarks])
    for t in tickers_cartera:
        if t not in tickers_sin_indice:
            tickers_sin_indice.append(t)
            if t not in DICT_TICKERS:
                DICT_TICKERS[t] = t

    LISTA_TICKERS = tickers_sin_indice + benchmarks

    cache_cfg = CONFIG.get("data_cache", {})
    exclude_tickers = set(cache_cfg.get("exclude_tickers", []) or [])
    if exclude_tickers:
        before = len(LISTA_TICKERS)
        LISTA_TICKERS = [t for t in LISTA_TICKERS if t.upper() not in exclude_tickers]
        removed = before - len(LISTA_TICKERS)
        print(
            f"[CACHE] exclude_tickers activo: {removed} ticker(s) excluido(s).",
            flush=True,
        )

    max_tickers_per_run = cache_cfg.get("max_tickers_per_run")
    if max_tickers_per_run:
        LISTA_TICKERS = LISTA_TICKERS[: int(max_tickers_per_run)]
        print(
            f"[CACHE] max_tickers_per_run activo: {len(LISTA_TICKERS)} ticker(s).",
            flush=True,
        )

    # FECHA_INICIO ya ha sido calculada dinÃ¡micamente arriba

    # --- SELECCIÃ“N DE FECHA FIN ---
    default_fin = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    if CONFIG.get("ask_end_date", True):
        print(
            f"\n[CONFIGURACION] Fecha Fin por defecto: AYER ({default_fin}) "
            "(ultima sesion cerrada)"
        )
        print(
            "Si quieres usar otra fecha (para backtest historico), introducela abajo (YYYY-MM-DD)."
        )
        while True:
            input_fecha = input(
                ">> Introduce Fecha Fin (YYYY-MM-DD) o Enter para AYER: "
            ).strip()
            if not input_fecha:
                FECHA_FIN = os.getenv("FECHA_FIN") or default_fin
                print(f"--> Usando Fecha Fin: {FECHA_FIN}")
                break
            try:
                datetime.strptime(input_fecha, "%Y-%m-%d")
                FECHA_FIN = input_fecha
                print(f"--> Usando Fecha Fin PERSONALIZADA: {FECHA_FIN}")
                break
            except ValueError:
                print(
                    f"!! Formato incorrecto ('{input_fecha}'). Usa YYYY-MM-DD o Enter para HOY."
                )
    else:
        cfg_fecha_fin = CONFIG.get("fecha_fin")
        if cfg_fecha_fin in (None, "", "HOY", "hoy"):
            FECHA_FIN = os.getenv("FECHA_FIN") or default_fin
        else:
            FECHA_FIN = cfg_fecha_fin
        print(f"[CONFIG] Fecha Fin (sin prompt): {FECHA_FIN}")

    out_dir = _prepare_output_directory(base_dir, FECHA_FIN.replace("-", ""))
    log_path = _activar_run_log(out_dir)
    print(f"[RUTA] Artefactos de salida en: {out_dir}", flush=True)
    print(f"[RUTA] Log de ejecucion: {log_path}", flush=True)

    COSTES_TRANSACCION = CONFIG.get("costes_transaccion", 0.001)
    EXECUTION_DELAY = CONFIG.get("execution_delay", 1)
    SLIPPAGE_BPS = CONFIG.get("slippage", {}).get("bps", 5.0)
    SLIPPAGE_ATR_MULT = CONFIG.get("slippage", {}).get("atr_mult", 0.0)
    SLIPPAGE_VOL_MULT = CONFIG.get("slippage", {}).get("vol_mult", 0.05)
    params_tendencia = CONFIG.get("params", {}).get(
        "tendencia", {"short_window": 50, "long_window": 140}
    )
    params_bollinger = CONFIG.get("params", {}).get(
        "bollinger", {"window": 30, "num_std_dev": 3}
    )
    params_rsi = CONFIG.get("params", {}).get(
        "rsi", {"window": 14, "umbral_compra": 30, "umbral_salida": 60}
    )
    params_macd = CONFIG.get("params", {}).get(
        "macd", {"fast_period": 8, "slow_period": 20, "signal_period": 9}
    )
    PESOS_ESTRATEGIAS = CONFIG.get(
        "pesos_estrategias",
        {"tendencia": 0.323, "bollinger": 0.232, "rsi": 0.197, "macd": 0.248},
    )

    # --- CONFIGURACION ANALISIS AVANZADO ---
    # Cambia a False para desactivar anÃ¡lisis pesados si el programa tarda demasiado
    ENABLE_WALK_FORWARD = CONFIG.get("analisis_avanzado", {}).get(
        "enable_walk_forward", True
    )
    ENABLE_SENSITIVITY = CONFIG.get("analisis_avanzado", {}).get(
        "enable_sensitivity", True
    )
    ENABLE_STRESS_TESTS = CONFIG.get("analisis_avanzado", {}).get(
        "enable_stress_tests", True
    )

    # Si es True, solo realiza analisis avanzados (Sensibilidad, Stress, etc) sobre la cartera activa
    SOLO_CARTERA_EN_AVANZADO = CONFIG.get("analisis_avanzado", {}).get(
        "solo_cartera", False
    )

    MAX_TICKERS_AVANZADO = CONFIG.get("analisis_avanzado", {}).get("max_tickers", 40)
    WALK_FORWARD_TRAIN_YEARS = (
        CONFIG.get("analisis_avanzado", {})
        .get("walk_forward", {})
        .get("train_years", 3)
    )
    WALK_FORWARD_TEST_YEARS = (
        CONFIG.get("analisis_avanzado", {}).get("walk_forward", {}).get("test_years", 1)
    )
    WALK_FORWARD_STEP_YEARS = (
        CONFIG.get("analisis_avanzado", {}).get("walk_forward", {}).get("step_years", 1)
    )
    WALK_FORWARD_METRIC = (
        CONFIG.get("analisis_avanzado", {})
        .get("walk_forward", {})
        .get("metric", "Ratio de Sharpe")
    )

    SENSITIVITY_METRIC = CONFIG.get("analisis_avanzado", {}).get(
        "sensitivity_metric", "Ratio de Sharpe"
    )

    COST_SCENARIOS = {
        "Base": COSTES_TRANSACCION,
        "Alta": COSTES_TRANSACCION * 2,
        "Extrema": COSTES_TRANSACCION * 4,
    }
    BOOTSTRAP_ITER = (
        CONFIG.get("analisis_avanzado", {}).get("bootstrap", {}).get("iters", 300)
    )
    BOOTSTRAP_SEED = (
        CONFIG.get("analisis_avanzado", {}).get("bootstrap", {}).get("seed", 42)
    )

    GRID_PARAMETROS = CONFIG.get(
        "grid_parametros",
        {
            "tendencia": {"short_window": [20, 50, 80], "long_window": [100, 140, 200]},
            "bollinger": {"window": [20, 30, 40], "num_std_dev": [2.0, 2.5, 3.0]},
            "rsi": {
                "window": [10, 14, 20],
                "umbral_compra": [25, 30, 35],
                "umbral_salida": [50, 55, 60],
            },
            "macd": {
                "fast_period": [8, 12],
                "slow_period": [20, 26],
                "signal_period": [9],
            },
        },
    )
    if "default" not in GRID_PARAMETROS:
        GRID_PARAMETROS["default"] = {
            "tendencia": params_tendencia,
            "bollinger": params_bollinger,
            "rsi": params_rsi,
            "macd": params_macd,
        }

    removed_cache_files = limpiar_cache_mercado(cache_cfg)
    if removed_cache_files > 0:
        print(f"[CACHE] Limpieza inicial completada: {removed_cache_files} archivo(s).")

    datos_completos = obtener_datos_historicos(
        tickers=LISTA_TICKERS,
        start_date=FECHA_INICIO,
        end_date=FECHA_FIN,
        cache_config=cache_cfg,
        omitted_tickers_csv=f"TICKERS_OMITIDOS_{FECHA_FIN.replace('-', '')}.csv",
    )
    data_suffix = FECHA_FIN.replace("-", "")
    if datos_completos is not None and not datos_completos.empty and "date" in datos_completos.columns:
        max_data_date = pd.to_datetime(datos_completos["date"], errors="coerce").max()
        if pd.notna(max_data_date):
            data_suffix = max_data_date.strftime("%Y%m%d")
    if CONFIG.get("data_quality_report", True) and datos_completos is not None:
        generar_reporte_calidad_datos(datos_completos, f"DATA_QUALITY_{data_suffix}.csv")
    val_cfg = CONFIG.get("data_validation", {})
    if val_cfg.get("enabled", False) and datos_completos is not None:
        datos_completos, _ = validar_datos(
            datos_completos, val_cfg, f"DATA_VALIDATION_{data_suffix}.csv"
        )
    HISTORIAL_MAPA = construir_mapa_historial(HISTORIAL_IBEX) if HISTORIAL_IBEX else {}
    if datos_completos is not None and HISTORIAL_MAPA:
        datos_completos = filtrar_datos_por_historial(
            datos_completos, HISTORIAL_MAPA, tickers_always=tickers_cartera
        )
    if datos_completos is not None:
        fecha_v = datos_completos["date"].max().strftime("%Y-%m-%d")
        resultados_generales = {}
        ganadores_por_ticker = {}
        datos_para_reporte_detallado = []
        cambios_de_estado_recientes = []
        lista_metricas_globales = []
        todas_las_fechas_trading = set()
        error_log = []

        perf_cfg = CONFIG.get("performance", {})
        max_tickers = perf_cfg.get("max_tickers")
        if max_tickers:
            LISTA_TICKERS = LISTA_TICKERS[: int(max_tickers)]
        num_tickers = len(LISTA_TICKERS)
        signal_log = []
        processed_tickers = 0
        for idx, ticker in enumerate(LISTA_TICKERS):
            if idx % 5 == 0:
                print(f"Analizando ({idx + 1}/{num_tickers}): {ticker}")
            datos_ticker_actual = datos_completos[
                datos_completos["ticker"].str.lower() == ticker.lower()
            ].copy()
            if datos_ticker_actual.empty:
                continue

            try:
                df_viz, metricas_combinadas = ejecutar_analisis_completo_individual(
                    datos_ticker_actual,
                    params_tendencia,
                    params_bollinger,
                    params_rsi,
                    params_macd,
                    COSTES_TRANSACCION,
                    PESOS_ESTRATEGIAS,
                    execution_delay=EXECUTION_DELAY,
                    slippage_bps=SLIPPAGE_BPS,
                    slippage_atr_mult=SLIPPAGE_ATR_MULT,
                    slippage_vol_mult=SLIPPAGE_VOL_MULT,
                    signal_log=signal_log,
                    ticker=ticker,
                )

                # Comparativa con benchmarks multiples
                for b in benchmarks:
                    df_b = datos_completos[
                        datos_completos["ticker"].str.lower() == b.lower()
                    ].copy()
                    if df_b.empty:
                        continue
                    bench_returns = (
                        df_b.set_index("date")["daily_return"]
                        .reindex(df_viz.index)
                        .dropna()
                    )
                    if bench_returns.empty:
                        continue
                    bm = calcular_metricas_desde_returns(bench_returns)
                    metricas_combinadas[f"Benchmark_{b}_CAGR"] = bm["CAGR"]
                    metricas_combinadas[f"Benchmark_{b}_Sharpe"] = bm["Sharpe"]
                    metricas_combinadas[f"Benchmark_{b}_Volatilidad"] = bm[
                        "Volatilidad"
                    ]
                    metricas_combinadas[f"Benchmark_{b}_MaxDrawdown"] = bm[
                        "Max Drawdown"
                    ]
            except Exception as e:
                error_log.append(
                    {
                        "phase": "ticker_analysis",
                        "ticker": ticker,
                        "error": str(e),
                    }
                )
                continue
            processed_tickers += 1

            todas_las_fechas_trading.update(df_viz.index.strftime("%Y-%m-%d").tolist())

            operaciones_data = []
            for strat in ["Tendencia", "Bollinger", "RSI", "MACD"]:
                entrada = _get_last_event(metricas_combinadas, strat, is_entry=True)
                salida = _get_last_event(metricas_combinadas, strat, is_entry=False)
                estado = (
                    "Activo"
                    if entrada != "N/A" and (salida == "N/A" or entrada > salida)
                    else "Inactivo"
                )
                operaciones_data.append(
                    {
                        "Estrategia": strat,
                        "Estado": estado,
                        "Ultima Entrada": entrada,
                        "Ultima Salida": salida,
                    }
                )

            datos_para_reporte_detallado.append(
                {
                    "ticker": ticker,
                    "metricas": metricas_combinadas,
                    "operaciones": operaciones_data,
                    "df_viz": df_viz,
                }
            )

            # DetecciÃ³n de cambios
            ultimas_5_fechas = (
                df_viz.index[-5:].strftime("%Y-%m-%d").tolist()
                if len(df_viz) >= 5
                else df_viz.index.strftime("%Y-%m-%d").tolist()
            )
            for strat, col_position in [
                ("Tendencia", "position_tendencia"),
                ("Bollinger", "position_bollinger"),
                ("RSI", "position_rsi"),
                ("MACD", "position_macd"),
            ]:
                ultimas_posiciones = df_viz[col_position].tail(5)
                for i_pos, fecha in enumerate(ultimas_5_fechas):
                    if i_pos < len(ultimas_posiciones):
                        pos = ultimas_posiciones.iloc[i_pos]
                        if pos == 1.0:
                            cambios_de_estado_recientes.append(
                                {
                                    "Ticker": ticker,
                                    "Estrategia": strat,
                                    "Fecha": fecha,
                                    "Evento": "ENTRADA",
                                    "Estado Nuevo": "ACTIVO",
                                }
                            )
                        elif pos == -1.0:
                            cambios_de_estado_recientes.append(
                                {
                                    "Ticker": ticker,
                                    "Estrategia": strat,
                                    "Fecha": fecha,
                                    "Evento": "SALIDA",
                                    "Estado Nuevo": "INACTIVO",
                                }
                            )

            lista_metricas_globales.append(
                {
                    "ticker": ticker,
                    "metricas": metricas_combinadas,
                    "operaciones": operaciones_data,
                    "precio_actual": df_viz["close"].iloc[-1],
                }
            )

            sharpes = {
                s: metricas_combinadas[f"Ratio de Sharpe_{s}"]
                for s in ["Tendencia", "Bollinger", "RSI", "MACD", "Combinada"]
            }
            ganadores_por_ticker[ticker] = max(sharpes, key=sharpes.get)

        try:
            if SOLO_CARTERA_EN_AVANZADO:
                tickers_avanzado = seleccionar_tickers_avanzado(
                    tickers_cartera, tickers_cartera, MAX_TICKERS_AVANZADO
                )
            else:
                tickers_avanzado = seleccionar_tickers_avanzado(
                    LISTA_TICKERS, tickers_cartera, MAX_TICKERS_AVANZADO
                )

            if tickers_avanzado:
                print(
                    f"Analisis avanzado sobre {len(tickers_avanzado)} ticker(s): {', '.join(tickers_avanzado)}"
                )

            if ENABLE_WALK_FORWARD:
                generar_informe_walk_forward(
                    datos_completos,
                    tickers_avanzado,
                    GRID_PARAMETROS,
                    COSTES_TRANSACCION,
                    PESOS_ESTRATEGIAS,
                    execution_delay=EXECUTION_DELAY,
                    slippage_bps=SLIPPAGE_BPS,
                    slippage_atr_mult=SLIPPAGE_ATR_MULT,
                    slippage_vol_mult=SLIPPAGE_VOL_MULT,
                    fecha_ult=fecha_v,
                    train_years=WALK_FORWARD_TRAIN_YEARS,
                    test_years=WALK_FORWARD_TEST_YEARS,
                    step_years=WALK_FORWARD_STEP_YEARS,
                    metric_key=WALK_FORWARD_METRIC,
                )

            if ENABLE_SENSITIVITY:
                generar_sensibilidad_parametros(
                    datos_completos,
                    tickers_avanzado,
                    GRID_PARAMETROS,
                    COSTES_TRANSACCION,
                    execution_delay=EXECUTION_DELAY,
                    slippage_bps=SLIPPAGE_BPS,
                    slippage_atr_mult=SLIPPAGE_ATR_MULT,
                    slippage_vol_mult=SLIPPAGE_VOL_MULT,
                    metric_key=SENSITIVITY_METRIC,
                    fecha_ult=fecha_v,
                    params_actuales={
                        "tendencia": params_tendencia,
                        "bollinger": params_bollinger,
                        "rsi": params_rsi,
                        "macd": params_macd,
                    },
                    pesos_actuales=PESOS_ESTRATEGIAS,
                )

            if ENABLE_STRESS_TESTS:
                generar_stress_tests(
                    datos_completos,
                    tickers_avanzado,
                    params_tendencia,
                    params_bollinger,
                    params_rsi,
                    params_macd,
                    PESOS_ESTRATEGIAS,
                    COST_SCENARIOS,
                    execution_delay=EXECUTION_DELAY,
                    slippage_bps=SLIPPAGE_BPS,
                    slippage_atr_mult=SLIPPAGE_ATR_MULT,
                    slippage_vol_mult=SLIPPAGE_VOL_MULT,
                    bootstrap_iters=BOOTSTRAP_ITER,
                    bootstrap_seed=BOOTSTRAP_SEED,
                    fecha_ult=fecha_v,
                )

            generar_pdf_detalles_estado(
                datos_para_reporte_detallado, DICT_TICKERS, fecha_ult=fecha_v
            )
            generar_pdf_resumen_ganadores(
                ganadores_por_ticker,
                DICT_TICKERS,
                fecha_ult=fecha_v,
                portfolio_tickers=tickers_cartera,
            )
            generar_pdf_cambios_estado(
                cambios_de_estado_recientes,
                todas_las_fechas_trading,
                DICT_TICKERS,
                fecha_ult=fecha_v,
            )
            generar_pdf_dashboard_tecnico(
                datos_para_reporte_detallado,
                DICT_TICKERS,
                fecha_ult=fecha_v,
                portfolio_tickers=tickers_cartera,
            )
            generar_informe_estrategico_largo_plazo(
                lista_metricas_globales,
                DICT_TICKERS,
                fecha_ult=fecha_v,
                portfolio_tickers=tickers_cartera,
            )

            # AnÃ¡lisis enriquecido
            ejecutar_flujo_enriquecido_completo(
                datos_para_reporte_detallado,
                fecha_v,
                tickers_cartera,
                df_cartera,
                df_log_completo=df_log_completo,
            )

            generar_recomendacion_perfiles(
                lista_metricas_globales,
                DICT_TICKERS,
                capital_inicial=10000,
                fecha_ult=fecha_v,
                portfolio_tickers=tickers_cartera,
                lista_datos_completos=datos_para_reporte_detallado,
            )
            generar_grafico_3d_activos(
                lista_metricas_globales, DICT_TICKERS, fecha_ult=fecha_v
            )

            # Informes individuales y agregados
            res_ind = {
                item["ticker"]: {
                    "dataframe": item["df_viz"],
                    "metricas": item["metricas"],
                }
                for item in datos_para_reporte_detallado
            }
            crear_informe_pdf(
                res_ind,
                PESOS_ESTRATEGIAS,
                DICT_TICKERS,
                is_aggregated=False,
                fecha_ult=fecha_v,
            )

            df_viz_agregado, metricas_agregadas = ejecutar_analisis_completo_agregado(
                datos_completos,
                params_tendencia,
                params_bollinger,
                params_rsi,
                params_macd,
                COSTES_TRANSACCION,
                PESOS_ESTRATEGIAS,
                execution_delay=EXECUTION_DELAY,
                slippage_bps=SLIPPAGE_BPS,
                slippage_atr_mult=SLIPPAGE_ATR_MULT,
                slippage_vol_mult=SLIPPAGE_VOL_MULT,
                resultados_previos=datos_para_reporte_detallado,
            )
            if not df_viz_agregado.empty:
                crear_informe_pdf(
                    {
                        "CARTERA_AGREGADA": {
                            "dataframe": df_viz_agregado,
                            "metricas": metricas_agregadas,
                        }
                    },
                    PESOS_ESTRATEGIAS,
                    DICT_TICKERS,
                    is_aggregated=True,
                    fecha_ult=fecha_v,
                )

            export_cfg = CONFIG.get("export_results", {})
            if export_cfg.get("enabled", False):
                suffix = fecha_v.replace("-", "")
                rows = []
                for item in lista_metricas_globales:
                    df_viz = None
                    for d in datos_para_reporte_detallado:
                        if d["ticker"] == item["ticker"]:
                            df_viz = d["df_viz"]
                            break
                    df_viz_records = (
                        df_viz.reset_index().to_dict("records") if df_viz is not None else []
                    )
                    rows.append(
                        {
                            "ticker": item["ticker"],
                            "metricas": item["metricas"],
                            "operaciones": item["operaciones"],
                            "precio_actual": item["precio_actual"],
                            "ganadora": ganadores_por_ticker.get(item["ticker"]),
                            "df_viz": df_viz_records,
                        }
                    )
                if export_cfg.get("json", True):
                    payload = {
                        "fecha_ultima": fecha_v,
                        "ganadores": ganadores_por_ticker,
                        "tickers": rows,
                    }
                    with open(
                        f"RESULTADOS_{suffix}.json", "w", encoding="utf-8"
                    ) as f:
                        json.dump(
                            payload, f, ensure_ascii=False, default=_to_serializable
                        )
                if export_cfg.get("parquet", True):
                    try:
                        df_export = pd.json_normalize(
                            [
                                {
                                    "ticker": r["ticker"],
                                    "ganadora": r["ganadora"],
                                    "precio_actual": r["precio_actual"],
                                    **r["metricas"],
                                }
                                for r in rows
                            ]
                        )
                        df_export.to_parquet(
                            f"RESULTADOS_{suffix}.parquet", index=False
                        )
                        # Exportar df_viz largo (puede ser pesado)
                        viz_rows = []
                        for r in rows:
                            for rec in r["df_viz"]:
                                rec = dict(rec)
                                rec["ticker"] = r["ticker"]
                                viz_rows.append(rec)
                        if viz_rows:
                            df_viz_export = pd.DataFrame(viz_rows)
                            if "dividends" in df_viz_export.columns:
                                df_viz_export["dividends"] = pd.to_numeric(
                                    df_viz_export["dividends"]
                                    .astype(str)
                                    .str.replace(r"[^0-9.\-]", "", regex=True),
                                    errors="coerce",
                                )
                            df_viz_export.to_parquet(
                                f"RESULTADOS_VIZ_{suffix}.parquet", index=False
                            )
                    except Exception as e:
                        print(f"[AVISO] No se pudo exportar parquet: {e}")

            trace_cfg = CONFIG.get("signal_trace", {})
            if trace_cfg.get("enabled", False) and signal_log:
                suffix = fecha_v.replace("-", "")
                if trace_cfg.get("csv", True):
                    try:
                        pd.DataFrame(signal_log).to_csv(
                            f"SENIALES_{suffix}.csv", index=False, encoding="utf-8"
                        )
                    except Exception as e:
                        print(f"[AVISO] No se pudo exportar seÃ±ales CSV: {e}")
                if trace_cfg.get("json", False):
                    try:
                        with open(
                            f"SENIALES_{suffix}.json", "w", encoding="utf-8"
                        ) as f:
                            json.dump(
                                signal_log,
                                f,
                                ensure_ascii=False,
                                default=_to_serializable,
                            )
                    except Exception as e:
                        print(f"[AVISO] No se pudo exportar seÃ±ales JSON: {e}")
        except Exception as e:
            print(f"Error: {e}")
            import traceback

            traceback.print_exc()

        err_cfg = CONFIG.get("error_summary", {})
        suffix = fecha_v.replace("-", "")
        _exportar_error_summary(error_log, suffix, err_cfg)
        if err_cfg.get("enabled", True) and error_log:
            print(f"[RESUMEN] Errores registrados: {len(error_log)}")
        elif err_cfg.get("enabled", True):
            print("[RESUMEN] Sin errores durante el procesamiento.")

        rep_cfg = CONFIG.get("reproducibilidad", {})
        if rep_cfg.get("enabled", True) and rep_cfg.get("snapshot", True):
            try:
                snapshot = {
                    "fecha_ultima": fecha_v,
                    "tickers": LISTA_TICKERS,
                    "config": CONFIG,
                    "version_script": "modular",
                }
                with open(
                    f"RUN_SNAPSHOT_{fecha_v.replace('-', '')}.json",
                    "w",
                    encoding="utf-8",
                ) as f:
                    json.dump(snapshot, f, ensure_ascii=False, default=_to_serializable)
            except Exception as e:
                print(f"[AVISO] No se pudo guardar snapshot: {e}")

        summary = _guardar_run_summary(
            fecha_v=fecha_v,
            lista_tickers=LISTA_TICKERS,
            tickers_procesados=processed_tickers,
            ganadores_por_ticker=ganadores_por_ticker,
            error_log=error_log,
            started_at_ts=started_at_ts,
        )
        artifacts_index = _guardar_artifacts_index(fecha_v)
        if isinstance(summary, dict):
            summary["artifacts_index"] = artifacts_index
        _actualizar_latest_run(base_dir, summary)


if __name__ == "__main__":
    main()


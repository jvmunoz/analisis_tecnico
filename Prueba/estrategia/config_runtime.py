import sys
import os
import time
import threading
import signal
import multiprocessing
import json
import builtins
from datetime import datetime
from pathlib import Path


def configurar_utf8_salida():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


_ORIGINAL_PRINT = builtins.print


def _fix_mojibake_text(text):
    """Repara texto mojibake comun (UTF-8 interpretado como latin-1/cp1252)."""
    if not isinstance(text, str):
        return text
    if not any(mark in text for mark in ("Ã", "Â", "â", "�")):
        return text
    for enc in ("latin-1", "cp1252"):
        try:
            repaired = text.encode(enc).decode("utf-8")
            if repaired:
                return repaired
        except Exception:
            continue
    return text


def _patch_print_for_utf8():
    """Parchea print para sanear texto mojibake en consola y run.log."""
    if builtins.print is not _ORIGINAL_PRINT:
        return

    def _safe_print(*args, **kwargs):
        fixed_args = [
            _fix_mojibake_text(a) if isinstance(a, str) else a
            for a in args
        ]
        _ORIGINAL_PRINT(*fixed_args, **kwargs)

    builtins.print = _safe_print


def log(msg):
    """Funcion de logging centralizada para seguimiento de progreso."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def _handle_sigint(signum, frame):
    print("\n[INTERRUPCION] Senal recibida. Terminando proceso...", flush=True)
    os._exit(1)


def init_runtime():
    _patch_print_for_utf8()
    configurar_utf8_salida()
    try:
        signal.signal(signal.SIGINT, _handle_sigint)
        signal.signal(signal.SIGTERM, _handle_sigint)
    except Exception:
        pass
    log("Iniciando sistema de analisis tecnico...")


def _deep_update(base, updates):
    for k, v in updates.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_update(base[k], v)
        else:
            base[k] = v
    return base


def _parse_cli_flags(argv):
    cfg_path = None
    batch_flag = None
    ask_end_date_flag = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--config", "-c") and i + 1 < len(argv):
            cfg_path = argv[i + 1]
            i += 2
            continue
        if arg == "--batch":
            batch_flag = True
        if arg == "--interactive":
            batch_flag = False
            ask_end_date_flag = True
        i += 1
    return cfg_path, batch_flag, ask_end_date_flag


def _coerce_float(value, default, min_value=None, max_value=None):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    if min_value is not None and out < min_value:
        out = min_value
    if max_value is not None and out > max_value:
        out = max_value
    return out


def _coerce_int(value, default, min_value=None, max_value=None):
    try:
        out = int(value)
    except (TypeError, ValueError):
        return default
    if min_value is not None and out < min_value:
        out = min_value
    if max_value is not None and out > max_value:
        out = max_value
    return out


def _validar_y_normalizar_config(config):
    """Sanea valores frecuentes de configuracion para evitar errores silenciosos."""
    cfg = config if isinstance(config, dict) else {}

    cfg["costes_transaccion"] = _coerce_float(
        cfg.get("costes_transaccion", 0.001), 0.001, min_value=0.0
    )
    cfg["execution_delay"] = _coerce_int(
        cfg.get("execution_delay", 1), 1, min_value=0
    )

    slippage = cfg.get("slippage", {})
    if not isinstance(slippage, dict):
        slippage = {}
    slippage["bps"] = _coerce_float(slippage.get("bps", 5.0), 5.0, min_value=0.0)
    slippage["atr_mult"] = _coerce_float(
        slippage.get("atr_mult", 0.0), 0.0, min_value=0.0
    )
    slippage["vol_mult"] = _coerce_float(
        slippage.get("vol_mult", 0.05), 0.05, min_value=0.0
    )
    cfg["slippage"] = slippage

    benchmarks = cfg.get("benchmarks", ["^IBEX"])
    if isinstance(benchmarks, str):
        benchmarks = [benchmarks]
    if not isinstance(benchmarks, list):
        benchmarks = ["^IBEX"]
    clean_benchmarks = []
    for b in benchmarks:
        if isinstance(b, str) and b.strip():
            clean_benchmarks.append(b.strip())
    cfg["benchmarks"] = list(dict.fromkeys(clean_benchmarks)) or ["^IBEX"]

    val_cfg = cfg.get("data_validation", {})
    if not isinstance(val_cfg, dict):
        val_cfg = {}
    val_cfg["min_rows_per_ticker"] = _coerce_int(
        val_cfg.get("min_rows_per_ticker", 252), 252, min_value=0
    )
    val_cfg["max_missing_close_pct"] = _coerce_float(
        val_cfg.get("max_missing_close_pct", 0.05), 0.05, min_value=0.0, max_value=1.0
    )
    val_cfg["max_zero_volume_pct"] = _coerce_float(
        val_cfg.get("max_zero_volume_pct", 0.5), 0.5, min_value=0.0, max_value=1.0
    )
    cfg["data_validation"] = val_cfg

    weights = cfg.get("pesos_estrategias", {})
    if not isinstance(weights, dict):
        weights = {}
    default_w = {"tendencia": 0.357, "bollinger": 0.272, "rsi": 0.240, "macd": 0.131}
    normalized = {}
    for k, dv in default_w.items():
        normalized[k] = _coerce_float(weights.get(k, dv), dv, min_value=0.0)
    total_w = sum(normalized.values())
    if total_w <= 0:
        normalized = default_w.copy()
        total_w = sum(normalized.values())
    cfg["pesos_estrategias"] = {k: v / total_w for k, v in normalized.items()}

    adv_cfg = cfg.get("analisis_avanzado", {})
    if not isinstance(adv_cfg, dict):
        adv_cfg = {}
    adv_cfg["max_tickers"] = _coerce_int(
        adv_cfg.get("max_tickers", 40), 40, min_value=1
    )
    bootstrap = adv_cfg.get("bootstrap", {})
    if not isinstance(bootstrap, dict):
        bootstrap = {}
    bootstrap["iters"] = _coerce_int(bootstrap.get("iters", 300), 300, min_value=10)
    bootstrap["seed"] = _coerce_int(bootstrap.get("seed", 42), 42, min_value=0)
    adv_cfg["bootstrap"] = bootstrap
    cfg["analisis_avanzado"] = adv_cfg

    cache_cfg = cfg.get("data_cache", {})
    if not isinstance(cache_cfg, dict):
        cache_cfg = {}
    cache_cfg["enabled"] = bool(cache_cfg.get("enabled", True))
    cache_cfg["force_refresh"] = bool(cache_cfg.get("force_refresh", False))
    cache_cfg["clear_on_start"] = bool(cache_cfg.get("clear_on_start", False))
    max_age = cache_cfg.get("max_age_days", None)
    if max_age in (None, "", False):
        cache_cfg["max_age_days"] = None
    else:
        cache_cfg["max_age_days"] = _coerce_int(max_age, 30, min_value=0)
    max_tickers_per_run = cache_cfg.get("max_tickers_per_run", None)
    if max_tickers_per_run in (None, "", False):
        cache_cfg["max_tickers_per_run"] = None
    else:
        cache_cfg["max_tickers_per_run"] = _coerce_int(
            max_tickers_per_run, 50, min_value=1
        )
    exclude_tickers = cache_cfg.get("exclude_tickers", [])
    if isinstance(exclude_tickers, str):
        exclude_tickers = [exclude_tickers]
    if not isinstance(exclude_tickers, list):
        exclude_tickers = []
    cleaned_excluded = []
    for t in exclude_tickers:
        if isinstance(t, str) and t.strip():
            cleaned_excluded.append(t.strip().upper())
    cache_cfg["exclude_tickers"] = list(dict.fromkeys(cleaned_excluded))
    cfg["data_cache"] = cache_cfg

    return cfg


def cargar_configuracion():
    default_config = {
        "batch_mode": False,
        "fecha_inicio_sistema": "2020-01-01",
        "fecha_fin": None,
        "ask_end_date": True,
        "runtime_limit_minutes": None,
        "heartbeat_seconds": 0,
        "data_quality_report": True,
        "data_validation": {
            "enabled": True,
            "min_rows_per_ticker": 252,
            "max_missing_close_pct": 0.05,
            "max_zero_volume_pct": 0.5,
        },
        "data_cache": {
            "enabled": True,
            "force_refresh": False,
            "clear_on_start": False,
            "max_age_days": None,
            "max_tickers_per_run": None,
            "exclude_tickers": [],
        },
        "export_results": {
            "enabled": True,
            "json": True,
            "parquet": True,
        },
        "signal_trace": {
            "enabled": True,
            "csv": True,
            "json": False,
        },
        "error_summary": {
            "enabled": True,
            "csv": True,
            "json": True,
        },
        "reproducibilidad": {
            "enabled": True,
            "seed": 42,
            "snapshot": True,
        },
        "benchmarks": ["^IBEX"],
        "performance": {
            "max_tickers": None,
            "max_runtime_minutes": None,
        },
        "costes_transaccion": 0.001,
        "execution_delay": 1,
        "slippage": {"bps": 5.0, "atr_mult": 0.0, "vol_mult": 0.05},
        "params": {
            "tendencia": {"short_window": 50, "long_window": 200},
            "bollinger": {"window": 30, "num_std_dev": 2},
            "rsi": {"window": 14, "umbral_compra": 30, "umbral_salida": 60},
            "macd": {"fast_period": 8, "slow_period": 20, "signal_period": 9},
        },
        "pesos_estrategias": {
            "tendencia": 0.357,
            "bollinger": 0.272,
            "rsi": 0.240,
            "macd": 0.131,
        },
        "analisis_avanzado": {
            "enable_walk_forward": True,
            "enable_sensitivity": True,
            "enable_stress_tests": True,
            "solo_cartera": False,
            "max_tickers": 40,
            "walk_forward": {
                "train_years": 3,
                "test_years": 1,
                "step_years": 1,
                "metric": "Ratio de Sharpe",
            },
            "sensitivity_metric": "Ratio de Sharpe",
            "bootstrap": {"iters": 300, "seed": 42},
        },
        "grid_parametros": {
            "tendencia": {"short_window": [20, 50, 80], "long_window": [100, 140, 200]},
            "bollinger": {"window": [20, 30, 40], "num_std_dev": [2.0, 2.5, 3.0]},
            "rsi": {
                "window": [10, 14, 20],
                "umbral_compra": [25, 30, 35],
                "umbral_salida": [50, 55, 60],
            },
            "macd": {"fast_period": [8, 12], "slow_period": [20, 26], "signal_period": [9]},
        },
    }

    cfg_path_cli, batch_flag, ask_end_date_flag = _parse_cli_flags(sys.argv[1:])
    default_cfg_path = str(Path(__file__).resolve().parents[1] / "config.json")
    cfg_path = cfg_path_cli or os.getenv("CONFIG_PATH") or default_cfg_path
    cfg = {}
    if os.path.exists(cfg_path):
        try:
            if cfg_path.lower().endswith((".yml", ".yaml")):
                try:
                    import yaml
                except Exception:
                    print("[AVISO] PyYAML no instalado; usar JSON o instalar PyYAML.")
                else:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = yaml.safe_load(f) or {}
            else:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            print(f"[CONFIG] Cargada configuracion desde: {cfg_path}")
        except Exception as e:
            print(f"[AVISO] No se pudo leer config '{cfg_path}': {e}")
    else:
        print(f"[CONFIG] No existe archivo de configuracion: {cfg_path} (usando defaults)")

    config = _deep_update(default_config, cfg if isinstance(cfg, dict) else {})
    if batch_flag is not None:
        config["batch_mode"] = batch_flag
    if ask_end_date_flag is not None:
        config["ask_end_date"] = ask_end_date_flag
    config = _validar_y_normalizar_config(config)
    return config


def _hard_kill_process(ppid, minutes):
    time.sleep(minutes * 60)
    try:
        os.system(f"taskkill /F /PID {ppid}")
    except Exception:
        pass


def _start_watchdog(config):
    start = time.time()
    limit_min = config.get("runtime_limit_minutes")
    heartbeat = config.get("heartbeat_seconds", 0)

    if not limit_min and not heartbeat:
        return None

    pid = os.getpid()
    print(f"[WATCHDOG] PID={pid} limite={limit_min}min heartbeat={heartbeat}s", flush=True)

    def _run():
        last_beat = 0.0
        while True:
            elapsed = time.time() - start
            if limit_min and elapsed > (limit_min * 60):
                print(
                    f"[WATCHDOG] Tiempo maximo excedido ({limit_min} min). Terminando proceso...",
                    flush=True,
                )
                os._exit(1)
            if heartbeat and (elapsed - last_beat) >= heartbeat:
                last_beat = elapsed
                print(f"[WATCHDOG] Ejecutando... {int(elapsed)}s", flush=True)
            time.sleep(1)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    if limit_min:
        p = multiprocessing.Process(target=_hard_kill_process, args=(pid, limit_min), daemon=True)
        p.start()
    return t

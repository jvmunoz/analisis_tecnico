import pandas as pd
import numpy as np
import yfinance as yf
import re
from pathlib import Path
import time


def _safe_cache_key(ticker):
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(ticker))


def _cache_paths(cache_dir, ticker):
    key = _safe_cache_key(ticker)
    return (
        cache_dir / f"{key}.parquet",
        cache_dir / f"{key}.csv",
    )


def _is_stale(path_obj, max_age_days):
    if max_age_days is None or not path_obj.exists():
        return False
    max_age_seconds = float(max_age_days) * 86400.0
    age_seconds = time.time() - path_obj.stat().st_mtime
    return age_seconds > max_age_seconds


def _read_cache(cache_dir, ticker, max_age_days=None):
    p_parquet, p_csv = _cache_paths(cache_dir, ticker)

    if _is_stale(p_parquet, max_age_days):
        try:
            p_parquet.unlink()
        except Exception:
            pass
    if _is_stale(p_csv, max_age_days):
        try:
            p_csv.unlink()
        except Exception:
            pass

    df = pd.DataFrame()
    if p_parquet.exists():
        try:
            df = pd.read_parquet(p_parquet)
        except Exception:
            df = pd.DataFrame()
    if df.empty and p_csv.exists():
        try:
            df = pd.read_csv(p_csv)
        except Exception:
            df = pd.DataFrame()
    if df.empty:
        return df
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
    return df


def _write_cache(cache_dir, ticker, df):
    if df is None or df.empty:
        return
    p_parquet, p_csv = _cache_paths(cache_dir, ticker)
    try:
        df.to_parquet(p_parquet, index=False)
    except Exception:
        try:
            df.to_csv(p_csv, index=False, encoding="utf-8")
        except Exception:
            pass


def _download_single_ticker(ticker, start_date, end_date):
    data = yf.download(
        ticker,
        start=start_date,
        end=end_date,
        auto_adjust=False,
        actions=True,
        progress=False,
    )
    if data is None or data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        level1 = data.columns.get_level_values(1).unique().tolist()
        sub_ticker = ticker if ticker in level1 else level1[0]
        data = data.xs(sub_ticker, axis=1, level=1, drop_level=True)

    try:
        close_safe = data["Close"].replace(0, np.nan)
        adj_factor = (
            (data["Adj Close"] / close_safe)
            .replace([np.inf, -np.inf], np.nan)
            .fillna(1.0)
        )
        data["Open"] *= adj_factor
        data["High"] *= adj_factor
        data["Low"] *= adj_factor
        data["Close"] = data["Adj Close"]
    except Exception:
        pass

    df = data.reset_index()
    df.columns = [str(c).lower() for c in df.columns]
    if "date" not in df.columns:
        for candidate in ("index", "datetime", "timestamp", "level_0"):
            if candidate in df.columns:
                df = df.rename(columns={candidate: "date"})
                break
    if "date" not in df.columns:
        return pd.DataFrame()
    df["ticker"] = ticker
    if "dividends" not in df.columns:
        df["dividends"] = 0.0
    else:
        df["dividends"] = df["dividends"].fillna(0.0)
    cols = ["date", "ticker"] + [c for c in df.columns if c not in ("date", "ticker")]
    return df[cols]


def limpiar_cache_mercado(cache_config=None):
    cache_cfg = cache_config if isinstance(cache_config, dict) else {}
    if not bool(cache_cfg.get("enabled", True)):
        return 0
    if not bool(cache_cfg.get("clear_on_start", False)):
        return 0

    cache_dir = Path(__file__).resolve().parents[1] / "cache" / "market_data"
    if not cache_dir.exists():
        return 0

    removed = 0
    for p in cache_dir.iterdir():
        if p.is_file() and p.suffix.lower() in (".parquet", ".csv"):
            try:
                p.unlink()
                removed += 1
            except Exception:
                pass
    return removed

def obtener_datos_historicos(
    tickers, start_date, end_date, cache_config=None, omitted_tickers_csv=None
):
    """
    Descarga y procesa datos histÃ³ricos.
    Usa auto_adjust=False para preservar la columna de dividendos y ajusta precios manualmente.
    """
    print(
        f"Descargando datos para {len(tickers)} ticker(s) desde {start_date} hasta {end_date}..."
    )
    cache_cfg = cache_config if isinstance(cache_config, dict) else {}
    cache_enabled = bool(cache_cfg.get("enabled", True))
    force_refresh = bool(cache_cfg.get("force_refresh", False))
    max_age_days = cache_cfg.get("max_age_days", None)
    if max_age_days in ("", False):
        max_age_days = None
    cache_dir = Path(__file__).resolve().parents[1] / "cache" / "market_data"
    cache_dir.mkdir(parents=True, exist_ok=True)
    start_ts = pd.to_datetime(start_date, errors="coerce")
    end_ts = pd.to_datetime(end_date, errors="coerce")
    if pd.isna(start_ts) or pd.isna(end_ts):
        print("Error: Rango de fechas invalido.")
        return None
    start_ts = start_ts.normalize()
    end_ts = end_ts.normalize()
    requested_end_ts = end_ts
    today_ts = pd.Timestamp.now().normalize()
    # Solo usar sesiones cerradas: hoy y futuro se recortan a ayer.
    if end_ts >= today_ts:
        end_ts = today_ts - pd.Timedelta(days=1)
        print(
            f"[DATOS] Fecha fin solicitada {requested_end_ts.date()} recortada a "
            f"{end_ts.date()} (ultima sesion cerrada)."
        )
    if start_ts > end_ts:
        print(f"Error: Rango de fechas invertido ({start_ts.date()} > {end_ts.date()}).")
        return None
    # yfinance usa `end` como limite exclusivo.
    end_download_ts = end_ts + pd.Timedelta(days=1)

    collected = []
    tickers_sin_datos = {}
    for i, ticker in enumerate(tickers):
        if i % 10 == 0 and i > 0:
            print(f"  Cache/descarga procesados {i}/{len(tickers)} ticker(s)...")

        df_cache = (
            _read_cache(cache_dir, ticker, max_age_days=max_age_days)
            if cache_enabled
            else pd.DataFrame()
        )
        first_cached = pd.NaT
        last_cached = pd.NaT
        if not df_cache.empty and "date" in df_cache.columns:
            cache_dates = pd.to_datetime(df_cache["date"], errors="coerce").dropna()
            if not cache_dates.empty:
                first_cached = cache_dates.min().normalize()
                last_cached = cache_dates.max().normalize()

        fetch_start_ts = start_ts
        if (
            cache_enabled
            and not force_refresh
            and not pd.isna(last_cached)
        ):
            fetch_start_ts = last_cached + pd.Timedelta(days=1)
        elif force_refresh:
            fetch_start_ts = start_ts

        df_backfill = pd.DataFrame()
        needs_backfill = (
            cache_enabled
            and not force_refresh
            and not pd.isna(first_cached)
            and first_cached > start_ts
        )
        if needs_backfill:
            backfill_start_ts = start_ts
            backfill_end_exclusive_ts = first_cached
            has_business_days_backfill = (
                np.busday_count(
                    backfill_start_ts.normalize().date(),
                    backfill_end_exclusive_ts.normalize().date(),
                )
                > 0
            )
            if has_business_days_backfill:
                df_backfill = _download_single_ticker(
                    ticker,
                    backfill_start_ts.strftime("%Y-%m-%d"),
                    backfill_end_exclusive_ts.strftime("%Y-%m-%d"),
                )
                if not df_backfill.empty:
                    print(
                        f"[CACHE] Backfill aplicado en {ticker}: "
                        f"{backfill_start_ts.date()} -> "
                        f"{(backfill_end_exclusive_ts - pd.Timedelta(days=1)).date()}"
                    )

        df_new = pd.DataFrame()
        # Evita la peticiÃ³n incremental hoy->hoy, que suele devolver vacÃ­o
        # y generar mensajes de "possibly delisted" en yfinance.
        only_today_window = (
            fetch_start_ts.normalize() == end_ts.normalize() == today_ts
        )
        # Evita peticiones en ventanas sin dias habiles (fines de semana),
        # que yfinance suele reportar como "possibly delisted".
        has_business_days = (
            np.busday_count(
                fetch_start_ts.normalize().date(),
                (end_ts + pd.Timedelta(days=1)).normalize().date(),
            )
            > 0
        )
        if fetch_start_ts <= end_ts and not only_today_window and has_business_days:
            df_new = _download_single_ticker(
                ticker,
                fetch_start_ts.strftime("%Y-%m-%d"),
                end_download_ts.strftime("%Y-%m-%d"),
            )

        if df_cache.empty and df_backfill.empty and df_new.empty:
            tickers_sin_datos[ticker] = "sin_descarga"
            continue

        if df_cache.empty and df_backfill.empty:
            df_all = df_new.copy()
        elif df_new.empty and df_backfill.empty:
            df_all = df_cache.copy()
        else:
            parts = [df_cache, df_backfill, df_new]
            df_all = pd.concat([p for p in parts if p is not None and not p.empty], ignore_index=True)

        if "date" in df_all.columns:
            df_all["date"] = pd.to_datetime(df_all["date"], errors="coerce")
            df_all = df_all.dropna(subset=["date"])
            df_all = (
                df_all.sort_values("date")
                .drop_duplicates(subset=["date"], keep="last")
                .reset_index(drop=True)
            )

        if cache_enabled:
            _write_cache(cache_dir, ticker, df_all)

        df_window = df_all[(df_all["date"] >= start_ts) & (df_all["date"] <= end_ts)].copy()
        if not df_window.empty:
            collected.append(df_window)
        else:
            tickers_sin_datos[ticker] = "fuera_de_ventana"

    if not collected:
        if tickers_sin_datos:
            print(
                "[DATOS] Sin datos para "
                f"{len(tickers_sin_datos)} ticker(s): {', '.join(list(tickers_sin_datos.keys())[:10])}"
                + (" ..." if len(tickers_sin_datos) > 10 else "")
            )
            if omitted_tickers_csv:
                try:
                    pd.DataFrame(
                        [
                            {
                                "ticker": t,
                                "motivo": m,
                                "fecha_inicio": str(start_ts.date()),
                                "fecha_fin": str(end_ts.date()),
                            }
                            for t, m in tickers_sin_datos.items()
                        ]
                    ).sort_values(["motivo", "ticker"]).to_csv(
                        omitted_tickers_csv, index=False, encoding="utf-8"
                    )
                    print(f"[DATOS] CSV de omitidos exportado: {omitted_tickers_csv}")
                except Exception as e:
                    print(f"[AVISO] No se pudo exportar CSV de omitidos: {e}")
        print("Error: No se pudieron descargar datos.")
        return None

    if tickers_sin_datos:
        print(
            "[DATOS] Tickers omitidos por falta de datos en la ventana solicitada: "
            f"{len(tickers_sin_datos)}"
        )
        if omitted_tickers_csv:
            try:
                pd.DataFrame(
                    [
                        {
                            "ticker": t,
                            "motivo": m,
                            "fecha_inicio": str(start_ts.date()),
                            "fecha_fin": str(end_ts.date()),
                        }
                        for t, m in tickers_sin_datos.items()
                    ]
                ).sort_values(["motivo", "ticker"]).to_csv(
                    omitted_tickers_csv, index=False, encoding="utf-8"
                )
                print(f"[DATOS] CSV de omitidos exportado: {omitted_tickers_csv}")
            except Exception as e:
                print(f"[AVISO] No se pudo exportar CSV de omitidos: {e}")

    df_final = pd.concat(collected, ignore_index=True)
    df_final.columns = [str(col).lower() for col in df_final.columns]
    # Si no hay dividendos en la descarga, crear columna vacÃ­a para evitar errores
    if "dividends" not in df_final.columns:
        df_final["dividends"] = 0.0
    else:
        df_final["dividends"] = df_final["dividends"].fillna(0.0)

    # --- MOTOR GENÃ‰RICO DE SANEAMIENTO DE DATOS (DetecciÃ³n de Splits HuÃ©rfanos) ---
    tickers_presentes = df_final["ticker"].unique()
    print(f"Saneando datos para {len(tickers_presentes)} tickers...")
    for i, t in enumerate(tickers_presentes):
        if i % 10 == 0 and i > 0:
            print(f"  Procesados {i}/{len(tickers_presentes)} tickers...")
        mask_ticker = df_final["ticker"] == t
        df_ticker = df_final[mask_ticker].sort_values(by=["date"])

        if "stock splits" in df_final.columns:
            if df_final.loc[mask_ticker, "stock splits"].fillna(0).sum() > 0:
                continue
        if "stock_splits" in df_final.columns:
            if df_final.loc[mask_ticker, "stock_splits"].fillna(0).sum() > 0:
                continue

        if len(df_ticker) < 2:
            continue

        # Calcular variaciones porcentuales diarias
        # Buscamos caÃ­das masivas (>50%) que se mantienen estables
        close_prices = df_ticker["close"].values
        if np.nanmedian(close_prices) < 1:
            continue
        pct_changes = df_ticker["close"].pct_change(fill_method=None).values

        # Encontrar el Ã­ndice de la caÃ­da mÃ¡s fuerte
        idx_drop = np.where(pct_changes < -0.50)[0]

        for idx in idx_drop:
            fecha_drop = df_ticker.iloc[idx]["date"]
            precio_pre = close_prices[idx - 1]
            precio_post = close_prices[idx]

            if precio_pre <= 0 or precio_post <= 0:
                continue

            # Verificar estabilidad: El precio post-caÃ­da no debe rebotar > 30% en los siguientes 5 dÃ­as
            # (esto descarta errores puntuales de un solo dÃ­a o flash crashes)
            lookforward = close_prices[idx : min(idx + 6, len(close_prices))]
            if len(lookforward) > 1:
                rebote = (np.max(lookforward) / precio_post) - 1
                if rebote < 0.30:
                    # Es probable que sea un split no ajustado.
                    # Estimamos el ratio (ej: 0.1 -> 10:1, 0.2 -> 5:1, 0.5 -> 2:1)
                    ratio_estimado = round(precio_pre / precio_post)
                    if ratio_estimado >= 2 and ratio_estimado <= 20:
                        print(
                            f"  [AVISO DATOS] AnomalÃ­a detectada en {t} el {fecha_drop.date()}."
                        )
                        print(
                            f"               Precio: {precio_pre:.2f} -> {precio_post:.2f} (Ratio ~{ratio_estimado}:1)"
                        )
                        print(f"               Aplicando normalizaciÃ³n automÃ¡tica...")

                        # Aplicar correcciÃ³n a todos los datos previos
                        mask_pre = (df_final["ticker"] == t) & (
                            df_final["date"] < fecha_drop
                        )
                        for col in ["open", "high", "low", "close"]:
                            if col in df_final.columns:
                                df_final.loc[mask_pre, col] = (
                                    df_final.loc[mask_pre, col] / ratio_estimado
                                )

    if "close" not in df_final.columns or "date" not in df_final.columns:
        print("Error: Las columnas 'close' o 'date' no se encontraron.")
        return None
    df_final = df_final.sort_values(by=["ticker", "date"])
    df_final["daily_return"] = df_final.groupby("ticker")["close"].pct_change(
        fill_method=None
    )
    df_final.dropna(subset=["daily_return"], inplace=True)
    print("Datos descargados y procesados con Ã©xito.")
    cols_order = [
        "ticker",
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "daily_return",
        "dividends",
    ]
    existing_cols = [col for col in cols_order if col in df_final.columns]
    return df_final[existing_cols]

def generar_reporte_calidad_datos(df, filename):
    if df is None or df.empty:
        return None

    rows = []
    for ticker, df_t in df.groupby("ticker"):
        df_t = df_t.sort_values(by="date")
        total = len(df_t)
        if total == 0:
            continue
        missing_close = df_t["close"].isna().mean()
        missing_volume = df_t["volume"].isna().mean() if "volume" in df_t.columns else 0
        zero_volume = (df_t["volume"] == 0).mean() if "volume" in df_t.columns else 0
        missing_div = df_t["dividends"].isna().mean() if "dividends" in df_t.columns else 0
        dup_dates = df_t["date"].duplicated().sum()
        start = df_t["date"].iloc[0]
        end = df_t["date"].iloc[-1]
        rows.append(
            {
                "ticker": ticker,
                "rows": total,
                "start": start,
                "end": end,
                "missing_close_pct": missing_close,
                "missing_volume_pct": missing_volume,
                "zero_volume_pct": zero_volume,
                "missing_dividends_pct": missing_div,
                "duplicate_dates": dup_dates,
            }
        )
    if not rows:
        return None
    report = pd.DataFrame(rows)
    report.to_csv(filename, index=False, encoding="utf-8")
    return report

def validar_datos(df, config, filename):
    if df is None or df.empty:
        return df, None

    cfg = config or {}
    min_rows = int(cfg.get("min_rows_per_ticker", 0) or 0)
    max_missing_close = float(cfg.get("max_missing_close_pct", 1) or 1)
    max_zero_volume = float(cfg.get("max_zero_volume_pct", 1) or 1)

    rows = []
    keep_tickers = []
    for ticker, df_t in df.groupby("ticker"):
        total = len(df_t)
        miss_close = df_t["close"].isna().mean()
        zero_vol = (
            (df_t["volume"] == 0).mean() if "volume" in df_t.columns else 0
        )
        reasons = []
        if total < min_rows:
            reasons.append(f"rows<{min_rows}")
        if miss_close > max_missing_close:
            reasons.append(f"missing_close>{max_missing_close:.2%}")
        if zero_vol > max_zero_volume:
            reasons.append(f"zero_volume>{max_zero_volume:.2%}")
        if not reasons:
            keep_tickers.append(ticker)
        rows.append(
            {
                "ticker": ticker,
                "rows": total,
                "missing_close_pct": miss_close,
                "zero_volume_pct": zero_vol,
                "status": "KEEP" if not reasons else "DROP",
                "reasons": ";".join(reasons),
            }
        )

    report = pd.DataFrame(rows)
    report.to_csv(filename, index=False, encoding="utf-8")
    filtered = df[df["ticker"].isin(keep_tickers)].copy()
    return filtered, report


# ==============================================================================
# FUNCIÃ“N AUXILIAR PARA MÃ‰TRICAS
# ==============================================================================



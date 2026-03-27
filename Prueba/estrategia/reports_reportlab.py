from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import pandas as pd
import numpy as np
import os
from datetime import datetime
from .utils import generar_conclusion_texto

def generar_pdf_detalles_estado(
    datos_completos_reporte, nombres_tickers={}, fecha_ult=""
):
    """
    Genera un PDF con una tabla detallada de métricas y estado para cada ticker usando ReportLab.
    Este informe migra de Matplotlib a ReportLab para mayor eficiencia de memoria.
    """
    suffix = f"_{fecha_ult.replace('-', '')}" if fecha_ult else ""
    filename = f"INFORME_DETALLADO_METRICAS{suffix}.pdf"
    print(f"\nGenerando informe detallado de métricas (ReportLab): {filename}...")

    doc = SimpleDocTemplate(filename, pagesize=landscape(A4))
    elements = []

    # Estilos
    styles = getSampleStyleSheet()
    style_title = styles["Title"]
    style_h2 = styles["Heading2"]
    style_normal = styles["Normal"]

    def fmt_num(val, decimals=2):
        if val is None:
            return "N/A"
        if isinstance(val, (float, np.floating)):
            if np.isnan(val):
                return "N/A"
            if np.isinf(val):
                return "Inf"
            return f"{val:.{decimals}f}"
        return str(val)

    def fmt_pct(val, decimals=2):
        if val is None:
            return "N/A"
        if isinstance(val, (float, np.floating)):
            if np.isnan(val):
                return "N/A"
            if np.isinf(val):
                return "Inf"
            return f"{val:.{decimals}%}"
        return str(val)

    def fmt_int(val):
        if val is None:
            return "N/A"
        if isinstance(val, (float, np.floating)):
            if np.isnan(val) or np.isinf(val):
                return "N/A"
            return str(int(round(val)))
        return str(val)

    def _metric_get(metricas_dict, key, default=None):
        if not isinstance(metricas_dict, dict):
            return default
        val = metricas_dict.get(key, None)
        if val not in (None, ""):
            return val
        try:
            key_mojibake = key.encode("utf-8").decode("latin-1")
            val = metricas_dict.get(key_mojibake, None)
            if val not in (None, ""):
                return val
        except Exception:
            pass
        return default

    for item in datos_completos_reporte:
        ticker = item["ticker"]
        nombre_empresa = nombres_tickers.get(ticker, "")
        metricas = item["metricas"]
        operaciones = item["operaciones"]
        df_viz = item.get("df_viz", None)

        # Título de Página
        title_text = f"Detalle de Rendimiento y Estado: {ticker} - {nombre_empresa}"
        if fecha_ult:
            title_text += f" (Datos hasta {fecha_ult})"
        elements.append(Paragraph(title_text, style_title))
        elements.append(Spacer(1, 10))

        # --- TABLA 1: MÉTRICAS DE RENDIMIENTO ---
        elements.append(Paragraph("<b>Métricas de Rendimiento Acumulado</b>", style_h2))
        elements.append(Spacer(1, 5))

        table_data_metrics = [
            ["Estrategia", "CAGR (Anual)", "Volatilidad", "Sharpe", "Max Drawdown"]
        ]

        strats = ["Mercado", "Tendencia", "Bollinger", "RSI", "MACD", "Combinada"]
        for s in strats:
            suffix_m = f"_{s}" if s != "Mercado" else ""
            cagr = _metric_get(
                metricas, f"CAGR{suffix_m}" if s != "Mercado" else "CAGR Mercado", 0
            )
            vol = _metric_get(
                metricas,
                f"Volatilidad{suffix_m}" if s != "Mercado" else "Volatilidad Mercado",
                0,
            )
            sha = _metric_get(
                metricas,
                f"Ratio de Sharpe{suffix_m}" if s != "Mercado" else "Sharpe Mercado",
                0,
            )
            mdd = _metric_get(
                metricas,
                f"Máximo Drawdown{suffix_m}"
                if s != "Mercado"
                else "Máximo Drawdown Mercado",
                0,
            )

            table_data_metrics.append(
                [s, f"{cagr:.2%}", f"{vol:.2%}", f"{sha:.2f}", f"{mdd:.2%}"]
            )

        t1 = Table(table_data_metrics, colWidths=[120, 100, 100, 100, 120])
        t1.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2F5597")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.whitesmoke, colors.HexColor("#D9E2F3")],
                    ),
                ]
            )
        )
        elements.append(t1)
        elements.append(Spacer(1, 15))

        # --- TABLA 1B: RIESGO AVANZADO ---
        elements.append(Paragraph("<b>Riesgo Avanzado y Cola</b>", style_h2))
        elements.append(Spacer(1, 5))

        table_data_risk = [
            [
                "Estrategia",
                "Sortino",
                "Calmar",
                "Ulcer",
                "VaR 95",
                "CVaR 95",
                "DD Max (d)",
            ]
        ]
        for s in strats:
            if s == "Mercado":
                sortino = _metric_get(metricas, "Ratio de Sortino Mercado", None)
                calmar = _metric_get(metricas, "Ratio de Calmar Mercado", None)
                ulcer = _metric_get(metricas, "Ulcer Index Mercado", None)
                var_95 = _metric_get(metricas, "VaR 95 Mercado", None)
                cvar_95 = _metric_get(metricas, "CVaR 95 Mercado", None)
                dd_dur = _metric_get(metricas, "Duración Drawdown Mercado", None)
            else:
                sortino = _metric_get(metricas, f"Ratio de Sortino_{s}", None)
                calmar = _metric_get(metricas, f"Ratio de Calmar_{s}", None)
                ulcer = _metric_get(metricas, f"Ulcer Index_{s}", None)
                var_95 = _metric_get(metricas, f"VaR 95_{s}", None)
                cvar_95 = _metric_get(metricas, f"CVaR 95_{s}", None)
                dd_dur = _metric_get(metricas, f"Duración Drawdown_{s}", None)

            table_data_risk.append(
                [
                    s,
                    fmt_num(sortino, 2),
                    fmt_num(calmar, 2),
                    fmt_pct(ulcer, 2),
                    fmt_pct(var_95, 2),
                    fmt_pct(cvar_95, 2),
                    fmt_int(dd_dur),
                ]
            )

        t1b = Table(table_data_risk, colWidths=[90, 70, 70, 70, 70, 70, 80])
        t1b.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.whitesmoke, colors.HexColor("#E4ECF7")],
                    ),
                ]
            )
        )
        elements.append(t1b)
        elements.append(Spacer(1, 15))

        # --- TABLA 1C: ESTADÍSTICAS DE TRADES ---
        elements.append(Paragraph("<b>Estadísticas de Trades</b>", style_h2))
        elements.append(Spacer(1, 5))

        table_data_trades = [
            [
                "Estrategia",
                "Trades",
                "Win %",
                "Profit Factor",
                "Expectancy",
                "Avg Win",
                "Avg Loss",
                "Time in Mkt",
            ]
        ]
        for s in strats:
            if s == "Mercado":
                trades = None
                win_rate = None
                profit_factor = None
                expectancy = None
                avg_win = None
                avg_loss = None
                time_in = None
            else:
                trades = _metric_get(metricas, f"Trades_{s}", None)
                win_rate = _metric_get(metricas, f"Win Rate_{s}", None)
                profit_factor = _metric_get(metricas, f"Profit Factor_{s}", None)
                expectancy = _metric_get(metricas, f"Expectancy_{s}", None)
                avg_win = _metric_get(metricas, f"Avg Win_{s}", None)
                avg_loss = _metric_get(metricas, f"Avg Loss_{s}", None)
                time_in = _metric_get(metricas, f"Time in Market_{s}", None)

            table_data_trades.append(
                [
                    s,
                    fmt_int(trades),
                    fmt_pct(win_rate, 1),
                    fmt_num(profit_factor, 2),
                    fmt_pct(expectancy, 2),
                    fmt_pct(avg_win, 2),
                    fmt_pct(avg_loss, 2),
                    fmt_pct(time_in, 1),
                ]
            )

        t1c = Table(table_data_trades, colWidths=[90, 55, 60, 80, 75, 70, 70, 70])
        t1c.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#355C7D")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.whitesmoke, colors.HexColor("#EDF2F9")],
                    ),
                ]
            )
        )
        elements.append(t1c)
        elements.append(Spacer(1, 20))

        # --- TABLA 2: ESTADO Y ÚLTIMAS OPERACIONES ---
        elements.append(
            Paragraph("<b>Estado Actual y Últimas Operaciones</b>", style_h2)
        )
        elements.append(Spacer(1, 5))

        table_data_ops = [
            [
                "Estrategia",
                "Estado",
                "Entrada",
                "Salida",
                "Pr. Ent.",
                "Pr. Sal.",
                "CAGR",
                "Ret. Tot.",
                "Días",
            ]
        ]

        for op in operaciones:
            rendimiento_periodo = "N/A"
            retorno_total_periodo = "N/A"
            dias_periodo = "N/A"
            precio_entrada = "N/A"
            precio_salida = "N/A"

            if df_viz is not None:
                try:
                    entrada = op.get("Ultima Entrada") or op.get("Última Entrada", "N/A")
                    salida = op.get("Ultima Salida") or op.get("Última Salida", "N/A")
                    estado = op.get("Estado", "Inactivo")
                    strat = op.get("Estrategia", "")

                    if entrada != "N/A":
                        fecha_inicio = pd.to_datetime(entrada)
                        fecha_fin = (
                            df_viz.index[-1]
                            if estado == "Activo"
                            else pd.to_datetime(salida)
                            if salida != "N/A"
                            else None
                        )

                        if fecha_inicio and fecha_fin:
                            mask = (df_viz.index >= fecha_inicio) & (
                                df_viz.index <= fecha_fin
                            )
                            periodo_df = df_viz[mask]
                            if not periodo_df.empty:
                                precio_entrada = f"{periodo_df['close'].iloc[0]:.2f}€"
                                precio_salida = f"{periodo_df['close'].iloc[-1]:.2f}€"
                                col_cumret = f"{strat.lower()}_cumulative_return"
                                if col_cumret in periodo_df.columns:
                                    retorno_total = (
                                        periodo_df[col_cumret].iloc[-1]
                                        / periodo_df[col_cumret].iloc[0]
                                    ) - 1
                                    dias = (fecha_fin - fecha_inicio).days
                                    retorno_total_periodo = f"{retorno_total:.2%}"
                                    dias_periodo = str(dias)
                                    if dias > 0:
                                        years = dias / 365.25
                                        cagr_periodo = (1 + retorno_total) ** (
                                            1 / years
                                        ) - 1
                                        rendimiento_periodo = f"{cagr_periodo:.2%}"
                except:
                    rendimiento_periodo = "Err"

            table_data_ops.append(
                [
                    op["Estrategia"],
                    op["Estado"],
                    op.get("Ultima Entrada") or op.get("Última Entrada", "N/A"),
                    op.get("Ultima Salida") or op.get("Última Salida", "N/A"),
                    precio_entrada,
                    precio_salida,
                    rendimiento_periodo,
                    retorno_total_periodo,
                    dias_periodo,
                ]
            )

        t2 = Table(table_data_ops, colWidths=[80, 70, 75, 75, 65, 65, 60, 70, 50])
        t2.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("FONTSIZE", (0, 1), (-1, -1), 7),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.whitesmoke, colors.HexColor("#E7EFEF")],
                    ),
                ]
            )
        )
        elements.append(t2)

        # --- CONCLUSIONES AUTOMÁTICAS ---
        elements.append(Spacer(1, 15))
        elements.append(
            Paragraph("<b>CONCLUSIONES Y ANÁLISIS AUTOMÁTICO</b>", style_h2)
        )
        elements.append(Spacer(1, 5))

        texto_conclusiones = generar_conclusion_texto(metricas)
        # Usamos un marco/borde para resaltar
        style_concl = ParagraphStyle(
            "Concl",
            parent=style_normal,
            backColor=colors.whitesmoke,
            borderColor=colors.grey,
            borderWidth=0.5,
            borderPadding=5,
            leading=12,
        )
        elements.append(Paragraph(texto_conclusiones, style_concl))

        elements.append(PageBreak())

    try:
        doc.build(elements)
        print(f"Informe {filename} generado con éxito.")
    except Exception as e:
        print(f"Error al generar {filename}: {e}")

def generar_informe_cartera_pdf(
    data_enriquecida, df_cartera, lista_datos_completos, df_log_completo, fecha_ult=""
):
    """
    Genera un PDF con el P&L detallado de la cartera personal del usuario, incluyendo dividendos.
    """
    filename = f"INFORME_MI_CARTERA_{fecha_ult.replace('-', '')}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    style_title = styles["Title"]
    style_normal = styles["Normal"]

    elements.append(
        Paragraph(f"Informe de Cartera Personal - {fecha_ult}", style_title)
    )
    elements.append(Spacer(1, 20))

    if df_cartera.empty:
        elements.append(
            Paragraph("No hay posiciones activas en cartera.", style_normal)
        )
        doc.build(elements)
        return

    if df_log_completo is None:
        df_log_completo = pd.DataFrame()
    else:
        req_log_cols = {"Ticker", "Tipo", "Cantidad", "Fecha"}
        if not req_log_cols.issubset(df_log_completo.columns):
            df_log_completo = pd.DataFrame()

    # Extraer precios actuales y estados de la data_enriquecida
    precios_actuales = {item["Ticker"]: item["Precio"] for item in data_enriquecida}
    estados_tecnicos = {item["Ticker"]: item["Semaforo"] for item in data_enriquecida}

    # Mapeo de datos históricos para dividendos
    dict_historicos = {item["ticker"]: item["df_viz"] for item in lista_datos_completos}

    total_inversion = 0
    total_valor_actual = 0
    total_dividendos_global = 0

    table_data = [
        [
            "Ticker",
            "Cantidad",
            "Precio Media",
            "Precio Actual",
            "Val. Mer.",
            "Div. Cobr.",
            "P&L (%)",
            "P&L (€)",
            "Semáforo",
        ]
    ]

    for _, row in df_cartera.iterrows():
        ticker = row["Ticker"]
        cantidad = row["Cantidad"]
        precio_medio = row["Precio_Medio"]

        precio_actual = precios_actuales.get(ticker, 0)
        semaforo = estados_tecnicos.get(ticker, "N/A")

        # --- CÁLCULO DE DIVIDENDOS ---
        div_coyurados = 0
        if ticker in dict_historicos and not df_log_completo.empty:
            df_hist_t = dict_historicos[ticker]
            if "dividends" in df_hist_t.columns:
                # Filtrar log de este ticker
                df_log_t = df_log_completo[
                    df_log_completo["Ticker"] == ticker
                ].sort_values("Fecha")
                df_div_t = df_hist_t[df_hist_t["dividends"] > 0].copy()

                # Para cada dividendo pagado, ¿cuántas acciones teníamos?
                for _, d_row in df_div_t.iterrows():
                    # Asegurar que d_fecha es naive para comparar con el log
                    d_fecha = d_row.name
                    if hasattr(d_fecha, "tzinfo") and d_fecha.tzinfo is not None:
                        d_fecha = d_fecha.replace(tzinfo=None)

                    # Calcular posicion neta en esa fecha d_fecha
                    df_pre = df_log_t[df_log_t["Fecha"] <= d_fecha]
                    pos_en_fecha = (
                        df_pre[df_pre["Tipo"] == "COMPRA"]["Cantidad"].sum()
                        - df_pre[df_pre["Tipo"] == "VENTA"]["Cantidad"].sum()
                    )
                    if pos_en_fecha > 0:
                        div_val = d_row["dividends"]
                        div_coyurados += pos_en_fecha * div_val
                        # print(f"    - Div capturado el {d_fecha.date()}: {pos_en_fecha} x {div_val:.4f}")
        # -----------------------------

        inversion = cantidad * precio_medio
        valor_actual = cantidad * precio_actual

        total_inversion += inversion
        total_valor_actual += valor_actual
        total_dividendos_global += div_coyurados

        pnl_euros = (valor_actual - inversion) + div_coyurados
        pnl_pct = (pnl_euros / inversion) if inversion > 0 else 0

        table_data.append(
            [
                ticker,
                f"{cantidad:.0f}",
                f"{precio_medio:.3f}",
                f"{precio_actual:.3f}",
                f"{valor_actual:,.2f}€",
                f"{div_coyurados:.2f}€",
                f"{pnl_pct:.2%}",
                f"{pnl_euros:.2f}€",
                semaforo,
            ]
        )

    pnl_total = (total_valor_actual - total_inversion) + total_dividendos_global
    pnl_total_pct = (pnl_total / total_inversion) if total_inversion > 0 else 0

    elements.append(
        Paragraph(f"<b>Inversión Activa:</b> {total_inversion:,.2f}€", style_normal)
    )
    elements.append(
        Paragraph(f"<b>Valor Mercado:</b> {total_valor_actual:,.2f}€", style_normal)
    )
    elements.append(
        Paragraph(
            f"<b>Total Dividendos Cobrados (Cash):</b> {total_dividendos_global:,.2f}€",
            style_normal,
        )
    )

    color_pnl = "green" if pnl_total >= 0 else "red"
    elements.append(
        Paragraph(
            f"<b>P&amp;L Global (Incl. Div.):</b> <font color='{color_pnl}'>{pnl_total:,.2f}€ ({pnl_total_pct:.2%})</font>",
            style_normal,
        )
    )
    elements.append(Spacer(1, 20))

    t = Table(table_data)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E2F3")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )

    # Colorear P&L individual (Índice 6 y 7 son P&L % y P&L € ahora)
    for i in range(1, len(table_data)):
        val_str = table_data[i][6]
        try:
            val = float(val_str.replace("%", ""))
            c = colors.green if val >= 0 else colors.red
            t.setStyle(TableStyle([("TEXTCOLOR", (6, i), (7, i), c)]))
        except:
            pass

    elements.append(t)
    doc.build(elements)
    print(f"Informe de Cartera generado: {filename} (Dividendos incorporados)")

def generar_pdfs_enriquecidos_reportlab(data_enriquecida, fecha_ult="", **kwargs):
    """
    Genera los dos PDFs específicos solicitados por el usuario usando ReportLab.
    """
    fecha_str = fecha_ult if fecha_ult else datetime.now().strftime("%Y-%m-%d")

    # --- PDF 1: ANÁLISIS TÉCNICO COMPLETO ---
    pdf1_name = (
        f"Analisis_tecnico_tabla_completa_enriquecido_{fecha_str.replace('-', '')}.pdf"
    )
    print(f"Generando {pdf1_name}...")
    doc1 = SimpleDocTemplate(pdf1_name, pagesize=landscape(A4))
    elements1 = []
    styles = getSampleStyleSheet()

    # Estilos Personalizados
    style_title = ParagraphStyle(
        "TitleStyle", parent=styles["Title"], fontSize=24, spaceAfter=20
    )
    style_h2 = ParagraphStyle(
        "H2Style", parent=styles["Heading2"], fontSize=16, spaceAfter=10
    )
    style_normal = styles["Normal"]

    elements1.append(
        Paragraph("Informe técnico - Tabla completa con niveles teóricos", style_title)
    )
    elements1.append(
        Paragraph(f"(Breakout/Pullback) | Datos hasta {fecha_str}", style_h2)
    )
    elements1.append(Spacer(1, 10))

    # Definiciones
    elements1.append(Paragraph("<b>Definiciones:</b>", style_normal))
    elements1.append(
        Paragraph("- Breakout: Superación de resistencias con momentum.", style_normal)
    )
    elements1.append(
        Paragraph(
            "- Pullback: Aprovechamiento de retrocesos a soportes en tendencia alcista.",
            style_normal,
        )
    )
    elements1.append(Spacer(1, 15))

    # Tabla A: Niveles
    # Ordenar: Verdes primero, luego Amarillo, luego Rojo. Por Score Desc.
    data_enriquecida.sort(
        key=lambda x: (
            x["Semaforo"] != "VERDE",
            x["Semaforo"] != "AMARILLO",
            -x["Score"],
        )
    )

    table_data = [
        [
            "Ticker",
            "Pr. Actual",
            "Semáforo",
            "Estado",
            "Setup",
            "Score",
            "Entrada",
            "Stop",
            "T1",
            "T2",
            "Stop Seg.",
        ]
    ]
    portfolio_tickers = kwargs.get("portfolio_tickers", [])
    for item in data_enriquecida:
        ticker_display = item["Ticker"]
        if ticker_display in portfolio_tickers:
            ticker_display = f"{ticker_display} [C]"

        table_data.append(
            [
                ticker_display,
                item["Precio"],
                item["Semaforo"],
                item["Estado"],
                item["Setup"],
                item["Score"],
                item["Entrada"],
                item["Stop"],
                item["T1"],
                item["T2"],
                item["Trailing_Stop"],
            ]
        )

    t1 = Table(table_data, colWidths=[60, 50, 60, 70, 60, 35, 55, 55, 55, 55, 60])
    ts1 = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E2F3")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C9D3E1")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]
    )

    # Colores Semáforo
    for i, item in enumerate(data_enriquecida):
        c = colors.white
        if item["Semaforo"] == "VERDE":
            c = colors.HexColor("#C6EFCE")
        elif item["Semaforo"] == "AMARILLO":
            c = colors.HexColor("#FFF2CC")
        elif item["Semaforo"] == "ROJO":
            c = colors.HexColor("#F8CBAD")
        ts1.add("BACKGROUND", (2, i + 1), (2, i + 1), c)

    t1.setStyle(ts1)
    elements1.append(t1)
    # SECCION DE ALERTAS (ENTRADA y SALIDA)
    entry_alerts = []
    exit_alerts = []
    seen_entry = set()
    seen_exit = set()

    def _push_unique(container, seen, ticker, tipo, motivo):
        key = (ticker, tipo, motivo)
        if key not in seen:
            seen.add(key)
            container.append([ticker, tipo, motivo])

    for item in data_enriquecida:
        ticker = item["Ticker"]
        p = item["Precio"]
        entrada = item["Entrada"]
        t1 = item["T1"]
        t2 = item["T2"]

        # Alertas de Entrada
        if item["Semaforo"] == "VERDE" and item["Estado"] == "EJECUTAR":
            _push_unique(
                entry_alerts,
                seen_entry,
                ticker,
                "COMPRA (Setup)",
                "Semaforo Verde / Estado EJECUTAR",
            )
        if entrada > 0 and abs(p / entrada - 1) <= 0.01:
            _push_unique(
                entry_alerts,
                seen_entry,
                ticker,
                "VIGILANCIA (Entrada)",
                f"Precio {p} cerca de Entrada ({entrada})",
            )

        # Alertas de Salida
        if item["Semaforo"] == "ROJO":
            _push_unique(
                exit_alerts,
                seen_exit,
                ticker,
                "VENTA (Deterioro)",
                "Semaforo Rojo / Tendencia Bajista",
            )
        if t1 > 0 and abs(p / t1 - 1) <= 0.01:
            _push_unique(
                exit_alerts,
                seen_exit,
                ticker,
                "VIGILANCIA (T1)",
                f"Precio {p} cerca de Objetivo 1 ({t1})",
            )
        elif t2 > 0 and abs(p / t2 - 1) <= 0.01:
            _push_unique(
                exit_alerts,
                seen_exit,
                ticker,
                "VIGILANCIA (T2)",
                f"Precio {p} cerca de Objetivo 2 ({t2})",
            )

    if entry_alerts:
        elements1.append(Spacer(1, 20))
        elements1.append(Paragraph("Alertas de Entrada / Oportunidad", style_h2))
        elements1.append(
            Paragraph(
                "Activos con condiciones tecnicas de entrada favorables o cercanos al nivel de entrada.",
                style_normal,
            )
        )
        elements1.append(Spacer(1, 5))

        entry_table_data = [["Ticker", "Tipo Alerta", "Motivo"]]
        entry_table_data.extend(entry_alerts)

        et = Table(entry_table_data, colWidths=[100, 150, 250])
        et.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAD3")),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        elements1.append(et)

    if exit_alerts:
        elements1.append(Spacer(1, 20))
        elements1.append(Paragraph("Alertas de Salida / Vigilancia Estrecha", style_h2))
        elements1.append(
            Paragraph(
                "Se recomienda revisar los siguientes activos para posible cierre total o parcial de la posicion.",
                style_normal,
            )
        )
        elements1.append(Spacer(1, 5))

        exit_table_data = [["Ticker", "Tipo Alerta", "Motivo"]]
        exit_table_data.extend(exit_alerts)

        at = Table(exit_table_data, colWidths=[100, 150, 250])
        at.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFCCCC")),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        elements1.append(at)

    # NUEVA SECCIÓN: CORRELACIONES PELIGROSAS
    if "alertas_corr" in kwargs and kwargs["alertas_corr"]:
        elements1.append(Spacer(1, 30))
        elements1.append(
            Paragraph("Advertencia de Correlación (Riesgo de Concentración)", style_h2)
        )
        elements1.append(
            Paragraph(
                "Los siguientes activos tienen una correlación > 0.85. Se recomienda no entrar en ambos simultáneamente para evitar duplicar el riesgo.",
                style_normal,
            )
        )
        elements1.append(Spacer(1, 10))

        corr_data = [["Activo 1", "Activo 2", "Correlación"]]
        for a in kwargs["alertas_corr"]:
            corr_data.append([a["T1"], a["T2"], str(a["Corr"])])

        ct = Table(corr_data, colWidths=[100, 100, 100])
        ct.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFF2CC")),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )
        elements1.append(ct)

    doc1.build(elements1)

    # --- PDF 2: ASIGNACIÓN POR RIESGO (80/20) ---
    pdf2_name = f"Asignacion_por_riesgo_enriquecido_{fecha_str.replace('-', '')}.pdf"
    print(f"Generando {pdf2_name}...")
    doc2 = SimpleDocTemplate(pdf2_name, pagesize=A4)
    elements2 = []

    elements2.append(
        Paragraph("Asignación porcentual por riesgo – Valores ejecutables", style_title)
    )

    # Mostrar Salud del Mercado
    if "breadth" in kwargs:
        breadth_val, exposure_val = kwargs["breadth"]
        b_color = (
            "green" if breadth_val > 60 else "orange" if breadth_val >= 40 else "red"
        )
        elements2.append(
            Paragraph(
                f"<b>Salud del Mercado IBEX (Amplitud):</b> <font color='{b_color}'>{breadth_val}%</font> de valores sobre SMA200.",
                style_normal,
            )
        )
        elements2.append(
            Paragraph(
                f"<b>Exposición Recomendada:</b> {exposure_val}% del capital.",
                style_normal,
            )
        )
        elements2.append(Spacer(1, 10))

    elements2.append(
        Paragraph(
            f"Perfil de Riesgo Dinámico: {kwargs.get('exposure', 80.0)}% Inversión / {100.0 - kwargs.get('exposure', 80.0)}% Cash | {fecha_str}",
            style_h2,
        )
    )

    ejecutables = [d for d in data_enriquecida if d["Estado"] == "EJECUTAR"]

    table_data2 = [
        [
            "Ticker",
            "Setup",
            "Entrada",
            "Stop",
            "Distancia %",
            "Peso Op1 (80%)",
            "Peso Op2 (Cap Banca)",
        ]
    ]
    for item in ejecutables:
        table_data2.append(
            [
                item["Ticker"],
                item["Setup"],
                item["Entrada"],
                item["Stop"],
                f"{item['Distancia_stop_pct']}%",
                f"{item['Opción1_W']}%",
                f"{item['Opción2_W']}%",
            ]
        )
    table_data2.append(["CASH", "-", "-", "-", "-", "20.0%", "20.0%"])

    t2 = Table(table_data2, colWidths=[70, 70, 60, 60, 70, 80, 100])
    ts2 = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E2F3")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FFF2E5")),  # Fila Cash
            ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#9C3A2E")),
        ]
    )
    t2.setStyle(ts2)
    elements2.append(t2)

    elements2.append(Spacer(1, 30))
    elements2.append(Paragraph("<b>Nota Metodológica:</b>", style_normal))
    elements2.append(
        Paragraph(
            "- Opción 1: Reparto por paridad de riesgo sobre el 80% del capital.",
            style_normal,
        )
    )
    elements2.append(
        Paragraph(
            "- Opción 2: Limita el sector bancario a un máximo del 25% del total de la cartera.",
            style_normal,
        )
    )

    # NUEVO: Insertar Heatmap al final
    if "heatmap" in kwargs and os.path.exists(kwargs["heatmap"]):
        elements2.append(PageBreak())
        elements2.append(
            Paragraph("Estado Macro: Mapa de Calor Sectorial IBEX 35", style_title)
        )
        elements2.append(Spacer(1, 20))
        # Ajustar tamaño de imagen para que quepa bien en A4 horizontal
        img = Image(kwargs["heatmap"], width=9 * inch, height=5 * inch)
        elements2.append(img)
        elements2.append(Spacer(1, 10))
        elements2.append(
            Paragraph(
                "El color indica la salud técnica: Verde (Alcista), Amarillo (Vigilar), Rojo (Deterioro).",
                style_normal,
            )
        )

    doc2.build(elements2)
    print("Reportes enriquecidos generados con éxito.")



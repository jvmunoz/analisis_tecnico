import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import textwrap

from .ibex import SECTORES_IBEX
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def crear_informe_pdf(
    resultados_por_ticker,
    pesos_estrategias,
    nombres_tickers={},
    is_aggregated=False,
    fecha_ult="",
):
    """Genera un PDF con una página A4 HORIZONTAL por ticker o para el agregado."""
    suffix = f"_{fecha_ult.replace('-', '')}" if fecha_ult else ""
    filename = (
        f"{'INFORME_AGREGADO' if is_aggregated else 'INFORME_INDIVIDUAL'}{suffix}.pdf"
    )

    print(f"\nGenerando informe PDF: {filename}...")
    with PdfPages(filename) as pdf:
        for ticker, data in resultados_por_ticker.items():
            try:
                df_viz = data["dataframe"]
                metricas = data["metricas"]
                nombre_empresa = nombres_tickers.get(ticker, "")

                fig = plt.figure(figsize=(10, 7), dpi=72)
                title = f"Análisis de Estrategia: {ticker} - {nombre_empresa}"
                if fecha_ult:
                    title += f" (Datos hasta {fecha_ult})"
                fig.suptitle(title, fontsize=16, y=0.95)

                safe_ticker_name = ticker.replace(".", "_").replace("^", "INDEX")

                ax_price = None
                if is_aggregated or "INDEX" in safe_ticker_name:
                    gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1.2])
                    ax_equity = fig.add_subplot(gs[0, 0])
                    ax_table = fig.add_subplot(gs[1, 0])
                else:
                    gs = gridspec.GridSpec(3, 1, height_ratios=[3, 2, 1.3])
                    ax_price = fig.add_subplot(gs[0, 0])
                    ax_equity = fig.add_subplot(gs[1, 0], sharex=ax_price)
                    ax_table = fig.add_subplot(gs[2, 0])

                df_viz = data["dataframe"]
                metricas = data["metricas"]

                if not is_aggregated and "INDEX" not in safe_ticker_name:
                    ax_price.fill_between(
                        df_viz.index,
                        df_viz["banda_inferior"],
                        df_viz["banda_superior"],
                        color="lightblue",
                        alpha=0.4,
                        label="Canal Bollinger",
                    )
                    ax_price.plot(
                        df_viz.index,
                        df_viz["close"],
                        label="Precio",
                        color="black",
                        alpha=0.7,
                        linewidth=1.5,
                    )
                    ax_price.plot(
                        df_viz.index,
                        df_viz["sma_short"],
                        label="SMA Rápida (T)",
                        color="orange",
                        linestyle="--",
                        alpha=0.9,
                    )
                    ax_price.plot(
                        df_viz.index,
                        df_viz["sma_long"],
                        label="SMA Lenta (T)",
                        color="purple",
                        linestyle="--",
                        alpha=0.9,
                    )
                    ax_price.plot(
                        df_viz[df_viz["position_tendencia"] == 1.0].index,
                        df_viz["sma_short"][df_viz["position_tendencia"] == 1.0],
                        "^",
                        markersize=8,
                        color="green",
                        label="Compra T",
                    )
                    ax_price.plot(
                        df_viz[df_viz["position_tendencia"] == -1.0].index,
                        df_viz["sma_short"][df_viz["position_tendencia"] == -1.0],
                        "v",
                        markersize=8,
                        color="red",
                        label="Venta T",
                    )
                    ax_price.plot(
                        df_viz[df_viz["position_bollinger"] == 1.0].index,
                        df_viz["banda_inferior"][df_viz["position_bollinger"] == 1.0],
                        "o",
                        markersize=8,
                        color="green",
                        label="Compra B",
                        alpha=0.8,
                    )
                    ax_price.plot(
                        df_viz[df_viz["position_bollinger"] == -1.0].index,
                        df_viz["sma_bollinger"][df_viz["position_bollinger"] == -1.0],
                        "o",
                        markersize=8,
                        color="red",
                        label="Venta B",
                    )
                    ax_price.plot(
                        df_viz[df_viz["position_rsi"] == 1.0].index,
                        df_viz["close"][df_viz["position_rsi"] == 1.0] * 0.98,
                        "s",
                        markersize=7,
                        color="green",
                        label="Compra RSI",
                        alpha=0.9,
                    )
                    ax_price.plot(
                        df_viz[df_viz["position_rsi"] == -1.0].index,
                        df_viz["close"][df_viz["position_rsi"] == -1.0] * 1.02,
                        "s",
                        markersize=7,
                        color="red",
                        label="Venta RSI",
                        alpha=0.9,
                    )
                    ax_price.plot(
                        df_viz[df_viz["position_macd"] == 1.0].index,
                        df_viz["close"][df_viz["position_macd"] == 1.0] * 0.96,
                        "d",
                        markersize=7,
                        color="green",
                        label="Compra MACD",
                        alpha=0.9,
                    )
                    ax_price.plot(
                        df_viz[df_viz["position_macd"] == -1.0].index,
                        df_viz["close"][df_viz["position_macd"] == -1.0] * 1.04,
                        "d",
                        markersize=7,
                        color="red",
                        label="Venta MACD",
                        alpha=0.9,
                    )
                    ax_price.set_ylabel("Precio")
                    ax_price.legend(loc="upper left", fontsize=7, ncol=5)
                    ax_price.grid(True)
                    plt.setp(ax_price.get_xticklabels(), visible=False)

                label_combinada = f"Combinada ({pesos_estrategias['tendencia'] * 100:.0f}/{pesos_estrategias['bollinger'] * 100:.0f}/{pesos_estrategias['rsi'] * 100:.0f}/{pesos_estrategias['macd'] * 100:.0f})"
                ax_equity.plot(
                    df_viz.index,
                    df_viz["market_cumulative_return"],
                    label="Mercado",
                    color="gray",
                    linewidth=1.5,
                )
                ax_equity.plot(
                    df_viz.index,
                    df_viz["tendencia_cumulative_return"],
                    label="Tendencia",
                    linewidth=1.5,
                )
                ax_equity.plot(
                    df_viz.index,
                    df_viz["bollinger_cumulative_return"],
                    label="Bollinger",
                    linewidth=1.5,
                )
                ax_equity.plot(
                    df_viz.index,
                    df_viz["rsi_cumulative_return"],
                    label="RSI",
                    linewidth=1.5,
                )
                ax_equity.plot(
                    df_viz.index,
                    df_viz["macd_cumulative_return"],
                    label="MACD",
                    linewidth=1.5,
                    linestyle="--",
                )
                ax_equity.plot(
                    df_viz.index,
                    df_viz["combinada_cumulative_return"],
                    label=label_combinada,
                    color="black",
                    linewidth=2.0,
                    linestyle="-",
                )
                ax_equity.set_ylabel("Rendimiento Acumulado")
                ax_equity.set_xlabel("Fecha")
                ax_equity.legend(loc="upper left", fontsize=8)
                ax_equity.grid(True)

                ax_table.axis("off")

                def get_m(k, fmt=".2%"):
                    val = metricas.get(k, None)
                    if val in (None, ""):
                        try:
                            k_mojibake = k.encode("utf-8").decode("latin-1")
                            val = metricas.get(k_mojibake, None)
                        except Exception:
                            pass
                    if val in (None, ""):
                        val = 0
                    if val is None or (isinstance(val, float) and np.isnan(val)):
                        val = 0
                    try:
                        return f"{val:{fmt}}"
                    except:
                        return "0.00"

                table_data = [
                    [
                        get_m("CAGR Mercado"),
                        get_m("CAGR_Tendencia"),
                        get_m("CAGR_Bollinger"),
                        get_m("CAGR_RSI"),
                        get_m("CAGR_MACD"),
                        get_m("CAGR_Combinada"),
                    ],
                    [
                        get_m("Volatilidad Mercado"),
                        get_m("Volatilidad_Tendencia"),
                        get_m("Volatilidad_Bollinger"),
                        get_m("Volatilidad_RSI"),
                        get_m("Volatilidad_MACD"),
                        get_m("Volatilidad_Combinada"),
                    ],
                    [
                        get_m("Sharpe Mercado", ".2f"),
                        get_m("Ratio de Sharpe_Tendencia", ".2f"),
                        get_m("Ratio de Sharpe_Bollinger", ".2f"),
                        get_m("Ratio de Sharpe_RSI", ".2f"),
                        get_m("Ratio de Sharpe_MACD", ".2f"),
                        get_m("Ratio de Sharpe_Combinada", ".2f"),
                    ],
                    [
                        get_m("Máximo Drawdown Mercado"),
                        get_m("Máximo Drawdown_Tendencia"),
                        get_m("Máximo Drawdown_Bollinger"),
                        get_m("Máximo Drawdown_RSI"),
                        get_m("Máximo Drawdown_MACD"),
                        get_m("Máximo Drawdown_Combinada"),
                    ],
                ]
                col_labels = [
                    "Mercado",
                    "Tendencia",
                    "Bollinger",
                    "RSI",
                    "MACD",
                    "Combinada",
                ]
                row_labels = ["CAGR", "Volatilidad", "Sharpe", "Max Drawdown"]
                table = ax_table.table(
                    cellText=table_data,
                    rowLabels=row_labels,
                    colLabels=col_labels,
                    cellLoc="center",
                    loc="center",
                )
                table.auto_set_font_size(False)
                table.set_fontsize(10)
                table.scale(1, 1.8)

                plt.tight_layout(rect=[0, 0.03, 1, 0.95])
                pdf.savefig(fig, dpi=72)
                plt.close(fig)
                import gc

                gc.collect()

            except Exception as e:
                print(f"ERROR generando página para {ticker}: {e}")
                plt.close("all")  # Cerrar cualquier figura abierta
                continue  # Continuar con el siguiente ticker
    print(f"Informe PDF generado con éxito.")


# ==============================================================================
# NUEVAS FUNCIONES DE REPORTE PDF
# ==============================================================================

def generar_pdf_resumen_ganadores(
    ganadores_por_ticker, nombres_tickers={}, fecha_ult="", portfolio_tickers=[]
):
    """
    Genera un PDF con una tabla resumen de la estrategia ganadora por cada ticker usando ReportLab.
    """
    suffix = f"_{fecha_ult.replace('-', '')}" if fecha_ult else ""
    filename = f"INFORME_RESUMEN_GANADORES{suffix}.pdf"
    print(f"\nGenerando informe resumen de ganadores: {filename}...")

    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []

    # Estilos
    styles = getSampleStyleSheet()
    style_title = styles["Title"]
    style_normal = styles["Normal"]

    # Título
    title_text = "Resumen de Estrategias Ganadoras"
    if fecha_ult:
        title_text += f" (Datos hasta {fecha_ult})"
    elements.append(Paragraph(title_text, style_title))
    elements.append(Spacer(1, 10))
    elements.append(
        Paragraph(
            "Este informe detalla la estrategia que ha obtenido el mejor Ratio de Sharpe histórico para cada activo analizado.",
            style_normal,
        )
    )
    elements.append(Spacer(1, 20))
    elements.append(
        Paragraph(
            "<i>Tabla M/C = Mercado/Combinada. "
            "Los criterios de selección anteriores se aplican sobre Mercado.</i>",
            style_normal,
        )
    )
    elements.append(Spacer(1, 10))

    # Preparar datos de la tabla
    items = sorted(ganadores_por_ticker.items())
    table_data = [["Ticker", "Empresa", "Estrategia Ganadora (Mejor Sharpe)"]]

    for t, s in items:
        nombre = nombres_tickers.get(t, "N/A")
        display_t = f"{t} [C]" if t in portfolio_tickers else t
        table_data.append([display_t, nombre, s])

    # Crear Tabla
    t_width = [80, 240, 150]
    table = Table(table_data, colWidths=t_width, repeatRows=1)

    # Estilo de la tabla
    style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.whitesmoke, colors.HexColor("#D9E2F3")],
            ),
        ]
    )
    table.setStyle(style)

    elements.append(table)

    # Nota al pie
    elements.append(Spacer(1, 20))
    elements.append(
        Paragraph(
            "<i>Nota: El Ratio de Sharpe mide el retorno ajustado por riesgo. Un mayor Sharpe indica una mejor eficiencia de la estrategia.</i>",
            style_normal,
        )
    )

    try:
        doc.build(elements)
        print(f"Informe {filename} generado con éxito.")
    except Exception as e:
        print(f"Error al generar {filename}: {e}")

def generar_pdf_cambios_estado(
    lista_cambios, todas_las_fechas_disponibles=None, nombres_tickers={}, fecha_ult=""
):
    """
    Genera un PDF con los valores que han cambiado de estado en las últimas 5 fechas.
    lista_cambios: Lista de diccionarios {Ticker, Estrategia, Evento, Fecha, Precio, Estado Nuevo}
    todas_las_fechas_disponibles: Set de todas las fechas de trading disponibles para mostrar siempre 5 fechas
    """
    suffix = f"_{fecha_ult.replace('-', '')}" if fecha_ult else ""
    filename = f"INFORME_CAMBIOS_ESTADO{suffix}.pdf"
    print(f"\nGenerando informe de cambios de estado: {filename}...")

    # Obtener las últimas 5 fechas únicas (de todos los tickers disponibles)
    if todas_las_fechas_disponibles:
        fechas_unicas = sorted(todas_las_fechas_disponibles, reverse=True)[:5]
    elif lista_cambios:
        fechas_unicas = sorted(
            set(item["Fecha"] for item in lista_cambios), reverse=True
        )[:5]
    else:
        fechas_unicas = []

    fechas_str = ", ".join(reversed(fechas_unicas))  # Mostrar en orden ascendente

    if not lista_cambios:
        print(
            "  -> No se detectaron cambios de estado en las últimas 5 fechas para ningún valor."
        )
        # Crear PDF vacío o con mensaje
        with PdfPages(filename) as pdf:
            fig = plt.figure(figsize=(10, 7), dpi=72)
            title = f"Informe de Cambios de Estado - Últimas 5 Fechas"
            if fecha_ult:
                title += f" (Última: {fecha_ult})"
            fig.suptitle(title, fontsize=16, y=0.95)
            ax = fig.add_subplot(111)
            mensaje = f"No hubo cambios de estado (Entradas/Salidas)\nen las últimas 5 fechas registradas.\n\nFechas analizadas: {fechas_str}"
            ax.text(
                0.5,
                0.5,
                mensaje,
                horizontalalignment="center",
                verticalalignment="center",
                fontsize=14,
            )
            ax.axis("off")
            pdf.savefig(fig, dpi=72)
            plt.close(fig)
            import gc

            gc.collect()
        return

    # Filtrar solo los cambios en las últimas 5 fechas
    cambios_filtrados = [
        item for item in lista_cambios if item["Fecha"] in fechas_unicas
    ]

    # ORDENAR: Primero por fecha (ascendente), luego por ticker (alfabético)
    cambios_filtrados.sort(key=lambda x: (x["Fecha"], x["Ticker"]))

    # Dividir en páginas si hay muchos
    chunk_size = 15
    chunks = [
        cambios_filtrados[i : i + chunk_size]
        for i in range(0, len(cambios_filtrados), chunk_size)
    ]

    with PdfPages(filename) as pdf:
        for i, chunk in enumerate(chunks):
            fig = plt.figure(figsize=(10, 7), dpi=72)
            titulo = f"Cambios de Estado - Últimas 5 Fechas (Pág {i + 1})"
            fig.suptitle(titulo, fontsize=16, y=0.98)

            # Agregar subtítulo con las fechas
            gs = gridspec.GridSpec(2, 1, height_ratios=[0.1, 1])
            ax_subtitle = fig.add_subplot(gs[0, 0])
            ax_table = fig.add_subplot(gs[1, 0])

            ax_subtitle.axis("off")
            ax_subtitle.text(
                0.5,
                0.5,
                f"Fechas analizadas: {fechas_str}",
                horizontalalignment="center",
                verticalalignment="center",
                fontsize=11,
                style="italic",
            )

            ax_table.axis("off")

            # Preparar datos para tabla
            table_data = []
            for item in chunk:
                ticker = item["Ticker"]
                nombre = nombres_tickers.get(ticker, "")
                # Usar formato Ticker\nNombre
                if nombre:
                    short_name = textwrap.shorten(nombre, width=18, placeholder="...")
                    ticker_display = f"{ticker}\n{short_name}"
                else:
                    ticker_display = ticker
                table_data.append(
                    [
                        ticker_display,
                        item["Estrategia"],
                        item["Fecha"],
                        item["Evento"],
                        item["Estado Nuevo"],
                    ]
                )

            col_labels = ["Ticker", "Estrategia", "Fecha", "Evento", "Estado Nuevo"]

            table = ax_table.table(
                cellText=table_data,
                colLabels=col_labels,
                cellLoc="center",
                loc="center",
            )
            table.auto_set_font_size(False)
            table.set_fontsize(8)
            table.scale(1, 2.2)

            col_widths = [0.30, 0.17, 0.14, 0.18, 0.18]
            for (row, col), cell in table.get_celld().items():
                if col < len(col_widths):
                    cell.set_width(col_widths[col])

            plt.tight_layout(rect=[0, 0.03, 1, 0.95])
            pdf.savefig(fig, dpi=72)
            plt.close(fig)
            import gc

            gc.collect()

    print(
        f"Informe {filename} generado con éxito ({len(cambios_filtrados)} cambios en últimas 5 fechas: {fechas_str})."
    )

def generar_pdf_dashboard_tecnico(
    lista_datos_completos, nombres_tickers={}, fecha_ult="", portfolio_tickers=[]
):
    """
    Genera un PDF con el estado actual (última vela) de los indicadores técnicos clave.
    """
    suffix = f"_{fecha_ult.replace('-', '')}" if fecha_ult else ""
    filename = f"DASHBOARD_INDICADORES_TECNICOS{suffix}.pdf"
    print(f"\nGenerando Dashboard de Indicadores Técnicos: {filename}...")

    dashboard_data = []

    for item in lista_datos_completos:
        ticker = item["ticker"]
        df_viz = item["df_viz"]
        if df_viz is None or df_viz.empty:
            continue

        # Últimos 60 días para niveles clave
        df_recent = df_viz.tail(60)
        soporte = df_recent["low"].min()
        resistencia = df_recent["high"].max()

        last = df_viz.iloc[-1]
        close = last["close"]

        # Distancias porcentuales
        dist_sop = (close / soporte - 1) * 100 if soporte != 0 else 0
        dist_res = (resistencia / close - 1) * 100 if close != 0 else 0

        # Bollinger avanzado
        upper = last["banda_superior"]
        lower = last["banda_inferior"]
        middle = last["sma_bollinger"]

        # %B: Posición relativa (0=suelo, 1=techo)
        b_perc = (close - lower) / (upper - lower) if (upper - lower) != 0 else 0.5
        b_txt = f"{b_perc:.1%}"

        # Bandwidth: Volatilidad relativa (Ancho de bandas / Media)
        bandwidth = (upper - lower) / middle if middle != 0 else 0
        bw_txt = f"{bandwidth:.2f}"
        if bandwidth < 0.05:
            bw_txt += " (Sqz)"  # Squeeze: bandas muy estrechas

        # RSI e interpretación
        rsi_val = last["rsi"]
        rsi_txt = f"{rsi_val:.1f}"
        if rsi_val < 30:
            rsi_txt += " (SV)"
        elif rsi_val > 70:
            rsi_txt += " (SC)"

        # RVOL (Volumen Relativo)
        rvol = last["rvol"]
        rvol_txt = f"{rvol:.2f}"
        if rvol > 1.5:
            rvol_txt += " (+)"  # Alto volumen

        # ATR % (Volatilidad Operativa)
        atr_p = last["atr_perc"]
        atr_txt = f"{atr_p:.1f}%"

        # ADX (Régimen de Mercado)
        adx_val = last["adx"]
        if adx_val > 25:
            regime = "Trend"
        elif adx_val < 20:
            regime = "Lateral"
        else:
            regime = "Neutral"
        adx_txt = f"{adx_val:.0f} ({regime})"

        # MACD Bias
        m_hist = last["macd_histogram"]
        m_bias = "Alc." if m_hist > 0 else "Baj."

        # Tendencia SMA
        sma_s = last["sma_short"]
        sma_l = last["sma_long"]
        t_txt = "Alc." if sma_s > sma_l else "Baj."

        display_t = f"{ticker} [C]" if ticker in portfolio_tickers else ticker
        dashboard_data.append(
            [
                display_t,
                f"{close:.2f}",
                f"{dist_sop:.1f}%",
                f"{dist_res:.1f}%",
                rvol_txt,
                atr_txt,
                rsi_txt,
                b_txt,
                adx_txt,
                f"{m_bias}",
                t_txt,
            ]
        )

    # Ordenar por Ticker
    dashboard_data.sort(key=lambda x: x[0])

    # --- NUEVO: Exportar a CSV para IA ---
    csv_filename = f"dashboard_data{suffix}.csv"
    col_labels = [
        "Ticker",
        "Precio",
        "% Sop",
        "% Res",
        "RVOL",
        "ATR%",
        "RSI",
        "B %B",
        "ADX (Trend)",
        "MACD",
        "Trend",
    ]
    try:
        import csv

        with open(csv_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(col_labels)
            writer.writerows(dashboard_data)
        print(f"Datos exportados a CSV: {csv_filename}")
    except Exception as e:
        print(f"Error exportando CSV: {e}")
    # -------------------------------------

    # Crear PDF
    with PdfPages(filename) as pdf:
        rows_per_page = 22
        for i in range(0, len(dashboard_data), rows_per_page):
            chunk = dashboard_data[i : i + rows_per_page]

            fig, ax = plt.subplots(figsize=(11.69, 8.27))
            ax.axis("off")
            title = "Dashboard Técnico Profesional: Momentum, Volatilidad y Tendencia"
            if fecha_ult:
                title += f" (Datos hasta {fecha_ult})"
            fig.suptitle(title, fontsize=16, y=0.95)

            table = ax.table(
                cellText=chunk, colLabels=col_labels, loc="center", cellLoc="center"
            )
            table.auto_set_font_size(False)
            table.set_fontsize(7.5)
            table.scale(1, 2.2)

            plt.tight_layout()
            pdf.savefig(fig, dpi=72)
            plt.close(fig)
            import gc

            gc.collect()

    print(f"Informe Dashboard generado con éxito.")

def generar_grafico_3d_activos(metricas_globales, nombres_tickers={}, fecha_ult=""):
    """
    Genera un gráfico 3D interactivo (HTML) situando cada activo según Sharpe, Volatilidad y Max DD.
    Incluye una superficie de extrapolación para visualizar la tendencia rentabilidad-riesgo.
    """
    suffix = f"_{fecha_ult.replace('-', '')}" if fecha_ult else ""
    filename = f"ANALISIS_3D_INTERACTIVO{suffix}.html"
    print(f"\nGenerando visualización 3D INTERACTIVA de activos: {filename}...")

    tickers = []
    sharpes = []
    vols = []
    drawdowns = []
    cagrs = []
    hovers = []

    for item in metricas_globales:
        t = item["ticker"]
        if "^" in t or "IBEX" in t.upper():
            continue  # Saltar índices

        m = item["metricas"]
        tickers.append(t)
        sharpe_c = m.get("Ratio de Sharpe_Combinada", 0)
        sharpes.append(sharpe_c)
        vol_c = m.get("Volatilidad_Combinada", 0)
        vols.append(vol_c)
        dd_c = 0
        for k, v in m.items():
            if "drawdown_combinada" in str(k).lower():
                if v is not None:
                    dd_c = v
                break
        drawdowns.append(abs(dd_c))
        cagr_c = m.get("CAGR_Combinada", 0)
        cagrs.append(cagr_c)

        nombre = nombres_tickers.get(t, t)
        hover_text = (
            f"<b>{t} ({nombre})</b><br>"
            f"CAGR: {cagr_c:.2%}<br>"
            f"Sharpe: {sharpe_c:.2f}<br>"
            f"Volatilidad: {vol_c:.2%}<br>"
            f"Max DD: {dd_c:.2%}"
        )
        hovers.append(hover_text)

    if not tickers:
        print("  -> No hay suficientes datos para generar el gráfico 3D.")
        return

    # 1. Crear la figura base de Plotly
    fig = go.Figure()

    # 2. Agregar los puntos (Scatter3D)
    fig.add_trace(
        go.Scatter3d(
            x=vols,
            y=sharpes,
            z=drawdowns,
            mode="markers+text",
            marker=dict(
                size=10,
                color=cagrs,
                colorscale="Viridis",
                colorbar=dict(title="CAGR (%)", tickformat=".1%"),
                opacity=0.8,
                line=dict(color="white", width=1),
            ),
            text=tickers,
            hovertext=hovers,
            hoverinfo="text",
            textposition="top center",
            name="Activos",
        )
    )

    # 3. Calcular superficie de tendencia (Regresión Lineal: Z = aX + bY + c)
    try:
        # Convertir a arrays de numpy para cálculos
        X = np.array(vols)
        Y = np.array(sharpes)
        Z = np.array(drawdowns)

        # Preparar la matriz para mínimos cuadrados: [X, Y, 1]
        A = np.c_[X, Y, np.ones(X.shape)]

        # Resolver los coeficientes (a, b, c) -> a*Vol + b*Sharpe + c = Drawdown
        coeffs, _, _, _ = np.linalg.lstsq(A, Z, rcond=None)
        a, b, c = coeffs

        # Crear una malla para la superficie visual
        xi = np.linspace(min(vols), max(vols), 20)
        yi = np.linspace(min(sharpes), max(sharpes), 20)
        xi_grid, yi_grid = np.meshgrid(xi, yi)

        # Calcular Z (Drawdown estimado) en cada punto de la malla usando el plano
        zi_grid = a * xi_grid + b * yi_grid + c

        # Para el color de la superficie, usamos el plano de rentabilidad (opcional)
        # o simplemente el mismo degradado de color
        C = np.array(cagrs)
        A_c = np.c_[X, Y, np.ones(X.shape)]
        coeffs_c, _, _, _ = np.linalg.lstsq(A_c, C, rcond=None)
        ac, bc, cc = coeffs_c
        ci_grid = ac * xi_grid + bc * yi_grid + cc

        # Agregar la superficie (Best-fit plane)
        fig.add_trace(
            go.Surface(
                x=xi,
                y=yi,
                z=zi_grid,
                surfacecolor=ci_grid,
                colorscale="Viridis",
                showscale=False,
                opacity=0.4,
                name="Tendencia de Riesgo (Ajuste)",
                hoverinfo="skip",
            )
        )
    except Exception as e:
        print(f"  -> Aviso: No se pudo generar la superficie de ajuste: {e}")

    # 4. Configuración del diseño
    title_text = "Análisis Espacial de Activos: Eficiencia, Riesgo y Drawdown"
    if fecha_ult:
        title_text += f" (Datos hasta {fecha_ult})"
    fig.update_layout(
        title=title_text,
        scene=dict(
            xaxis_title="Volatilidad Anualizada",
            yaxis_title="Ratio de Sharpe",
            zaxis_title="Máximo Drawdown (Abs)",
            bgcolor="rgb(240, 240, 240)",
        ),
        margin=dict(l=0, r=0, b=0, t=50),
        width=1200,
        height=900,
    )

    # Guardar como HTML
    fig.write_html(filename)
    print(f"Gráfico interactivo guardado como {filename}.")

def generar_heatmap_sectores(data_enriquecida, filename="heatmap_sectores.png"):
    """
    Genera un mapa de calor sectorial del IBEX 35 basado en el Score técnico.
    """
    SECTORES = SECTORES_IBEX

    # Preparar datos
    records = []
    for item in data_enriquecida:
        ticker = item["Ticker"]
        if ticker in SECTORES:
            records.append(
                {
                    "Ticker": ticker,
                    "Sector": SECTORES[ticker],
                    "Score": item["Score"],
                    "Semaforo": item["Semaforo"],
                }
            )

    if not records:
        return
    df = pd.DataFrame(records)

    # Crear figura
    plt.figure(figsize=(10, 6))
    sectors = sorted(df["Sector"].unique())
    num_sectors = len(sectors)

    # Usaremos una representación de rectángulos simple para el heatmap
    # Plotly Treemap sería ideal pero para el PDF estático usamos Matplotlib
    import matplotlib.patches as patches

    fig, ax = plt.subplots(figsize=(12, 8))

    # Agrupar por sector
    y_pos = 0
    box_height = 0.8
    for sector in sectors:
        df_sec = df[df["Sector"] == sector]
        x_pos = 0
        ax.text(
            -0.5,
            y_pos + box_height / 2,
            sector,
            va="center",
            ha="right",
            fontweight="bold",
            fontsize=10,
        )

        for _, row in df_sec.iterrows():
            color = (
                "#C6EFCE"
                if row["Semaforo"] == "VERDE"
                else "#FFF2CC"
                if row["Semaforo"] == "AMARILLO"
                else "#F8CBAD"
            )
            rect = patches.Rectangle(
                (x_pos, y_pos),
                0.9,
                box_height,
                linewidth=1,
                edgecolor="white",
                facecolor=color,
            )
            ax.add_patch(rect)
            ax.text(
                x_pos + 0.45,
                y_pos + box_height / 2,
                row["Ticker"],
                va="center",
                ha="center",
                fontsize=8,
            )
            x_pos += 1.0

        y_pos += 1.0

    ax.set_xlim(-2, df.groupby("Sector")["Ticker"].count().max() + 1)
    ax.set_ylim(-0.5, num_sectors + 0.5)
    ax.axis("off")
    plt.title("Mapa de Calor Sectorial IBEX 35 (Salud Técnica)", fontsize=14, pad=20)
    plt.tight_layout()
    plt.savefig(filename, dpi=150, bbox_inches="tight")
    plt.close()


# ==============================================================================
# BLOQUE PRINCIPAL DE EJECUCIÓN
# ==============================================================================

def generar_informe_estrategico_largo_plazo(
    metricas_globales, nombres_tickers={}, fecha_ult="", portfolio_tickers=[]
):
    """
    Genera un informe PDF con los activos de mayor convicción para el largo plazo.
    Filtra por CAGR, Sharpe y Drawdown históricos.
    """
    fecha_str = fecha_ult if fecha_ult else datetime.now().strftime("%Y-%m-%d")
    filename = f"Inversion_Estrategica_Largo_Plazo_{fecha_str.replace('-', '')}.pdf"
    print(f"Generando {filename}...")

    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        "TitleStyle", parent=styles["Title"], fontSize=22, spaceAfter=20
    )
    style_h2 = ParagraphStyle(
        "H2Style", parent=styles["Heading2"], fontSize=16, spaceAfter=10
    )
    style_normal = styles["Normal"]

    elements.append(
        Paragraph("Informe de Inversión Estratégica (Medio/Largo Plazo)", style_title)
    )
    elements.append(
        Paragraph(
            f"Selección de Activos de Alta Convicción - Datos hasta {fecha_str}",
            style_h2,
        )
    )
    elements.append(Spacer(1, 12))

    elements.append(
        Paragraph(
            "Este informe identifica activos con solidez histórica estructural, ideales para estrategias de 'Buy & Hold' o acumulación.",
            style_normal,
        )
    )
    elements.append(Paragraph("<b>Criterios de Selección:</b>", style_normal))
    elements.append(
        Paragraph(
            "- CAGR Histórico > 10%: Crecimiento anual compuesto positivo y robusto.",
            style_normal,
        )
    )
    elements.append(
        Paragraph(
            "- Ratio de Sharpe > 0.60: Alta eficiencia entre rentabilidad y riesgo.",
            style_normal,
        )
    )
    elements.append(
        Paragraph(
            "- Máximo Drawdown < 30%: Resiliencia demostrada en periodos correctivos.",
            style_normal,
        )
    )
    elements.append(Spacer(1, 20))

    def _get_metric_any(metricas, *keys, default=0):
        for k in keys:
            if k in metricas:
                v = metricas.get(k)
                if v is not None:
                    return v
            try:
                k_mojibake = str(k).encode("utf-8").decode("latin-1")
                if k_mojibake in metricas:
                    v = metricas.get(k_mojibake)
                    if v is not None:
                        return v
            except Exception:
                pass
        return default

    # Filtrar y ordenar
    picks = []
    for item in metricas_globales:
        m = item["metricas"]
        # Usamos metricas del Mercado (el activo en si) para inversion estructural
        cagr = _get_metric_any(m, "CAGR Mercado", default=0)
        sharpe = _get_metric_any(m, "Sharpe Mercado", default=0)
        cagr_c = _get_metric_any(m, "CAGR_Combinada", default=0)
        sharpe_c = _get_metric_any(m, "Ratio de Sharpe_Combinada", default=0)
        drawdown = _get_metric_any(m, "Máximo Drawdown Mercado", default=0)
        drawdown_c = _get_metric_any(m, "Máximo Drawdown_Combinada", default=0)


        if cagr > 0.10 and sharpe > 0.60 and drawdown > -0.30:
            picks.append(
                {
                    "Ticker": item["ticker"],
                    "Display_Ticker": f"{item['ticker']} [C]"
                    if item["ticker"] in portfolio_tickers
                    else item["ticker"],
                    "Nombre": nombres_tickers.get(item["ticker"], item["ticker"]),
                    "CAGR": f"{cagr:.2%} / {cagr_c:.2%}",
                    "Sharpe": f"{sharpe:.2f} / {sharpe_c:.2f}",
                    "MaxDD": f"{drawdown:.2%} / {drawdown_c:.2%}",
                    "Precio": f"{item['precio_actual']:.2f}€",
                    "val_sharpe": sharpe,
                }
            )

    # Ordenar por Sharpe descendente
    picks.sort(key=lambda x: x["val_sharpe"], reverse=True)

    if picks:
        table_data = [
            ["Ticker", "Nombre", "CAGR M/C", "Sharpe M/C", "Max DD M/C", "Pr. Actual"]
        ]
        for p in picks:
            table_data.append(
                [
                    p["Display_Ticker"],
                    p["Nombre"],
                    p["CAGR"],
                    p["Sharpe"],
                    p["MaxDD"],
                    p["Precio"],
                ]
            )

        t = Table(table_data, colWidths=[60, 140, 92, 88, 100, 58])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2F5597")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.whitesmoke, colors.HexColor("#EDF2F9")],
                    ),
                ]
            )
        )
        elements.append(t)
    else:
        elements.append(
            Paragraph(
                "No se han detectado activos que cumplan simultáneamente con todos los criterios de alta convicción en este periodo.",
                style_normal,
            )
        )

    elements.append(Spacer(1, 30))
    elements.append(
        Paragraph(
            "<b>Nota importante:</b> La inversión a largo plazo requiere paciencia. Estos activos muestran una tendencia de fondo constructiva, pero pueden sufrir volatilidad de corto plazo.",
            style_normal,
        )
    )

    doc.build(elements)
    print(f"Informe estratégico generado: {filename}")


# ==============================================================================
# NUEVAS FUNCIONES: ANÁLISIS ENRIQUECIDO DETERMINISTA (IA + PYTHON)
# ==============================================================================


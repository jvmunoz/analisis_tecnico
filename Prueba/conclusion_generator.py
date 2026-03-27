def generar_conclusion_texto(metricas):
    lines = []
    
    # 1. Análisis de Eficiencia (Sharpe)
    sharpe_comb = metricas.get('Ratio de Sharpe_Combinada', 0)
    sharpe_mkt = metricas.get('Sharpe Mercado', 0)
    if sharpe_comb > 1.5:
        eff_status = "EXCELENTE"
    elif sharpe_comb > 1.0:
        eff_status = "BUENA"
    elif sharpe_comb > 0.5:
        eff_status = "ACEPTABLE"
    else:
        eff_status = "DEFICIENTE"
    
    comp_mkt = "SUPERIOR" if sharpe_comb > sharpe_mkt else "INFERIOR"
    lines.append(f"<b>Eficiencia Global:</b> La estrategia muestra una eficiencia <b>{eff_status}</b> (Sharpe {sharpe_comb:.2f}), siendo <b>{comp_mkt}</b> al mercado ({sharpe_mkt:.2f}).")

    # 2. Perfil de Riesgo (Drawdown & VaR)
    dd_comb = metricas.get('Máximo Drawdown_Combinada', 0)
    var_95 = metricas.get('VaR 95_Combinada', 0)
    if abs(dd_comb) < 0.15:
        risk_profile = "MUY CONSERVADOR"
    elif abs(dd_comb) < 0.25:
        risk_profile = "MODERADO"
    else:
        risk_profile = "AGRESIVO/ALTO RIESGO"
        
    lines.append(f"<b>Perfil de Riesgo:</b> {risk_profile}. El sistema ha contenido las caídas en un máximo del <b>{dd_comb:.1%}</b>. "
                 f"En un escenario diario adverso (VaR 95%), se espera perder un <b>{var_95:.2%}</b>.")

    # 3. Estilo de Trading (Win Rate vs Profit Factor)
    win_rate = metricas.get('Win Rate_Tendencia', 0) # Usamos Tendencia como proxy de "estilo direccional"
    pf = metricas.get('Profit Factor_Tendencia', 0)
    
    if win_rate < 0.40 and pf > 1.5:
        style = "TENDENCIAL PURO (Cazador de olas)"
        desc = "baja tasa de aciertos pero grandes beneficios cuando gana"
    elif win_rate > 0.60:
        style = "REVERSION/PRECISIÓN"
        desc = "alta tasa de aciertos con beneficios más moderados"
    else:
        style = "HÍBRIDO/EQUILIBRADO"
        desc = "un equilibrio entre frecuencia de aciertos y magnitud de ganancia"
        
    lines.append(f"<b>Estilo Operativo:</b> Se comporta como un sistema <b>{style}</b>, caracterizado por tener {desc}. "
                 f"(Profit Factor Tendencia: {pf:.2f}).")

    # 4. Aportación de Estrategias
    sharpes = {
        'Tendencia': metricas.get('Ratio de Sharpe_Tendencia', -99),
        'Bollinger': metricas.get('Ratio de Sharpe_Bollinger', -99),
        'RSI': metricas.get('Ratio de Sharpe_RSI', -99),
        'MACD': metricas.get('Ratio de Sharpe_MACD', -99)
    }
    best_strat = max(sharpes, key=sharpes.get)
    worst_strat = min(sharpes, key=sharpes.get)
    
    lines.append(f"<b>Contribución:</b> La estrategia estrella es <b>{best_strat}</b> (Sharpe {sharpes[best_strat]:.2f}), "
                 f"mientras que <b>{worst_strat}</b> es la que más lastra el conjunto.")

    return "<br/>".join(lines)

def analizar_matriz_heatmap(matriz):
    """Devuelve estadísticas clave de una matriz de sensibilidad."""
    valid_vals = matriz[~np.isnan(matriz)]
    if len(valid_vals) == 0:
        return {'max': 0, 'mean': 0, 'std': 0, 'robustness': 0}
    
    max_val = np.max(valid_vals)
    mean_val = np.mean(valid_vals)
    std_val = np.std(valid_vals)
    
    # Robustez: % de configuraciones que tienen un Sharpe decente (> 70% del maximo o > 0.5 absoluto)
    # Si el maximo es muy bajo (<0.3), la robustez es irrelevante (es 0)
    thresh = max(0.5, max_val * 0.7)
    robust_count = np.sum(valid_vals >= thresh)
    robustness = robust_count / len(valid_vals)
    
    return {'max': max_val, 'mean': mean_val, 'std': std_val, 'robustness': robustness}

def generar_conclusion_sensibilidad(stats_dict):
    """
    Genera un texto de conclusiones basado en las estadísticas de las 4 estrategias.
    stats_dict: {'Tendencia': stats, 'Bollinger': stats, ...}
    """
    lines = []
    
    # 1. Identificar la mejor estrategia (potencial máximo)
    best_strat = max(stats_dict, key=lambda k: stats_dict[k]['max'])
    best_val = stats_dict[best_strat]['max']
    
    # 2. Identificar la estrategia más robusta
    most_stable = max(stats_dict, key=lambda k: stats_dict[k]['robustness'])
    stable_val = stats_dict[most_stable]['robustness']
    
    lines.append(f"Potencial Máximo: La estrategia con mayor techo es {best_strat} (Sharpe máx: {best_val:.2f}).")
    
    if stable_val > 0.4:
        stab_desc = "muy noble" if stable_val > 0.7 else "bastante estable"
        lines.append(f"Estabilidad: {most_stable} se comporta de forma {stab_desc} ante cambios de parámetros (Robustez: {stable_val:.0%}).")
    else:
        lines.append(f"Estabilidad: En general, los resultados son sensibles a los parámetros. Se recomienda optimización precisa.")
        
    # 3. Advertencias
    warnings = []
    for strat, s in stats_dict.items():
        if s['max'] < 0.2:
            warnings.append(f"{strat} (débil)")
        elif s['std'] > 0.5: # Mucha varianza
            warnings.append(f"{strat} (inestable)")
            
    if warnings:
        clean_warns = ", ".join(warnings)
        lines.append(f"Atención: Revisar {clean_warns}.")
        
    return " | ".join(lines)

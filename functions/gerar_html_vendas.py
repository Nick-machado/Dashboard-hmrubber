import pandas as pd
from datetime import datetime
import io

def gerar_html_relatorio_vendas(df_vendas, ano, mes, role, 
                               total_vendas, margem_total, volume_total, ticket_medio,
                               delta_total_vendas, delta_margem, delta_volume, delta_ticket,
                               fat_canal=None, fat_grupo=None, fat_cliente=None, fat_vendedor=None,
                               usuario_nome=None):
    """
    Gera um relatório HTML completo da Visão Geral de Vendas
    Este HTML pode ser convertido para PDF pelo navegador (Ctrl+P -> Salvar como PDF)
    """
    
    meses = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    
    # CSS para formatação
    css = """
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            line-height: 1.6;
            color: #333;
        }
        .header { 
            text-align: center; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            padding: 20px; 
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .section { 
            margin: 20px 0; 
            padding: 15px;
            border-left: 4px solid #667eea;
            background: #f8f9fa;
            border-radius: 0 5px 5px 0;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .metric-card {
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }
        .metric-title {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
            font-weight: 500;
        }
        .metric-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }
        .metric-delta {
            font-size: 0.85em;
        }
        table { 
            width: 100%; 
            border-collapse: collapse; 
            margin: 10px 0;
            background: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        th, td { 
            padding: 12px; 
            text-align: left; 
            border-bottom: 1px solid #ddd;
        }
        th { 
            background: #667eea;
            color: white;
            font-weight: 600;
        }
        tr:nth-child(even) { 
            background: #f8f9fa;
        }
        tr:hover {
            background: #e9ecef;
        }
        .positive { color: #28a745; font-weight: bold; }
        .negative { color: #dc3545; font-weight: bold; }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #667eea;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }
        @media print {
            body { font-size: 12px; margin: 10px; }
            .header { background: #667eea !important; }
            .section { break-inside: avoid; }
            .metric-card { break-inside: avoid; }
        }
    </style>
    """
    
    # HTML principal
    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Relatório de Vendas - {meses[mes-1]} {ano}</title>
        {css}
    </head>
    <body>
        <div class="header">
            <h1>📊 Relatório de Vendas - {meses[mes-1]} de {ano}</h1>
            <p><strong>Setor:</strong> {role} | <strong>Data:</strong> {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
        </div>
    """
    
    # Função auxiliar para formatar deltas
    def format_delta(value):
        if value >= 0:
            return f'<span class="positive">▲ R$ {value:,.2f}</span>'
        else:
            return f'<span class="negative">▼ R$ {abs(value):,.2f}</span>'
    
    def format_delta_volume(value):
        if value >= 0:
            return f'<span class="positive">▲ {value:,.2f}</span>'
        else:
            return f'<span class="negative">▼ {abs(value):,.2f}</span>'
    
    # KPIs Principais
    html += f"""
        <div class="section">
            <h2>📈 Indicadores Principais</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-title">Faturamento Total</div>
                    <div class="metric-value">R$ {total_vendas:,.2f}</div>
                    <div class="metric-delta">{format_delta(delta_total_vendas)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">Margem Total</div>
                    <div class="metric-value">R$ {margem_total:,.2f}</div>
                    <div class="metric-delta">{format_delta(delta_margem)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">Volume Vendido</div>
                    <div class="metric-value">{volume_total:,.2f}</div>
                    <div class="metric-delta">{format_delta_volume(delta_volume)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">Ticket Médio</div>
                    <div class="metric-value">R$ {ticket_medio:,.2f}</div>
                    <div class="metric-delta">{format_delta(delta_ticket)}</div>
                </div>
            </div>
        </div>
    """
    
    # Faturamento por Canal
    if fat_canal is not None and not fat_canal.empty:
        # Ordenar por faturamento (maior para menor)
        fat_canal_sorted = fat_canal.sort_values('Total NF', ascending=False)
        
        html += """
            <div class="section">
                <h2>🏢 Faturamento por Canal</h2>
                <table>
                    <thead>
                        <tr><th>Canal</th><th>Faturamento</th><th>Participação %</th></tr>
                    </thead>
                    <tbody>
        """
        
        total_canal = fat_canal['Total NF'].sum()
        for _, row in fat_canal_sorted.iterrows():
            participacao = (row['Total NF'] / total_canal * 100) if total_canal > 0 else 0
            html += f"""
                        <tr>
                            <td>{row['Atividade']}</td>
                            <td>R$ {row['Total NF']:,.2f}</td>
                            <td>{participacao:.1f}%</td>
                        </tr>"""
        
        html += """
                    </tbody>
                </table>
            </div>
        """
    
    # Top 10 Clientes
    if fat_cliente is not None and not fat_cliente.empty:
        html += """
            <div class="section">
                <h2>🏆 Top 10 Clientes</h2>
                <table>
                    <thead>
                        <tr><th>#</th><th>Cliente</th><th>Faturamento</th><th>Margem</th><th>Margem %</th></tr>
                    </thead>
                    <tbody>
        """
        
        top_clientes = fat_cliente.head(10)
        for i, (_, row) in enumerate(top_clientes.iterrows(), 1):
            cliente_nome = str(row['Cliente'])[:40] + "..." if len(str(row['Cliente'])) > 40 else str(row['Cliente'])
            margem_pct = (row['Margem'] / row['Faturamento'] * 100) if row['Faturamento'] > 0 else 0
            html += f"""
                        <tr>
                            <td>{i}</td>
                            <td>{cliente_nome}</td>
                            <td>R$ {row['Faturamento']:,.2f}</td>
                            <td>R$ {row['Margem']:,.2f}</td>
                            <td>{margem_pct:.1f}%</td>
                        </tr>"""
        
        html += """
                    </tbody>
                </table>
            </div>
        """
    
    # Top 10 Grupos de Produtos
    if fat_grupo is not None and not fat_grupo.empty:
        html += """
            <div class="section">
                <h2>📦 Top 10 Grupos de Produtos</h2>
                <table>
                    <thead>
                        <tr><th>Grupo</th><th>Faturamento</th><th>Margem</th><th>Volume</th></tr>
                    </thead>
                    <tbody>
        """
        
        top_grupos = fat_grupo.head(10)
        for _, row in top_grupos.iterrows():
            grupo_nome = str(row['Grupo'])[:35] + "..." if len(str(row['Grupo'])) > 35 else str(row['Grupo'])
            html += f"""
                        <tr>
                            <td>{grupo_nome}</td>
                            <td>R$ {row['Total NF']:,.2f}</td>
                            <td>R$ {row['$ Margem']:,.2f}</td>
                            <td>{row['Quant.']:,.1f}</td>
                        </tr>"""
        
        html += """
                    </tbody>
                </table>
            </div>
        """
    
    # Top 10 Vendedores
    if fat_vendedor is not None and not fat_vendedor.empty:
        html += """
            <div class="section">
                <h2>👤 Top 10 Vendedores</h2>
                <table>
                    <thead>
                        <tr><th>#</th><th>Vendedor</th><th>Faturamento</th><th>Participação %</th></tr>
                    </thead>
                    <tbody>
        """
        
        top_vendedores = fat_vendedor.head(10)
        total_vendedores = fat_vendedor['$ Margem'].sum()
        for i, (_, row) in enumerate(top_vendedores.iterrows(), 1):
            vendedor_nome = str(row['Vendedor'])[:40] + "..." if len(str(row['Vendedor'])) > 40 else str(row['Vendedor'])
            participacao = (row['$ Margem'] / total_vendedores * 100) if total_vendedores > 0 else 0
            html += f"""
                        <tr>
                            <td>{i}</td>
                            <td>{vendedor_nome}</td>
                            <td>R$ {row['$ Margem']:,.2f}</td>
                            <td>{participacao:.1f}%</td>
                        </tr>"""
        
        html += """
                    </tbody>
                </table>
            </div>
        """
    
    # Resumo Estatístico
    html += f"""
        <div class="section">
            <h2>📊 Resumo Estatístico</h2>
            <table>
                <thead>
                    <tr><th>Métrica</th><th>Valor</th></tr>
                </thead>
                <tbody>
                    <tr><td>Total de Clientes Únicos</td><td>{df_vendas['Cliente'].nunique():,}</td></tr>
                    <tr><td>Total de Produtos Vendidos</td><td>{df_vendas['Produto'].nunique():,}</td></tr>
                    <tr><td>Total de Notas Fiscais</td><td>{df_vendas['Nota'].nunique():,}</td></tr>
                    <tr><td>Margem Média (%)</td><td>{(margem_total / total_vendas * 100):.2f}%</td></tr>
                    <tr><td>Volume Médio por Nota</td><td>{(volume_total / df_vendas['Nota'].nunique()):.2f}</td></tr>
                </tbody>
            </table>
        </div>
    """
    
    # Rodapé
    usuario_info = ""
    if usuario_nome:
        usuario_info = f"<p><strong>Solicitado por:</strong> {usuario_nome}<br/><strong>Setor:</strong> {role}</p>"
    
    html += f"""
        <div class="footer">
            {usuario_info}
            <p><em>Relatório gerado automaticamente pelo Sistema Dashboard HM Rubber</em></p>
            <p>Data/Hora: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>
            <p><strong>💡 Dica:</strong> Para salvar como PDF, use Ctrl+P e selecione "Salvar como PDF"</p>
        </div>
    </body>
    </html>
    """
    
    return html


def criar_html_simples_vendas(df_vendas, ano, mes, total_vendas, margem_total, role):
    """
    Versão simplificada para gerar HTML apenas com dados essenciais
    """
    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Relatório Resumido - {meses[mes-1]} {ano}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ text-align: center; background: #667eea; color: white; padding: 15px; }}
            .content {{ margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Relatório Resumido - {meses[mes-1]} de {ano}</h1>
        </div>
        <div class="content">
            <p><strong>Faturamento Total:</strong> R$ {total_vendas:,.2f}</p>
            <p><strong>Margem Total:</strong> R$ {margem_total:,.2f}</p>
            <p><strong>Clientes Atendidos:</strong> {df_vendas['Cliente'].nunique()}</p>
            <p><strong>Produtos Vendidos:</strong> {df_vendas['Produto'].nunique()}</p>
            <p><em>Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</em></p>
        </div>
    </body>
    </html>
    """
    
    return html
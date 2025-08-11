import io
import pandas as pd
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import plotly.graph_objects as go
import plotly.io as pio

def gerar_pdf_relatorio_vendas(df_vendas, ano, mes, role, 
                              total_vendas, margem_total, volume_total, ticket_medio,
                              delta_total_vendas, delta_margem, delta_volume, delta_ticket,
                              fat_canal=None, fat_grupo=None, fat_cliente=None, fat_vendedor=None,
                              usuario_nome=None):
    """
    Gera um relatório PDF completo da Visão Geral de Vendas
    
    Args:
        df_vendas: DataFrame com dados de vendas
        ano: Ano selecionado
        mes: Mês selecionado  
        role: Perfil do usuário (setor)
        total_vendas: Faturamento total
        margem_total: Margem total
        volume_total: Volume total
        ticket_medio: Ticket médio
        delta_*: Variações comparativas
        fat_*: DataFrames opcionais para análises detalhadas
        usuario_nome: Nome do usuário que solicitou o relatório (opcional)
    
    Returns:
        BytesIO: Buffer com o PDF gerado
    """
    
    # Buffer para o PDF
    buffer = io.BytesIO()
    
    # Configuração do documento
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo personalizado para título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.darkblue,
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    # Estilo para subtítulos
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.darkblue,
        spaceBefore=20,
        spaceAfter=15
    )
    
    # Estilo para texto normal
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT
    )
    
    # Lista de elementos do PDF
    elements = []
    
    # ============= CABEÇALHO =============
    meses = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    
    titulo = f"Relatório de Vendas - {meses[mes-1]} de {ano}"
    elements.append(Paragraph(titulo, title_style))
    
    # Informações gerais
    info_geral = f"""
    <b>Setor:</b> {role}<br/>
    <b>Período:</b> {meses[mes-1]} de {ano}<br/>
    <b>Data de Geração:</b> {datetime.now().strftime('%d/%m/%Y às %H:%M')}<br/>
    """
    elements.append(Paragraph(info_geral, normal_style))
    elements.append(Spacer(1, 20))
    
    # ============= KPIs PRINCIPAIS =============
    elements.append(Paragraph("📈 Indicadores Principais", subtitle_style))
    
    # Tabela de KPIs
    kpi_data = [
        ['Indicador', 'Valor Atual', 'Variação vs Ano Anterior'],
        [
            'Faturamento Total',
            f"R$ {total_vendas:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            f"R$ {delta_total_vendas:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + (' 📈' if delta_total_vendas >= 0 else ' 📉')
        ],
        [
            'Margem Total',
            f"R$ {margem_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            f"R$ {delta_margem:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + (' 📈' if delta_margem >= 0 else ' 📉')
        ],
        [
            'Volume Vendido',
            f"{volume_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            f"{delta_volume:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + (' 📈' if delta_volume >= 0 else ' 📉')
        ],
        [
            'Ticket Médio',
            f"R$ {ticket_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            f"R$ {delta_ticket:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + (' 📈' if delta_ticket >= 0 else ' 📉')
        ]
    ]
    
    kpi_table = Table(kpi_data)
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    elements.append(kpi_table)
    elements.append(Spacer(1, 20))
    
    # ============= ANÁLISE POR CANAL =============
    if fat_canal is not None and not fat_canal.empty:
        elements.append(Paragraph("🏢 Faturamento por Canal", subtitle_style))
        
        # Ordenar por faturamento (maior para menor)
        fat_canal_sorted = fat_canal.sort_values('Total NF', ascending=False)
        
        # Preparar dados do canal
        canal_data = [['Canal', 'Faturamento', 'Participação %']]
        for _, row in fat_canal_sorted.iterrows():
            canal_data.append([
                str(row['Atividade']),
                f"R$ {row['Total NF']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                f"{(row['Total NF'] / fat_canal['Total NF'].sum() * 100):.1f}%"
            ])
        
        canal_table = Table(canal_data)
        canal_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        elements.append(canal_table)
        elements.append(Spacer(1, 20))
    
    # ============= TOP 10 CLIENTES =============
    if fat_cliente is not None and not fat_cliente.empty:
        elements.append(Paragraph("🏆 Top 10 Clientes", subtitle_style))
        
        # Limitar a 10 clientes para o PDF
        top_clientes = fat_cliente.head(10)
        
        cliente_data = [['#', 'Cliente', 'Faturamento', 'Margem', 'Margem %']]
        for i, (_, row) in enumerate(top_clientes.iterrows(), 1):
            margem_pct = (row['Margem'] / row['Faturamento'] * 100) if row['Faturamento'] > 0 else 0
            cliente_data.append([
                str(i),
                str(row['Cliente'])[:30] + "..." if len(str(row['Cliente'])) > 30 else str(row['Cliente']),
                f"R$ {row['Faturamento']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                f"R$ {row['Margem']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                f"{margem_pct:.1f}%"
            ])
        
        cliente_table = Table(cliente_data)
        cliente_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        elements.append(cliente_table)
        elements.append(Spacer(1, 15))
    
    # ============= NOVA PÁGINA - ANÁLISES DETALHADAS =============
    elements.append(PageBreak())
    
    # ============= FATURAMENTO POR GRUPO DE PRODUTOS =============
    if fat_grupo is not None and not fat_grupo.empty:
        elements.append(Paragraph("📦 Faturamento por Grupo de Produtos", subtitle_style))
        
        grupo_data = [['Grupo', 'Faturamento', 'Margem', 'Volume']]
        for _, row in fat_grupo.head(10).iterrows():
            grupo_data.append([
                str(row['Grupo'])[:25] + "..." if len(str(row['Grupo'])) > 25 else str(row['Grupo']),
                f"R$ {row['Total NF']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                f"R$ {row['$ Margem']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                f"{row['Quant.']:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
            ])
        
        grupo_table = Table(grupo_data)
        grupo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        elements.append(grupo_table)
        elements.append(Spacer(1, 20))
    
    # ============= TOP VENDEDORES =============
    if fat_vendedor is not None and not fat_vendedor.empty:
        elements.append(Paragraph("👤 Top 10 Vendedores", subtitle_style))
        
        vendedor_data = [['#', 'Vendedor', 'Faturamento', 'Margem']]
        for i, (_, row) in enumerate(fat_vendedor.head(10).iterrows(), 1):
            vendedor_data.append([
                str(i),
                str(row['Vendedor'])[:30] + "..." if len(str(row['Vendedor'])) > 30 else str(row['Vendedor']),
                f"R$ {row['$ Margem']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),  # fat_vendedor usa '$ Margem' como total
                f"{(row['$ Margem'] / fat_vendedor['$ Margem'].sum() * 100):.1f}%" if fat_vendedor['$ Margem'].sum() > 0 else "0%"
            ])
        
        vendedor_table = Table(vendedor_data)
        vendedor_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        elements.append(vendedor_table)
        elements.append(Spacer(1, 20))
    
    # ============= RESUMO ESTATÍSTICO =============
    elements.append(Paragraph("📊 Resumo Estatístico", subtitle_style))
    
    resumo_data = [
        ['Métrica', 'Valor'],
        ['Total de Clientes Únicos', f"{df_vendas['Cliente'].nunique():,}"],
        ['Total de Produtos Vendidos', f"{df_vendas['Produto'].nunique():,}"],
        ['Total de Notas Fiscais', f"{df_vendas['Nota'].nunique():,}"],
        ['Margem Média (%)', f"{(margem_total / total_vendas * 100):.2f}%" if total_vendas > 0 else "0%"],
        ['Volume Médio por Nota', f"{(volume_total / df_vendas['Nota'].nunique()):.2f}" if df_vendas['Nota'].nunique() > 0 else "0"]
    ]
    
    resumo_table = Table(resumo_data)
    resumo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    elements.append(resumo_table)
    
    # ============= RODAPÉ =============
    elements.append(Spacer(1, 30))
    
    # Informações do usuário
    usuario_info = ""
    if usuario_nome:
        usuario_info = f"Solicitado por: {usuario_nome}<br/>Setor: {role}<br/><br/>"
    
    rodape = f"""
    <i>{usuario_info}Relatório gerado automaticamente pelo Sistema Dashboard HM Rubber<br/>
    Data/Hora: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</i>
    """
    elements.append(Paragraph(rodape, ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)))
    
    # ============= GERAR PDF =============
    try:
        doc.build(elements)
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Erro ao gerar PDF: {e}")
        return None


def criar_pdf_simples_vendas(df_vendas, ano, mes, total_vendas, margem_total):
    """
    Versão simplificada para gerar PDF apenas com dados essenciais
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    
    # Título
    title = f"Relatório Resumido - {meses[mes-1]} de {ano}"
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Spacer(1, 20))
    
    # Resumo básico
    resumo = f"""
    Faturamento Total: R$ {total_vendas:,.2f}<br/>
    Margem Total: R$ {margem_total:,.2f}<br/>
    Clientes Atendidos: {df_vendas['Cliente'].nunique()}<br/>
    Produtos Vendidos: {df_vendas['Produto'].nunique()}<br/>
    """
    elements.append(Paragraph(resumo, styles['Normal']))
    
    try:
        doc.build(elements)
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Erro ao gerar PDF simples: {e}")
        return None

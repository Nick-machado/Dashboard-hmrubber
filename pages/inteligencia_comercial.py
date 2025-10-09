"""
Página de Inteligência Comercial - Dashboard de Análise de Vendas (Refatorada)

Esta página fornece análises avançadas baseadas em dados do banco:
- Tendência de crescimento por atividade (Grupo)
- Previsão de vendas (forecast) com modelo polinomial
- Sazonalidade dos produtos e padrões mensais
- KPIs executivos consolidados
"""

from functions.menu import menu_with_redirect
import streamlit as st
import sys
import os

st.set_page_config(layout="wide", page_title="Inteligência Comercial")
menu_with_redirect()

# Adicionar módulos ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'modules'))

import pandas as pd
import numpy as np
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import plotly.graph_objects as go
import plotly.express as px
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import r2_score
from functions.query import run_query
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# ESTILOS CUSTOMIZADOS
# ============================================================================
st.markdown(
    """
    <style>
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    div[data-testid="metric-container"] > label {
        color: white !important;
        font-weight: 600 !important;
    }
    div[data-testid="metric-container"] > div {
        color: white !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 24px;
        background: none !important;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
        color: #fff !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #667eea !important;
        color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================================
# CONFIGURAÇÕES E CORES
# ============================================================================
COLORS = {
    'primary': '#3b82f6',
    'secondary': '#10b981',
    'tertiary': '#f59e0b',
    'quaternary': '#ef4444',
    'quinary': '#8b5cf6',
    'senary': '#ec4899'
}

COLOR_SEQUENCE = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']

# ============================================================================
# FUNÇÕES DE CARREGAMENTO DE DADOS
# ============================================================================
@st.cache_data(ttl=3600)
def carregar_dados_banco(data_inicio: str, data_fim: str) -> pd.DataFrame:
    """Carrega dados do banco usando query.py"""
    df = run_query(data_inicio, data_fim)
    return df

def processar_dados_mensais(df: pd.DataFrame) -> pd.DataFrame:
    """Processa dados para análise mensal"""
    df_mensal = df.groupby(['Ano', 'Mês']).agg({
        'Total NF': 'sum',
        'Vlr.Líquido': 'sum',
        '$ Margem': 'sum',
        'Quant.': 'sum'
    }).reset_index()
    
    # Criar coluna de data
    df_mensal['Data'] = pd.to_datetime(
        df_mensal['Ano'].astype(str) + '-' + df_mensal['Mês'].astype(str) + '-01'
    )
    df_mensal = df_mensal.sort_values('Data')
    
    # Criar nome do mês
    meses_nomes = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
                   7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    df_mensal['Nome do Mês'] = df_mensal['Mês'].map(meses_nomes)
    
    # Calcular margem percentual
    df_mensal['% Margem'] = (df_mensal['$ Margem'] / df_mensal['Vlr.Líquido'] * 100).round(2)
    
    return df_mensal

def processar_dados_grupo(df: pd.DataFrame) -> pd.DataFrame:
    """Processa dados por grupo"""
    df_grupo = df.groupby('Grupo').agg({
        'Total NF': 'sum',
        'Vlr.Líquido': 'sum',
        '$ Margem': 'sum',
        'Quant.': 'sum'
    }).reset_index()
    
    # Calcular participação
    df_grupo['Participação %'] = (df_grupo['Vlr.Líquido'] / df_grupo['Vlr.Líquido'].sum() * 100).round(2)
    
    # Calcular margem percentual
    df_grupo['% Margem'] = (df_grupo['$ Margem'] / df_grupo['Vlr.Líquido'] * 100).round(2)
    
    # Calcular ticket médio
    df_grupo['Ticket Médio'] = (df_grupo['Vlr.Líquido'] / df_grupo['Quant.']).round(2)
    
    # Ordenar por faturamento
    df_grupo = df_grupo.sort_values('Vlr.Líquido', ascending=False)
    
    return df_grupo

def obter_top_produtos(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Obtém top N produtos"""
    df_produtos = df.groupby(['Produto', 'Grupo']).agg({
        'Vlr.Líquido': 'sum',
        '$ Margem': 'sum',
        'Quant.': 'sum'
    }).reset_index()
    
    df_produtos['% Margem'] = (df_produtos['$ Margem'] / df_produtos['Vlr.Líquido'] * 100).round(2)
    
    top = df_produtos.nlargest(n, 'Vlr.Líquido').copy()
    top['Ranking'] = range(1, len(top) + 1)
    
    return top[['Ranking', 'Produto', 'Grupo', 'Vlr.Líquido', '$ Margem', '% Margem', 'Quant.']]

# ============================================================================
# FUNÇÕES UTILITÁRIAS
# ============================================================================
def format_currency_br(valor) -> str:
    """Formata número no padrão monetário brasileiro: R$ 1.234.567,89"""
    try:
        return (
            f"R$ {float(valor):,.2f}"  # 1,234,567.89
            .replace(",", "X")        # 1X234X567.89
            .replace(".", ",")        # 1X234X567,89
            .replace("X", ".")        # 1.234.567,89
        )
    except Exception:
        return str(valor)

# ============================================================================
# FUNÇÕES DE ANÁLISE
# ============================================================================
def calcular_previsao_vendas(df_mensal: pd.DataFrame, periodos_futuros: int = 3) -> tuple:
    """Calcula previsão usando regressão polinomial"""
    df_mensal_completo = df_mensal.copy()
    df_mensal_completo['Mês_Num'] = range(1, len(df_mensal_completo) + 1)
    
    X = df_mensal_completo['Mês_Num'].values.reshape(-1, 1)
    y = df_mensal_completo['Vlr.Líquido'].values
    
    # Modelo Polinomial
    poly_features = PolynomialFeatures(degree=2)
    X_poly = poly_features.fit_transform(X)
    
    modelo = LinearRegression()
    modelo.fit(X_poly, y)
    
    # Calcular R²
    y_pred = modelo.predict(X_poly)
    r2 = r2_score(y, y_pred)
    
    # Fazer previsões
    meses_futuros = np.array([[i] for i in range(len(df_mensal_completo) + 1, 
                                                   len(df_mensal_completo) + periodos_futuros + 1)])
    previsoes = modelo.predict(poly_features.transform(meses_futuros))
    
    # Criar DataFrame
    meses_nomes = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                   'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    
    ultimo_mes = df_mensal_completo['Mês'].iloc[-1]
    
    nomes_previsao = []
    for i in range(periodos_futuros):
        mes_idx = (ultimo_mes + i) % 12
        if mes_idx == 0:
            mes_idx = 12
        nomes_previsao.append(meses_nomes[mes_idx - 1])
    
    df_previsao = pd.DataFrame({
        'Mês': nomes_previsao,
        'Previsão': previsoes,
        'Tipo': 'Previsão'
    })
    
    df_historico = df_mensal_completo[['Nome do Mês', 'Vlr.Líquido']].copy()
    df_historico.columns = ['Mês', 'Previsão']
    df_historico['Tipo'] = 'Real'
    
    df_completo = pd.concat([df_historico, df_previsao], ignore_index=True)
    
    metricas = {
        'r2': float(r2),
        'media_historica': float(y.mean()),
        'previsoes': previsoes.tolist()
    }
    
    return df_completo, metricas

def calcular_media_movel(df_mensal: pd.DataFrame, janela: int = 3) -> pd.DataFrame:
    """Calcula média móvel"""
    df = df_mensal.copy()
    df['Média Móvel'] = df['Vlr.Líquido'].rolling(window=janela).mean()
    return df

def analisar_sazonalidade(df_mensal: pd.DataFrame) -> dict:
    """Analisa padrões de sazonalidade"""
    media = df_mensal['Vlr.Líquido'].mean()
    
    df_analise = df_mensal.copy()
    df_analise['Desvio %'] = ((df_analise['Vlr.Líquido'] - media) / media * 100).round(2)
    
    mes_pico = df_analise.loc[df_analise['Vlr.Líquido'].idxmax()]
    mes_baixa = df_analise.loc[df_analise['Vlr.Líquido'].idxmin()]
    
    return {
        'dados': df_analise,
        'media': float(media),
        'mes_pico': {
            'nome': mes_pico['Nome do Mês'],
            'valor': float(mes_pico['Vlr.Líquido']),
            'desvio': float(mes_pico['Desvio %'])
        },
        'mes_baixa': {
            'nome': mes_baixa['Nome do Mês'],
            'valor': float(mes_baixa['Vlr.Líquido']),
            'desvio': float(mes_baixa['Desvio %'])
        },
        'amplitude': float(mes_pico['Vlr.Líquido'] - mes_baixa['Vlr.Líquido'])
    }

# ============================================================================
# FUNÇÕES DE VISUALIZAÇÃO
def criar_grafico_margem(df_grupo: pd.DataFrame) -> go.Figure:
    """Gráfico comparativo vendas vs margem"""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df_grupo['Grupo'],
        x=df_grupo['Vlr.Líquido'],
        name='Vendas',
        orientation='h',
        marker_color=COLORS['primary']
    ))
    fig.add_trace(go.Bar(
        y=df_grupo['Grupo'],
        x=df_grupo['$ Margem'],
        name='Margem',
        orientation='h',
        marker_color=COLORS['secondary']
    ))
    fig.update_layout(
        title='Comparativo: Vendas vs Margem',
        xaxis_title='Valor (R$)',
        barmode='group',
        height=400,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', y=1.1)
    )
    return fig
# ============================================================================
def criar_grafico_barras_grupo(df_grupo: pd.DataFrame) -> go.Figure:
    """Gráfico de barras por grupo"""
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df_grupo['Grupo'],
        y=df_grupo['Vlr.Líquido'],
        marker_color=COLORS['primary'],
        text=df_grupo['Vlr.Líquido'].apply(lambda x: f'R$ {x/1e6:.1f}M'),
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Vendas: R$ %{y:,.0f}<extra></extra>'
    ))
    
    fig.update_layout(
        xaxis_title='Grupo',
        yaxis_title='Faturamento (R$)',
        height=600,
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    fig.update_xaxes(tickangle=-45)
    fig.update_yaxes(gridcolor='lightgray')
    
    return fig

def criar_grafico_pizza(df_grupo: pd.DataFrame) -> go.Figure:
    """Gráfico de pizza participação"""
    fig = go.Figure()
    
    fig.add_trace(go.Pie(
        labels=df_grupo['Grupo'],
        values=df_grupo['Participação %'],
        marker=dict(colors=COLOR_SEQUENCE),
        textinfo='label+percent',
        hovertemplate='<b>%{label}</b><br>Participação: %{value:.2f}%<extra></extra>'
    ))
    
    fig.update_layout(
        height=600,
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def criar_grafico_pizza(df: pd.DataFrame) -> go.Figure:
    """Gráfico de pizza participação por Atividade"""
    # Agrupar por Atividade
    df_atividade = df.groupby('Atividade').agg({'Vlr.Líquido': 'sum'}).reset_index()
    total_vendas = df_atividade['Vlr.Líquido'].sum()
    df_atividade['Participação %'] = (df_atividade['Vlr.Líquido'] / total_vendas * 100).round(2)

    # Separar atividades acima de 1% e agrupar o restante como 'Outros'
    atividades_principais = df_atividade[df_atividade['Participação %'] > 1].copy()
    atividades_outros = df_atividade[df_atividade['Participação %'] <= 1].copy()
    if not atividades_outros.empty:
        outros_row = pd.DataFrame({
            'Atividade': ['Outros'],
            'Vlr.Líquido': [atividades_outros['Vlr.Líquido'].sum()],
            'Participação %': [atividades_outros['Participação %'].sum()]
        })
        atividades_principais = pd.concat([atividades_principais, outros_row], ignore_index=True)

    # Ordenar por participação decrescente
    atividades_principais = atividades_principais.sort_values('Participação %', ascending=False)

    fig = go.Figure()
    fig.add_trace(go.Pie(
        labels=atividades_principais['Atividade'],
        values=atividades_principais['Participação %'],
        marker=dict(colors=COLOR_SEQUENCE),
        textinfo='label+percent',
        hovertemplate='<b>%{label}</b><br>Participação: %{value:.2f}%<extra></extra>'
    ))
    fig.update_layout(
        height=600,
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig
    
    fig.update_layout(
        title='Comparativo: Vendas vs Margem',
        xaxis_title='Valor (R$)',
        barmode='group',
        height=400,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', y=1.1)
    )
    
    return fig

def criar_grafico_previsao(df_completo: pd.DataFrame, metricas: dict) -> go.Figure:
    """Gráfico de previsão"""
    fig = go.Figure()
    
    df_real = df_completo[df_completo['Tipo'] == 'Real']
    fig.add_trace(go.Scatter(
        x=df_real['Mês'],
        y=df_real['Previsão'],
        name='Histórico',
        mode='lines',
        line=dict(color=COLORS['primary'], width=3),
        fill='tozeroy',
        fillcolor='rgba(59, 130, 246, 0.2)'
    ))
    
    df_prev = df_completo[df_completo['Tipo'] == 'Previsão']
    if not df_prev.empty:
        fig.add_trace(go.Scatter(
            x=df_prev['Mês'],
            y=df_prev['Previsão'],
            name='Previsão',
            mode='lines+markers',
            line=dict(color=COLORS['tertiary'], width=3, dash='dash'),
            marker=dict(size=8)
        ))
    
    fig.update_layout(
        title=f'Histórico e Previsão de Vendas (R² = {metricas["r2"]:.3f})',
        xaxis_title='Mês',
        yaxis_title='Faturamento (R$)',
        height=450,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', y=1.1)
    )
    
    fig.update_xaxes(tickangle=-45)
    fig.update_yaxes(gridcolor='lightgray')
    
    return fig

def criar_grafico_sazonalidade(df_mensal: pd.DataFrame, df_media_movel: pd.DataFrame) -> go.Figure:
    """Gráfico de sazonalidade"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_mensal['Nome do Mês'],
        y=df_mensal['Vlr.Líquido'],
        name='Vendas Mensais',
        mode='lines+markers',
        line=dict(color=COLORS['primary'], width=3),
        marker=dict(size=8)
    ))
    
    if 'Média Móvel' in df_media_movel.columns:
        fig.add_trace(go.Scatter(
            x=df_media_movel['Nome do Mês'],
            y=df_media_movel['Média Móvel'],
            name='Média Móvel (3M)',
            mode='lines',
            line=dict(color=COLORS['tertiary'], width=2, dash='dash')
        ))
    
    fig.update_layout(
        title='Análise de Sazonalidade Mensal',
        xaxis_title='Mês',
        yaxis_title='Faturamento (R$)',
        height=450,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', y=1.15)
    )
    
    fig.update_xaxes(tickangle=-45)
    fig.update_yaxes(gridcolor='lightgray')
    
    return fig

# ============================================================================
# INTERFACE PRINCIPAL
# ============================================================================

# ================================
# LÓGICA DE ROLE/SETOR NO INÍCIO DO CÓDIGO
# ================================
st.title("🧠 Inteligência Comercial - Dashboard Executivo")

# ⚠️ AVISO DE DESENVOLVIMENTO
st.warning("""
⚠️ **PÁGINA EM DESENVOLVIMENTO** ⚠️  
Esta página ainda está em fase de desenvolvimento e testes.  
**Os dados apresentados NÃO devem ser considerados para tomada de decisões.**  
Aguarde a versão final para uso oficial.
""")

st.markdown("""
Este dashboard apresenta análises completas de vendas:
- 📈 **Tendência por Atividade**: Performance por grupo comercial
- 🔮 **Previsão de Vendas**: Forecast baseado em modelo estatístico
- 🌊 **Sazonalidade**: Padrões e ciclos de vendas
""")

# Padronização visual das métricas (remover bordas inconsistentes entre colunas)
st.markdown("---")

# Lógica de role/setor
user_role = st.session_state.get("role", [])
username = st.session_state.get("username", "Usuário Desconhecido")

role = None

if "Admin" in user_role or "Consultor" in user_role:
    setores = ["Indústria", "Varejo", "Exportação", "Admin (todas equipes)"]
    setor_base = st.selectbox("Selecione o setor", setores)
    if setor_base == "Varejo":
        st.markdown("---")
        role = "Varejo"
    elif setor_base == "Indústria":
        role = "Indústria"
    elif setor_base == "Exportação":
        role = "Exportação"
    else:
        role = "Admin (todas equipes)"

elif "Gerente Indústria" in user_role or "Indústria" in user_role:
    role = "Indústria"
    st.markdown(f"#### Setor: Indústria")

elif "Gerente Varejo" in user_role or "Varejo" in user_role:
    st.markdown("#### Setor: Varejo")
    role = "Varejo"
else:
    st.error("Acesso negado. Você não tem permissão para visualizar esta página.")
    st.stop()

# Função para mapear role para setor
def mapear_role_para_setor_meta(role):
    if role == "Indústria":
        return "Indústria"
    elif role == "Varejo":
        return "Varejo"
    elif role == "Exportação":
        return "Exportação"
    elif role == "Exportação Varejo":
        return "Exportação Varejo"
    else:
        return None

# Filtro de equipe para uso nos DataFrames
if role == "Indústria":
    filtro_equipe = "INDUSTRIAL"
elif role == "Varejo":
    filtro_equipe = "VAREJO"
elif role == "Exportação":
    filtro_equipe = ["EXPORTAÇÃO VAREJO", "EXPORTAÇÃO INDUSTRIA"]
else:  # Admin (todas equipes)
    filtro_equipe = None

# ============================================================================
# SELEÇÃO DE PERÍODO
# ============================================================================

# ================================
# FILTRO AUTOMÁTICO DE ANO ATUAL E ANTERIOR
# ================================
hoje = datetime.now()
ano_atual = hoje.year
ano_passado = ano_atual - 1

# Carregar dados do ano atual e anterior
data_inicio_atual = date(ano_atual, 1, 1)
data_fim_atual = date(ano_atual, 12, 31)
data_inicio_passado = date(ano_passado, 1, 1)
data_fim_passado = date(ano_passado, 12, 31)

data_inicio_str = data_inicio_atual.strftime('%Y-%m-%d')
data_fim_str = data_fim_atual.strftime('%Y-%m-%d')
data_inicio_passado_str = data_inicio_passado.strftime('%Y-%m-%d')
data_fim_passado_str = data_fim_passado.strftime('%Y-%m-%d')

# ============================================================================
# CARREGAMENTO DE DADOS
# ============================================================================

# Carregar dados dos dois anos
with st.spinner("📊 Carregando dados do banco para anos atual e anterior..."):
    try:
        df_raw_atual = carregar_dados_banco(data_inicio_str, data_fim_str)
        df_raw_passado = carregar_dados_banco(data_inicio_passado_str, data_fim_passado_str)

        # Aplicar filtro de equipe
        if isinstance(filtro_equipe, list):
            if 'Equipe' in df_raw_atual.columns:
                df_raw_atual = df_raw_atual[df_raw_atual['Equipe'].isin(filtro_equipe)]
            if 'Equipe' in df_raw_passado.columns:
                df_raw_passado = df_raw_passado[df_raw_passado['Equipe'].isin(filtro_equipe)]
        elif filtro_equipe and 'Equipe' in df_raw_atual.columns:
            df_raw_atual = df_raw_atual[df_raw_atual['Equipe'] == filtro_equipe]
            if 'Equipe' in df_raw_passado.columns:
                df_raw_passado = df_raw_passado[df_raw_passado['Equipe'] == filtro_equipe]
        # Se não houver coluna 'Equipe', mantém todos os dados

        # Unir os dois anos para análises comparativas e previsões
        df_raw = pd.concat([df_raw_passado, df_raw_atual], ignore_index=True)

        # Processar dados do ano atual
        df_mensal = processar_dados_mensais(df_raw_atual)
        df_grupo = processar_dados_grupo(df_raw_atual)
        df_top_produtos = obter_top_produtos(df_raw_atual, n=10)

        # Calcular estatísticas do ano atual
        total_vendas = float(df_mensal['Vlr.Líquido'].sum())
        total_margem = float(df_mensal['$ Margem'].sum())
        margem_percentual = (total_margem / total_vendas * 100)
        media_mensal = float(df_mensal['Vlr.Líquido'].mean())
        total_produtos = len(df_raw_atual['Produto'].unique())

        st.success(f"✅ Dados carregados para {ano_atual} e {ano_passado}!")

    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {str(e)}")
        st.stop()

# ============================================================================
# KPIS PRINCIPAIS
# ============================================================================
st.header("📊 Indicadores-Chave de Performance")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("💰 Total de Vendas", f"R$ {total_vendas/1e6:.2f}M")

with col2:
    st.metric("📈 Margem Total", f"R$ {total_margem/1e6:.2f}M", delta=f"{margem_percentual:.1f}%")

with col3:
    st.metric("📊 Média Mensal", f"R$ {media_mensal/1e6:.2f}M")

with col4:
    st.metric("📦 Total de Produtos", f"{total_produtos}")

st.markdown("---")

# ============================================================================
# ABAS DE ANÁLISE
# ============================================================================
tab1, tab2, tab3 = st.tabs([
    "📈 Tendência por Atividade",
    "🔮 Previsão de Vendas",
    "🌊 Sazonalidade"
])

# TAB 1: TENDÊNCIA
with tab1:
    st.header("📈 Tendência de Crescimento por Grupo")
    
    st.subheader("Participação de Mercado por Atividade")
    fig_pizza = criar_grafico_pizza(df_raw_atual)
    st.plotly_chart(fig_pizza, use_container_width=True)

    # DataFrame detalhado de participação de mercado por atividade
    df_atividade = df_raw_atual.groupby('Atividade').agg({
        'Total NF': 'sum',
        'Vlr.Líquido': 'sum',
        '$ Margem': 'sum'
    }).reset_index()
    total_vendas_atividade = df_atividade['Vlr.Líquido'].sum()
    df_atividade['Participação %'] = (df_atividade['Vlr.Líquido'] / total_vendas_atividade * 100).round(2)
    df_atividade = df_atividade.sort_values('Participação %', ascending=False)

    st.subheader("📊 Detalhamento de Participação de Mercado")
    st.dataframe(df_atividade, use_container_width=True, hide_index=True)

# TAB 2: PREVISÃO
with tab2:
    st.header("🔮 Previsão de Vendas")

    # Seletor de período para previsão otimista
    st.subheader("Configuração da Previsão")
    periodos_opcoes = {
        "3 meses": 3,
        "6 meses": 6,
        "12 meses": 12
    }
    periodo_selecionado = st.selectbox("Selecione o horizonte da previsão otimista:", list(periodos_opcoes.keys()), index=0)
    periodos_previsao = periodos_opcoes[periodo_selecionado]

    # Previsão baseada em dados do ano atual e anterior, excluindo o mês atual
    hoje = datetime.now()
    mes_atual = hoje.month
    ano_atual = hoje.year

    # Dados do histórico (ano atual, excluindo mês atual)
    df_mensal_historico = processar_dados_mensais(df_raw_atual)
    df_mensal_historico_filtrado = df_mensal_historico[
        ~((df_mensal_historico['Ano'] == ano_atual) & (df_mensal_historico['Mês'] == mes_atual))
    ].copy()

    # Dados para previsão (ano atual + anterior, excluindo mês atual)
    df_raw_previsao = pd.concat([df_raw_passado, df_raw_atual], ignore_index=True)
    df_mensal_previsao = processar_dados_mensais(df_raw_previsao)
    df_mensal_previsao_filtrado = df_mensal_previsao[
        ~((df_mensal_previsao['Ano'] == ano_atual) & (df_mensal_previsao['Mês'] == mes_atual))
    ].copy()

    with st.spinner("Calculando previsões..."):
        df_completo, metricas = calcular_previsao_vendas(df_mensal_previsao_filtrado, periodos_previsao)

    # Substituir histórico por dados do ano atual (sem mês atual)
    df_historico_atual = df_mensal_historico_filtrado[['Nome do Mês', 'Vlr.Líquido']].copy()
    df_historico_atual.columns = ['Mês', 'Previsão']
    df_historico_atual['Tipo'] = 'Real'
    # Filtrar previsões
    df_previsao = df_completo[df_completo['Tipo'] == 'Previsão'].copy().reset_index(drop=True)
    # Concatenar histórico do ano atual com previsões (para o gráfico)
    df_completo_grafico = pd.concat([df_historico_atual, df_previsao], ignore_index=True)

    fig_previsao = criar_grafico_previsao(df_completo_grafico, metricas)
    st.plotly_chart(fig_previsao, use_container_width=True)

    # =========================
    # 📅 Previsão Detalhada por Mês (AJUSTADA)
    # =========================
    st.subheader("📅 Previsão Detalhada por Mês")

    # Mapeamento de meses
    meses_nomes_map = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
        7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    # Descobrir índice do último mês histórico exibido
    ultimo_mes_hist_nome = df_historico_atual['Mês'].iloc[-1]
    ultimo_mes_hist_idx = next(k for k, v in meses_nomes_map.items() if v == ultimo_mes_hist_nome)

    # Construir labels mês-ano exclusivamente pela sequência prevista (df_previsao)
    ano_corrente = ano_atual
    mes_corrente = ultimo_mes_hist_idx
    meses_disponiveis = []

    for _ in range(len(df_previsao)):
        mes_corrente += 1
        if mes_corrente > 12:
            mes_corrente = 1
            ano_corrente += 1
        meses_disponiveis.append(f"{meses_nomes_map[mes_corrente]} - {ano_corrente}")

    # Lista suspensa (ordem já corresponde à ordem dos previstos)
    mes_selecionado = st.selectbox("Selecione o mês para ver a previsão:", meses_disponiveis)
    idx_mes = meses_disponiveis.index(mes_selecionado)

    if 0 <= idx_mes < len(df_previsao):
        row = df_previsao.iloc[idx_mes]
        variacao = ((row['Previsão'] / metricas['media_historica']) - 1) * 100

        cols = st.columns(3)
        with cols[0]:
            st.metric(
                label=f"📆 {mes_selecionado}",
                value=f"R$ {row['Previsão']/1e6:.2f}M",
                delta=f"{variacao:+.1f}% vs média"
            )
        with cols[1]:
            st.metric("R² Score", f"{metricas['r2']:.3f}")
        with cols[2]:
            st.metric("Média Histórica", f"R$ {metricas['media_historica']/1e6:.2f}M")
    else:
        st.warning("Não há dados de previsão disponíveis para o mês selecionado.")

# TAB 3: SAZONALIDADE
with tab3:
    st.header("🌊 Análise de Sazonalidade")
    
    df_media_movel = calcular_media_movel(df_mensal, janela=3)
    sazonalidade = analisar_sazonalidade(df_mensal)
    
    fig_sazonalidade = criar_grafico_sazonalidade(df_mensal, df_media_movel)
    st.plotly_chart(fig_sazonalidade, use_container_width=True)
    
    st.subheader("📊 Padrões Identificados")
    
    col1, col2 = st.columns(2)

    with col1:
        st.success(f"""
        **🔝 Mês de Pico**  
        {sazonalidade['mes_pico']['nome']}  
        R$ {sazonalidade['mes_pico']['valor']/1e6:.2f}M  
        ({sazonalidade['mes_pico']['desvio']:+.1f}% vs média)
        """)

    with col2:
        st.error(f"""
        **📉 Mês de Baixa**  
        {sazonalidade['mes_baixa']['nome']}  
        R$ {sazonalidade['mes_baixa']['valor']/1e6:.2f}M  
        ({sazonalidade['mes_baixa']['desvio']:+.1f}% vs média)
        """)
    
    st.subheader("🏆 Top 10 Produtos")
    # Formatar colunas monetárias no padrão brasileiro
    df_top_produtos_fmt = df_top_produtos.copy()
    if 'Vlr.Líquido' in df_top_produtos_fmt.columns:
        df_top_produtos_fmt['Vlr.Líquido'] = df_top_produtos_fmt['Vlr.Líquido'].apply(format_currency_br)
    if '$ Margem' in df_top_produtos_fmt.columns:
        df_top_produtos_fmt['$ Margem'] = df_top_produtos_fmt['$ Margem'].apply(format_currency_br)
    st.dataframe(df_top_produtos_fmt, use_container_width=True, hide_index=True)

# ============================================================================
# RODAPÉ
# ============================================================================
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p><strong>Dashboard de Inteligência Comercial</strong></p>
    <p>Período: 01/01/{ano_atual} a 31/12/{ano_atual}</p>
    <p>Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
</div>
""", unsafe_allow_html=True)
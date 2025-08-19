from functions.menu import menu_with_redirect
import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go
from calendar import monthrange
from functions.query import run_query
from functions.query_devo import run_query as run_query_devo
from functions.query_ped import run_query as run_query_ped
from functions.func_margem import grafico_margem, dataframe_margem
from functions.gerar_html_vendas import gerar_html_relatorio_vendas, criar_html_simples_vendas
import requests
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente para acessar API de metas
load_dotenv()
url_api = os.getenv("url_api")

st.set_page_config(layout="wide", page_title="Visão Geral de Vendas")
menu_with_redirect()

st.title("📊 Visão Geral de Vendas")

# Padronização visual das métricas (remover bordas inconsistentes entre colunas)
st.markdown(
    """
    <style>
    /* Uniformizar todos os st.metric */
    div[data-testid="metric-container"] {
        border: 0 !important;
        background: transparent !important;
        padding: 0.25rem 0.75rem !important;
        box-shadow: none !important;
    }
    /* Ajuste do texto para consistência */
    div[data-testid="metric-container"] > label p {
        font-weight: 600 !important;
        margin-bottom: 0.25rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ===========================================
# LÓGICA DE ROLE/SETOR NO INÍCIO DO CÓDIGO
# ===========================================
user_role = st.session_state.get("role", [])
username = st.session_state.get("username", "Usuário Desconhecido")

role = None

if "Admin" in user_role:
    setores = ["Indústria", "Varejo", "Admin (todas equipes)"]
    setor_base = st.selectbox("Selecione o setor", setores)
    if setor_base == "Varejo":
        st.markdown("---")
        role = st.radio(
            "Selecione o tipo de operação Varejo:",
            ["Varejo", "Exportação Varejo"],
            horizontal=True,
            key="sub_setor_admin"
        )
    elif setor_base == "Indústria":
        role = setor_base
    else:
        role = "Admin (todas equipes)"

elif "Gerente Indústria" in user_role or "Indústria" in user_role:
    role = "Indústria"
    st.markdown("#### Setor: Indústria")

elif "Gerente Varejo" in user_role or "Varejo" in user_role:
    st.markdown("#### Setor: Varejo")
    role = st.radio(
        "Selecione o tipo de operação:",
        ["Varejo", "Exportação Varejo"],
        horizontal=True,
        key="sub_setor_varejo"
    )
else:
    st.error("Acesso negado. Você não tem permissão para visualizar esta página.")
    st.stop()

# Função para mapear role para setor da API de metas
def mapear_role_para_setor_meta(role):
    """Mapeia o role selecionado para o setor correto da API de metas"""
    if role == "Indústria":
        return "Indústria"
    elif role == "Varejo":
        return "Varejo" 
    elif role == "Exportação Varejo":
        return "Exportação Varejo"
    else:  # Admin (todas equipes)
        return None  # Não há meta consolidada para todas as equipes

# Função para buscar meta de um mês específico
@st.cache_data(ttl=1200)
def buscar_meta_mensal(mes, ano, setor):
    """Busca a meta de um mês específico na API"""
    if not url_api or not setor:
        return 0.0
    
    try:
        params = {"mes": mes, "ano": ano, "setor": setor}
        response = requests.get(f"{url_api}/metas/buscar", params=params)
        if response.status_code == 200:
            return float(response.json().get("valor", 0.0))
    except requests.exceptions.RequestException:
        pass  # API indisponível, retorna 0
    return 0.0

# Função para buscar metas anuais
@st.cache_data(ttl=1200)
def buscar_metas_anuais(ano, setor):
    """Busca todas as metas de um ano da API"""
    if not url_api or not setor:
        return {}
    
    try:
        params = {"ano": ano, "setor": setor}
        response = requests.get(f"{url_api}/metas/anual", params=params)
        if response.status_code == 200:
            dados_api = response.json()
            metas_dict = dados_api.get("metas", {})
            # Converter chaves para int e valores para float
            return {int(k): float(v) for k, v in metas_dict.items()}
    except requests.exceptions.RequestException:
        pass  # API indisponível, retorna dict vazio
    return {}

# ================================
# Filtros de tempo
# ================================
hoje = datetime.now()
ano_atual = hoje.year
mes_atual = hoje.month
anos_disponiveis = list(range(ano_atual - 5, ano_atual + 1))
meses = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

col1, col2 = st.columns([2, 1])
with col2:
    st.markdown("### Ano")
    ano = st.selectbox(
    "Ano",
        options=anos_disponiveis,
        index=anos_disponiveis.index(ano_atual),
    key="select_ano",
    label_visibility="collapsed"
    )

if ano == ano_atual:
    meses_disponiveis = list(range(1, mes_atual + 1))
else:
    meses_disponiveis = list(range(1, 13))

with col1:
    st.markdown("### Mês")
    mes = st.selectbox(
    "Mês",
        options=meses_disponiveis,
        format_func=lambda m: meses[m - 1],
        index=meses_disponiveis.index(mes_atual) if ano == ano_atual else 0,
    key="select_mes",
    label_visibility="collapsed"
    )

# ================================
# Função cacheada - carrega tudo SEM filtro de setor
# ================================
@st.cache_data(ttl=1200)
def buscar_dados_periodo(ano: int):
    inicio = date(ano - 1, 1, 1)
    fim = date(ano, 12, 31)
    df = run_query(inicio.strftime("%Y-%m-%d"), fim.strftime("%Y-%m-%d"))
    df['Data'] = pd.to_datetime(df['Data'])
    df['Mês'] = df['Data'].dt.month
    df['Ano'] = df['Data'].dt.year

    df_devo = run_query_devo(inicio.strftime("%Y-%m-%d"), fim.strftime("%Y-%m-%d"))
    df_devo['Mês'] = pd.to_datetime(df_devo['DATA']).dt.month
    df_devo['Ano'] = pd.to_datetime(df_devo['DATA']).dt.year

    return df, df_devo

# NOVA FUNÇÃO: pedidos apenas do ano selecionado
@st.cache_data(ttl=1200)
def buscar_pedidos_ano(ano: int, permissoes: list):
    inicio = date(ano, 1, 1)
    fim = date(ano, 12, 31)
    df_ped = run_query_ped(inicio.strftime("%Y-%m-%d"), fim.strftime("%Y-%m-%d"), situacoes=permissoes)
    if not df_ped.empty:
        df_ped['Data'] = pd.to_datetime(df_ped['DATA'])
        df_ped['Mês'] = df_ped['Data'].dt.month
        df_ped['Ano'] = df_ped['Data'].dt.year
    return df_ped

# Carrega dados
with st.spinner("🔄 Carregando dados... (o banco só será consultado se mudar o ano)"):
    df_periodo_all, df_devo_all = buscar_dados_periodo(ano)
    permissoes = ['Encerrado', 'Liberado']
    df_pedidos_all = buscar_pedidos_ano(ano, permissoes)

# ========================================
# Aplique o filtro de setor apenas em RAM
# ========================================
if role == "Indústria":
    filtro_equipe = "INDUSTRIAL"
elif role == "Varejo":
    filtro_equipe = "VAREJO"
elif role == "Exportação Varejo":
    filtro_equipe = "EXPORTAÇÃO VAREJO"
else:  # Admin (todas equipes)
    filtro_equipe = None

# Filtro na principal (query comum)
if filtro_equipe and 'Equipe' in df_periodo_all.columns:
    df = df_periodo_all[df_periodo_all['Equipe'] == filtro_equipe]
else:
    df = df_periodo_all.copy()

# Filtro na QUERY_DEVO (usando EQUIPE e mesmo valor do filtro_equipe)
if filtro_equipe and 'EQUIPE' in df_devo_all.columns:
    df_devo = df_devo_all[df_devo_all['EQUIPE'] == filtro_equipe]
else:
    df_devo = df_devo_all.copy()

# ================================
# Filtros por ano e mês
# ================================
df_atual = df[df['Ano'] == ano]
prev_year = ano - 1
df_prev = df[df['Ano'] == prev_year]
df_mes = df_atual[df_atual['Mês'] == mes]

if df_mes.empty:
    st.warning(f"Não há dados para {meses[mes - 1]} de {ano}.")
    st.stop()

st.divider()

# ========================
# KPIS PRINCIPAIS
# ========================
st.subheader("📈 Indicadores Principais")

# Filtrar apenas vendas (sem devoluções)
df_vendas = df_mes[df_mes['Flag tipo'] == 'V']
df_devolucoes = df_mes[df_mes['Flag tipo'] == 'D'] 

# Cálculos baseados na mesma lógica da margem_cont.py
total_vendas = df_vendas['Total NF'].sum()
total_devolucoes_normais = df_devolucoes['Total NF'].sum()

# Devoluções extras (da query_devo)
df_devo_mes_extra = df_devo[(df_devo['Ano'] == ano) & (df_devo['Mês'] == mes)] if not df_devo.empty else pd.DataFrame()
devo_extra_mes = df_devo_mes_extra['TOTAL_MERCADORIA'].sum() if not df_devo_mes_extra.empty else 0
total_devolucoes_completo = total_devolucoes_normais + abs(devo_extra_mes)
fat_liquido = total_vendas - total_devolucoes_completo

# CMV e Margem
total_cmv = df_vendas['Vlr.ICM'].sum()
total_margem = df_vendas['$ Margem'].sum()

# Dados do ano anterior para comparação
vend_prev_mes = df_prev[df_prev['Flag tipo'] == 'V'].groupby('Mês')['Total NF'].sum().get(mes, 0)
dev_prev_mes = df_prev[df_prev['Flag tipo'] == 'D'].groupby('Mês')['Total NF'].sum().get(mes, 0)
devo_extra_mes_prev = df_devo[(df_devo['Ano'] == prev_year) & (df_devo['Mês'] == mes)]['TOTAL_MERCADORIA'].sum() if not df_devo.empty else 0
total_devolucoes_prev_completo = dev_prev_mes + abs(devo_extra_mes_prev)
fat_liq_prev_mes = vend_prev_mes - total_devolucoes_prev_completo

total_cmv_prev = df_prev[(df_prev['Mês'] == mes) & (df_prev['Flag tipo'] == 'V')]['Vlr.ICM'].sum()
total_margem_prev = df_prev[(df_prev['Mês'] == mes) & (df_prev['Flag tipo'] == 'V')]['$ Margem'].sum()

# Cálculo dos deltas
delta_total_vendas = total_vendas - vend_prev_mes
delta_total_devolucoes_completo = total_devolucoes_completo - total_devolucoes_prev_completo
delta_fat_liquido = fat_liquido - fat_liq_prev_mes
delta_total_cmv = total_cmv - total_cmv_prev
delta_total_margem = total_margem - total_margem_prev

# Buscar dados de pedidos
@st.cache_data(ttl=1200)
def buscar_dados_pedidos(ano: int, permissoes: list):
    inicio = date(ano - 1, 1, 1)
    fim = date(ano, 12, 31)
    df_pedidos = run_query_ped(inicio.strftime("%Y-%m-%d"), fim.strftime("%Y-%m-%d"), situacoes=permissoes)
    df_pedidos['Data'] = pd.to_datetime(df_pedidos['DATA'])
    df_pedidos['Mês'] = df_pedidos['Data'].dt.month
    df_pedidos['Ano'] = df_pedidos['Data'].dt.year
    return df_pedidos

permissoes = ['Encerrado', 'Liberado']
df_pedidos = buscar_dados_pedidos(ano, permissoes)

# Filtro por datas do mês
primeiro_dia = date(ano, mes, 1)
ultimo_dia = date(ano, mes, monthrange(ano, mes)[1])
if not df_pedidos_all.empty:
    df_pedidos_mes = df_pedidos_all[(df_pedidos_all['Data'] >= pd.Timestamp(primeiro_dia)) & (df_pedidos_all['Data'] <= pd.Timestamp(ultimo_dia))]
    if filtro_equipe and 'EQUIPE' in df_pedidos_mes.columns:
        df_pedidos_mes = df_pedidos_mes[df_pedidos_mes['EQUIPE'] == filtro_equipe]
    total_pedidos_mes = df_pedidos_mes['ID_PEDIDO'].nunique() if 'ID_PEDIDO' in df_pedidos_mes.columns else 0
else:
    total_pedidos_mes = 0

# Pedidos do ano anterior
df_pedidos_prev_mes = df_pedidos[
    (df_pedidos['Data'] >= pd.Timestamp(date(prev_year, mes, 1))) &
    (df_pedidos['Data'] <= pd.Timestamp(date(prev_year, mes, monthrange(prev_year, mes)[1])))
]
if filtro_equipe and 'EQUIPE' in df_pedidos_prev_mes.columns:
    df_pedidos_prev_mes = df_pedidos_prev_mes[df_pedidos_prev_mes['EQUIPE'] == filtro_equipe]

total_pedidos_prev = df_pedidos_prev_mes['ID_PEDIDO'].nunique() if 'ID_PEDIDO' in df_pedidos_prev_mes.columns else 0
delta_pedidos = total_pedidos_mes - total_pedidos_prev

col1, col2, col3 = st.columns(3)
col4, col5, col6 = st.columns(3)

with col1:
    st.metric(
        "Total Faturado", 
        f"R$ {total_vendas:,.2f}",
        f"R$ {delta_total_vendas:,.2f}",
        delta_color="normal" if delta_total_vendas >= 0 else "inverse"
    )

with col2:
    st.metric(
        "Total Devoluções", 
        f"R$ {total_devolucoes_completo:,.2f}",
        f"R$ {delta_total_devolucoes_completo:,.2f}",
        delta_color="normal" if delta_total_devolucoes_completo >= 0 else "inverse"
    )

with col3:
    st.metric(
        "Total Faturado Líquido", 
        f"R$ {fat_liquido:,.2f}", 
        f"R$ {delta_fat_liquido:,.2f}", 
        delta_color="normal" if delta_fat_liquido >= 0 else "inverse"
    )

with col4:
    st.metric(
        "Total CMV", 
        f"R$ {total_cmv:,.2f}",
        f"R$ {delta_total_cmv:,.2f}",
        delta_color="normal" if delta_total_cmv >= 0 else "inverse"
    )

with col5:
    st.metric(
        "Total Margem", 
        f"R$ {total_margem:,.2f}",
        f"R$ {delta_total_margem:,.2f}",
        delta_color="normal" if delta_total_margem >= 0 else "inverse"
    )

with col6:
    st.metric(
        "Total Pedidos",
        f"{total_pedidos_mes:,}"
    )

st.divider()

# ========================================
# FATURAMENTO TOTAL
# ========================================
st.subheader("💰 Faturamento Total")

# Função para calcular faturamento líquido mensal (Vendas - Devoluções - Devoluções Extras)
def calcular_faturamento_liquido_mensal(df, df_devo, ano_filtro):
    df_ano = df[df['Ano'] == ano_filtro]
    vendas = df_ano[df_ano['Flag tipo'] == 'V'].groupby('Mês')['Total NF'].sum()
    dev_norm = df_ano[df_ano['Flag tipo'] == 'D'].groupby('Mês')['Total NF'].sum()
    extra = pd.Series(dtype=float)
    if df_devo is not None and not df_devo.empty:
        df_devo_ano = df_devo[df_devo['Ano'] == ano_filtro]
        extra = df_devo_ano.groupby('Mês')['TOTAL_MERCADORIA'].sum().abs()
    return pd.Series({m: vendas.get(m, 0) - (dev_norm.get(m, 0) + extra.get(m, 0)) for m in range(1, 13)})

# Comparativo mensal detalhado
st.markdown("#### 📅 Comparativo Mensal")

with st.spinner("📊 Gerando gráfico comparativo detalhado..."):
    meses_range = meses_disponiveis
    meses_labels = [meses[m - 1] for m in meses_range]

    fat_prev_vendas = calcular_faturamento_liquido_mensal(df, df_devo, prev_year).loc[meses_range].tolist()
    fat_sel_vendas = calcular_faturamento_liquido_mensal(df, df_devo, ano).loc[meses_range].tolist()
    
    # Formatação brasileira dos valores (igual margem_cont.py)
    fmt_prev_vendas = [f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") for v in fat_prev_vendas]
    fmt_sel_vendas = [f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") for v in fat_sel_vendas]

    fig_comparativo = go.Figure()
    fig_comparativo.add_trace(go.Scatter(
        x=meses_labels,
        y=fat_prev_vendas,
        mode="lines+markers+text",
        name=str(prev_year),
        text=fmt_prev_vendas,
        textposition="bottom center",
        textfont=dict(size=12),
        line=dict(width=3, dash='dash'),
        marker=dict(size=6)
    ))
    fig_comparativo.add_trace(go.Scatter(
        x=meses_labels,
        y=fat_sel_vendas,
        mode="lines+markers+text",
        name=str(ano),
        text=fmt_sel_vendas,
        textposition="top center",
        textfont=dict(size=12),
        line=dict(width=3),
        marker=dict(size=6)
    ))
    fig_comparativo.update_layout(
        title=f"Faturamento Mensal (Líquido): {ano} vs {prev_year}",
        xaxis_title="Mês",
        yaxis_title="R$",
        margin=dict(l=40, r=40, t=50, b=40)
    )
    st.plotly_chart(fig_comparativo, use_container_width=True)

st.divider()

# ========================================
# FATURAMENTO POR CANAL
# ========================================
st.subheader("🏢 Faturamento por Canal")

col1, col2 = st.columns(2)

with col1:
    # Gráfico de pizza por atividade
    fat_canal = df_vendas.groupby('Atividade')['Total NF'].sum().reset_index()
    if not fat_canal.empty:
        fig_canal = px.pie(
            fat_canal, 
            values='Total NF', 
            names='Atividade',
            title='Faturamento por Canal'
        )
        fig_canal.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_canal, use_container_width=True)
    else:
        st.info("Sem dados de canal para o período selecionado")

with col2:
    # Tabela com valores
    if not fat_canal.empty:
        fat_canal_display = fat_canal.copy()
        fat_canal_display['Participação %'] = (fat_canal_display['Total NF'] / fat_canal_display['Total NF'].sum() * 100).round(2)
        fat_canal_display = fat_canal_display.rename(columns={'Total NF': 'Valor (R$)'})
        with st.expander("📋 Tabela Faturamento por Canal", expanded=False):
            st.dataframe(
                fat_canal_display[['Atividade', 'Valor (R$)', 'Participação %']], 
                hide_index=True,
                column_config={
                    "Valor (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                }
            )
        
        st.metric("Faturamento Total por Canal", f"R$ {fat_canal['Total NF'].sum():,.2f}")
    else:
        st.info("Sem dados para exibir")

st.divider()

# ========================================
# COMPARATIVO REAL X META
# ========================================
st.subheader("🎯 Comparativo Real x Meta")

setor_meta = mapear_role_para_setor_meta(role)
if setor_meta:  # Só mostra se houver setor válido para buscar meta
    
    # Buscar meta do mês atual
    meta_mensal = buscar_meta_mensal(mes, ano, setor_meta)
    
    if meta_mensal > 0:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Meta do Mês",
                f"R$ {meta_mensal:,.2f}"
            )
        
        with col2:
            percentual_atingido = (total_vendas / meta_mensal * 100) if meta_mensal > 0 else 0
            st.metric(
                "% Atingido",
                f"{percentual_atingido:.1f}%",
                delta_color="normal" if percentual_atingido >= 100 else "inverse"
            )
        
        with col3:
            diferenca_meta = total_vendas - meta_mensal
            st.metric(
                "Diferença",
                f"R$ {diferenca_meta:,.2f}",
                delta_color="normal" if diferenca_meta >= 0 else "inverse"
            )
        
        # Gráfico de progresso
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Barra de progresso visual
            progresso = min(percentual_atingido / 100, 1.0)  # Limita em 100% para a barra
            
            fig_meta = go.Figure()
            
            # Barra de meta (fundo)
            fig_meta.add_trace(go.Bar(
                x=[meta_mensal],
                y=['Meta'],
                orientation='h',
                name='Meta',
                marker_color='lightgray',
                width=0.5
            ))
            
            # Barra de realizado
            fig_meta.add_trace(go.Bar(
                x=[total_vendas],
                y=['Meta'],
                orientation='h',
                name='Realizado',
                marker_color='green' if percentual_atingido >= 100 else 'orange',
                width=0.5
            ))
            
            fig_meta.update_layout(
                title=f"Progresso da Meta - {meses[mes-1]} {ano}",
                xaxis_title="R$",
                barmode='overlay',
                height=250,
                showlegend=True
            )
            
            st.plotly_chart(fig_meta, use_container_width=True)
        
        with col2:
            # Status visual
            if percentual_atingido >= 100:
                st.success(f"✅ Meta atingida!\n+{percentual_atingido-100:.1f}% acima")
            elif percentual_atingido >= 80:
                st.warning(f"⚠️ Próximo da meta\n{100-percentual_atingido:.1f}% restante")
            else:
                st.error(f"❌ Abaixo da meta\n{100-percentual_atingido:.1f}% restante")
        
        # Comparativo anual (ano completo sempre)
        st.markdown("#### Comparativo Anual - Real x Meta (Ano Completo)")
        with st.spinner("📊 Carregando comparativo anual..."):
            metas_anuais = buscar_metas_anuais(ano, setor_meta)
            if metas_anuais:
                # Vendas por mês (somente vendas 'V')
                vendas_mensais = df_atual[df_atual['Flag tipo'] == 'V'].groupby('Mês')['Total NF'].sum()

                # Sempre 12 meses
                meses_disponiveis_grafico = list(range(1, 13))
                meses_labels_grafico = [meses[m - 1] for m in meses_disponiveis_grafico]

                metas_valores = [metas_anuais.get(m, 0) for m in meses_disponiveis_grafico]
                vendas_valores = [vendas_mensais.get(m, 0) for m in meses_disponiveis_grafico]

                meta_anual_total = sum(metas_valores)
                realizado_anual_total = sum(vendas_valores)  # Zeros para meses sem faturamento
                perc_conclusao = (realizado_anual_total / meta_anual_total * 100) if meta_anual_total > 0 else 0

                # Métricas anuais (Meta Total, Atingido, %)
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Meta Anual (Soma)", f"R$ {meta_anual_total:,.2f}")
                with c2:
                    st.metric("Realizado Anual", f"R$ {realizado_anual_total:,.2f}")
                with c3:
                    st.metric("% Conclusão", f"{perc_conclusao:.1f}%")

                # Gráfico (12 meses)
                fig_anual = go.Figure()
                fig_anual.add_trace(go.Scatter(
                    x=meses_labels_grafico,
                    y=metas_valores,
                    mode='lines+markers',
                    name='Meta Mensal',
                    line=dict(color='red', width=3, dash='dash'),
                    marker=dict(size=8)
                ))
                fig_anual.add_trace(go.Scatter(
                    x=meses_labels_grafico,
                    y=vendas_valores,
                    mode='lines+markers',
                    name='Realizado',
                    line=dict(color='blue', width=3),
                    marker=dict(size=8),
                    fill='tonexty',
                    fillcolor='rgba(0,100,80,0.15)'
                ))
                fig_anual.update_layout(
                    title=f'Evolução Real x Meta - {ano} (12 Meses)',
                    xaxis_title='Mês',
                    yaxis_title='R$',
                    hovermode='x unified',
                    height=420
                )
                st.plotly_chart(fig_anual, use_container_width=True)

                # Tabela detalhada
                df_comparativo = pd.DataFrame({
                    'Mês': meses_labels_grafico,
                    'Meta': metas_valores,
                    'Realizado': vendas_valores
                })
                df_comparativo['Diferença'] = df_comparativo['Realizado'] - df_comparativo['Meta']
                df_comparativo['% Atingido Mês'] = df_comparativo.apply(
                    lambda r: (r['Realizado'] / r['Meta'] * 100) if r['Meta'] > 0 else 0, axis=1
                ).round(1)

                df_comparativo_display = df_comparativo.copy()
                for col in ['Meta', 'Realizado', 'Diferença']:
                    df_comparativo_display[col] = df_comparativo_display[col].apply(lambda x: f"R$ {x:,.2f}")
                # Tornar a tabela ocultável (expander) conforme solicitado
                with st.expander("📋 Detalhe Mensal Real x Meta", expanded=False):
                    st.dataframe(
                        df_comparativo_display,
                        hide_index=True,
                        use_container_width=True
                    )
    else:
        st.info(f"Não há metas cadastradas para {ano} no setor {setor_meta}")
elif role == "Admin (todas equipes)":
    st.info("💡 Para visualizar metas, selecione um setor específico (Indústria ou Varejo)")
else:
    st.info("💡 Comparativo de metas disponível apenas para setores específicos")

st.divider()

# ========================================
# TICKET MÉDIO POR CANAL
# ========================================
st.subheader("🎫 Ticket Médio")

if not df_vendas.empty:
    tab_canal, tab_cliente = st.tabs(["Por Canal", "Por Cliente"])

    # ================= TAB CANAL =================
    with tab_canal:
        # Reorganizado: gráfico acima da tabela (antes lado a lado)
        # Análise de ticket médio por canal
        analise_ticket = df_vendas.groupby('Atividade').agg({
            'Total NF': 'sum',
            'Nota': 'nunique'
        }).reset_index()
        analise_ticket['Ticket Médio'] = analise_ticket['Total NF'] / analise_ticket['Nota']
        analise_ticket = analise_ticket.sort_values('Ticket Médio', ascending=False)

        fig_ticket = px.bar(
            analise_ticket,
            x='Atividade',
            y='Ticket Médio',
            title='Ticket Médio por Canal',
            text='Ticket Médio',
            color='Atividade',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_ticket.update_traces(texttemplate='R$ %{text:,.0f}', textposition='outside')
        fig_ticket.update_layout(height=700, margin=dict(l=40, r=30, t=70, b=140))
        st.plotly_chart(fig_ticket, use_container_width=True)

        analise_ticket_display = analise_ticket.rename(columns={
            'Total NF': 'Faturamento (R$)',
            'Ticket Médio': 'Ticket Médio (R$)'
        })
        with st.expander("📋 Tabela Ticket por Canal", expanded=False):
            st.dataframe(
                analise_ticket_display[['Atividade', 'Faturamento (R$)', 'Nota', 'Ticket Médio (R$)']].rename(columns={'Nota': 'Qtd Pedidos'}),
                hide_index=True,
                column_config={
                    "Faturamento (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Ticket Médio (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                }
            )
        ticket_geral = total_vendas / df_vendas['Nota'].nunique() if df_vendas['Nota'].nunique() > 0 else 0
        melhor_canal = analise_ticket.iloc[0]['Atividade'] if not analise_ticket.empty else "N/A"
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Ticket Médio Geral", f"R$ {ticket_geral:,.2f}")
        with col_b:
            st.metric("Melhor Canal", melhor_canal)
        # ===== Novo bloco de detalhamento por canal =====
        st.markdown("---")
        st.markdown("#### 🔎 Detalhamento do Canal")
        canais_disponiveis = analise_ticket['Atividade'].tolist()
        if canais_disponiveis:
            canal_selecionado = st.selectbox("Selecione um Canal", canais_disponiveis, key="canal_ticket_detalhe")
            df_canal_det = df_vendas[df_vendas['Atividade'] == canal_selecionado]
            if not df_canal_det.empty:
                fat_canal_sel = df_canal_det['Total NF'].sum()
                notas_canal_sel = df_canal_det['Nota'].nunique()
                ticket_canal_sel = fat_canal_sel / notas_canal_sel if notas_canal_sel > 0 else 0
                margem_canal_sel = df_canal_det['$ Margem'].sum()
                margem_pct_canal_sel = (margem_canal_sel / fat_canal_sel * 100) if fat_canal_sel > 0 else 0
                qtd_clientes_canal = df_canal_det['Cliente'].nunique()
                qtd_produtos_canal = df_canal_det['Produto'].nunique()

                # Ajuste: métricas em 2 linhas (3 por linha)
                row1_c1, row1_c2, row1_c3 = st.columns(3)
                row2_c1, row2_c2, row2_c3 = st.columns(3)
                with row1_c1: st.metric("Faturamento", f"R$ {fat_canal_sel:,.2f}")
                with row1_c2: st.metric("Qtd Notas", f"{notas_canal_sel}")
                with row1_c3: st.metric("Ticket Médio", f"R$ {ticket_canal_sel:,.2f}")
                with row2_c1: st.metric("Margem (R$)", f"R$ {margem_canal_sel:,.2f}")
                with row2_c2: st.metric("Margem %", f"{margem_pct_canal_sel:.2f}%")
                with row2_c3: st.metric("Clientes Únicos", f"{qtd_clientes_canal}")

                # Top produtos do canal (substitui top clientes) para alinhar com cliente
                top_produtos_canal = df_canal_det.groupby('Produto').agg({'Total NF':'sum','$ Margem':'sum','Nota':'nunique'}).reset_index()
                top_produtos_canal['Ticket Médio'] = top_produtos_canal['Total NF'] / top_produtos_canal['Nota']
                top_produtos_canal = top_produtos_canal.sort_values('Total NF', ascending=False).head(10)
                top_produtos_canal = top_produtos_canal.rename(columns={'Total NF':'Faturamento (R$)', '$ Margem':'Margem (R$)','Nota':'Qtd Notas'})

                # Exibição sequencial: gráfico seguido da tabela (sem colunas)
                if not top_produtos_canal.empty:
                    fig_top_produtos_canal = px.bar(
                        top_produtos_canal.sort_values('Faturamento (R$)', ascending=False),
                        x='Produto',
                        y='Faturamento (R$)',
                        title='Top 10 Produtos (Faturamento)',
                        text='Faturamento (R$)',
                        color='Produto',
                        color_discrete_sequence=px.colors.qualitative.Set2
                    )
                    fig_top_produtos_canal.update_traces(texttemplate='R$ %{text:,.0f}', textposition='outside')
                    fig_top_produtos_canal.update_layout(height=650, margin=dict(l=40,r=20,t=60,b=140), showlegend=False, xaxis_tickangle=-30)
                    st.plotly_chart(fig_top_produtos_canal, use_container_width=True)
                with st.expander("📋 Top 10 Produtos - Tabela (Canal)", expanded=False):
                    st.dataframe(top_produtos_canal, hide_index=True, column_config={
                        "Faturamento (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Margem (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Ticket Médio": st.column_config.NumberColumn(format="R$ %.2f"),
                    })

                # Expander com todos os registros do canal
                with st.expander(f"📋 Detalhes completos do canal {canal_selecionado}"):
                    df_canal_show = df_canal_det[['Data','Nota','Cliente','Produto','Total NF','$ Margem','Valor Unit.','Vendedor']].copy()
                    st.dataframe(df_canal_show, hide_index=True, use_container_width=True, column_config={
                        'Total NF': st.column_config.NumberColumn(format="R$ %.2f"),
                        '$ Margem': st.column_config.NumberColumn(format="R$ %.2f"),
                        'Valor Unit.': st.column_config.NumberColumn(format="R$ %.2f"),
                    })
        # ===== Fim bloco detalhamento canal =====

    # ================= TAB CLIENTE =================
    with tab_cliente:
        analise_ticket_cliente = df_vendas.groupby('Cliente').agg({
            'Total NF': 'sum',
            'Nota': 'nunique'
        }).reset_index()
        analise_ticket_cliente['Ticket Médio'] = analise_ticket_cliente['Total NF'] / analise_ticket_cliente['Nota']
        analise_ticket_cliente = analise_ticket_cliente.sort_values('Ticket Médio', ascending=False)

        # Exibir sempre Top 10 (remoção da opção Top 5/Top 10)
        analise_ticket_cliente_top = analise_ticket_cliente.head(10)

        # Gráfico Top 10
        fig_ticket_cliente = px.bar(
            analise_ticket_cliente_top,
            x='Cliente',
            y='Ticket Médio',
            title='Ticket Médio - Top 10 Clientes',
            text='Ticket Médio',
            color='Cliente',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_ticket_cliente.update_traces(texttemplate='R$ %{text:,.0f}', textposition='outside')
        fig_ticket_cliente.update_layout(xaxis_tickangle=-45, height=700, margin=dict(l=40, r=30, t=70, b=200))
        st.plotly_chart(fig_ticket_cliente, use_container_width=True)

        # Tabela Ticket
        analise_ticket_cliente_display = analise_ticket_cliente.rename(columns={
            'Total NF': 'Faturamento (R$)',
            'Ticket Médio': 'Ticket Médio (R$)'
        })
        with st.expander("📋 Tabela Ticket por Cliente", expanded=False):
            st.dataframe(
                analise_ticket_cliente_display[['Cliente', 'Faturamento (R$)', 'Nota', 'Ticket Médio (R$)']].rename(columns={'Nota': 'Qtd Pedidos'}),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Faturamento (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Ticket Médio (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                }
            )
        ticket_medio_geral_cliente = total_vendas / df_vendas['Nota'].nunique() if df_vendas['Nota'].nunique() > 0 else 0
        maior_ticket_cliente = analise_ticket_cliente.iloc[0]['Cliente'] if not analise_ticket_cliente.empty else "N/A"
        colc_a, colc_b = st.columns(2)
        with colc_a:
            st.metric("Ticket Médio Geral", f"R$ {ticket_medio_geral_cliente:,.2f}")
        with colc_b:
            st.metric("Maior Ticket Cliente", maior_ticket_cliente)
        # ===== Novo bloco de detalhamento por cliente =====
        st.markdown("---")
        st.markdown("#### 🔎 Detalhamento do Cliente")
        clientes_disponiveis = analise_ticket_cliente['Cliente'].tolist()
        if clientes_disponiveis:
            cliente_selecionado = st.selectbox("Selecione um Cliente", clientes_disponiveis, key="cliente_ticket_detalhe")
            df_cliente_det = df_vendas[df_vendas['Cliente'] == cliente_selecionado]
            if not df_cliente_det.empty:
                fat_cliente_sel = df_cliente_det['Total NF'].sum()
                notas_cliente_sel = df_cliente_det['Nota'].nunique()
                ticket_cliente_sel = fat_cliente_sel / notas_cliente_sel if notas_cliente_sel > 0 else 0
                margem_cliente_sel = df_cliente_det['$ Margem'].sum()
                margem_pct_cliente_sel = (margem_cliente_sel / fat_cliente_sel * 100) if fat_cliente_sel > 0 else 0
                qtd_produtos_cliente = df_cliente_det['Produto'].nunique()
                qtd_canais_cliente = df_cliente_det['Atividade'].nunique() if 'Atividade' in df_cliente_det.columns else 0

                # Ajuste métricas cliente em 2 linhas (3 por linha)
                r1c1, r1c2, r1c3 = st.columns(3)
                r2c1, r2c2, r2c3 = st.columns(3)
                with r1c1: st.metric("Faturamento", f"R$ {fat_cliente_sel:,.2f}")
                with r1c2: st.metric("Qtd Notas", f"{notas_cliente_sel}")
                with r1c3: st.metric("Ticket Médio", f"R$ {ticket_cliente_sel:,.2f}")
                with r2c1: st.metric("Margem (R$)", f"R$ {margem_cliente_sel:,.2f}")
                with r2c2: st.metric("Margem %", f"{margem_pct_cliente_sel:.2f}%")
                with r2c3: st.metric("Produtos Únicos", f"{qtd_produtos_cliente}")

                # (Removido) Gráfico de pizza de distribuição por canal a pedido do usuário

                # Top produtos do cliente
                top_produtos_cliente = df_cliente_det.groupby('Produto').agg({'Total NF':'sum','$ Margem':'sum','Nota':'nunique'}).reset_index()
                top_produtos_cliente['Ticket Médio'] = top_produtos_cliente['Total NF'] / top_produtos_cliente['Nota']
                top_produtos_cliente = top_produtos_cliente.sort_values('Total NF', ascending=False).head(10)
                top_produtos_cliente = top_produtos_cliente.rename(columns={'Total NF':'Faturamento (R$)', '$ Margem':'Margem (R$)','Nota':'Qtd Notas'})

                # Exibição sequencial: gráfico seguido da tabela (sem colunas)
                if not top_produtos_cliente.empty:
                    fig_top_produtos_cliente = px.bar(
                        top_produtos_cliente.sort_values('Faturamento (R$)', ascending=False),
                        x='Produto',
                        y='Faturamento (R$)',
                        title='Top 10 Produtos (Faturamento)',
                        text='Faturamento (R$)',
                        color='Produto',
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    fig_top_produtos_cliente.update_traces(texttemplate='R$ %{text:,.0f}', textposition='outside')
                    fig_top_produtos_cliente.update_layout(height=650, margin=dict(l=40,r=20,t=60,b=140), showlegend=False, xaxis_tickangle=-30)
                    st.plotly_chart(fig_top_produtos_cliente, use_container_width=True)
                with st.expander("📋 Top 10 Produtos - Tabela (Cliente)", expanded=False):
                    st.dataframe(top_produtos_cliente, hide_index=True, column_config={
                        "Faturamento (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Margem (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Ticket Médio": st.column_config.NumberColumn(format="R$ %.2f"),
                    })

                # Expander com todas as notas do cliente
                with st.expander(f"📋 Detalhes completos do cliente {cliente_selecionado}"):
                    df_cliente_show = df_cliente_det[['Data','Nota','Produto','Atividade','Total NF','$ Margem','Valor Unit.','Vendedor']].copy()
                    st.dataframe(df_cliente_show, hide_index=True, use_container_width=True, column_config={
                        'Total NF': st.column_config.NumberColumn(format="R$ %.2f"),
                        '$ Margem': st.column_config.NumberColumn(format="R$ %.2f"),
                        'Valor Unit.': st.column_config.NumberColumn(format="R$ %.2f"),
                    })
        # ===== Fim bloco detalhamento cliente =====
else:
    st.info("Sem dados de vendas para análise de ticket médio")

st.divider()

# ========================================
# MARGEM BRUTA POR CANAL
# ========================================
st.subheader("💰 Margem Bruta por Canal")

if not df_vendas.empty:
    # Análise de margem por canal
    analise_margem_canal = df_vendas.groupby('Atividade').agg({
        'Total NF': 'sum',
        '$ Margem': 'sum'
    }).reset_index()
    
    # Calcular margem %
    analise_margem_canal['Margem %'] = (analise_margem_canal['$ Margem'] / analise_margem_canal['Total NF'] * 100).round(2)
    analise_margem_canal = analise_margem_canal.sort_values('Margem %', ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_margem_canal = px.bar(
            analise_margem_canal,
            x='Atividade', 
            y='Margem %',
            title='Margem % por Canal',
            text='Margem %',
            color='Margem %',
            color_continuous_scale='RdYlGn',
            height=600
        )
        fig_margem_canal.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_margem_canal.update_layout(showlegend=False)
        st.plotly_chart(fig_margem_canal, use_container_width=True)
    
    with col2:
        # Tabela com valores absolutos e percentuais
        analise_margem_display = analise_margem_canal.copy()
        analise_margem_display = analise_margem_display.rename(columns={
            'Total NF': 'Faturamento (R$)',
            '$ Margem': 'Margem (R$)'
        })
        
        with st.expander("📋 Tabela Margem por Canal", expanded=False):
            st.dataframe(
                analise_margem_display[['Atividade', 'Faturamento (R$)', 'Margem (R$)', 'Margem %']],
                hide_index=True,
                column_config={
                    "Faturamento (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Margem (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                }
            )
        
        # Métricas resumo
        margem_geral_percent = (total_margem / total_vendas * 100) if total_vendas > 0 else 0
        melhor_margem_canal = analise_margem_canal.iloc[0]['Atividade'] if not analise_margem_canal.empty else "N/A"
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Margem % Geral", f"{margem_geral_percent:.2f}%")
        with col_b:
            st.metric("Melhor Margem %", melhor_margem_canal)
    
    # Gráfico de margem absoluta
    st.markdown("#### Margem Absoluta por Canal")
    fig_margem_abs = px.bar(
        analise_margem_canal.sort_values('$ Margem', ascending=False),
        x='Atividade',
        y='$ Margem',
        title='Margem Absoluta (R$) por Canal',
        text='$ Margem',
        color='Atividade',
        color_discrete_sequence=px.colors.qualitative.G10,
        height=600
    )
    fig_margem_abs.update_traces(texttemplate='R$ %{text:,.0f}', textposition='outside')
    st.plotly_chart(fig_margem_abs, use_container_width=True)
else:
    st.info("Sem dados de vendas para análise de margem")

st.divider()

# ========================================
# ANÁLISES DETALHADAS
# ========================================
st.subheader("🔍 Análises Detalhadas")

# ----------------------------------------
# Helper para calcular TOP faturamento líquido por dimensão
# ----------------------------------------
def calcular_top_faturamento_liquido(df_mes_full: pd.DataFrame, df_devo_mes_extra: pd.DataFrame, group_col: str, top_n: int = 10):
    """Retorna DataFrame com faturamento líquido por grupo (Top N).

    Fórmula: (Σ Vendas) - (Σ Devoluções) - (Σ Devoluções Extras) por grupo.
    Devoluções Extras são mapeadas quando possível para Cliente / Produto / Vendedor.
    """
    if group_col not in df_mes_full.columns:
        return pd.DataFrame(columns=[group_col, 'Faturamento Líquido'])

    vendas = df_mes_full[df_mes_full['Flag tipo'] == 'V'].groupby(group_col)['Total NF'].sum()
    devolucoes = df_mes_full[df_mes_full['Flag tipo'] == 'D'].groupby(group_col)['Total NF'].sum() if 'D' in df_mes_full['Flag tipo'].unique() else pd.Series(dtype=float)

    # Normaliza devoluções (tratadas sempre como valores a subtrair)
    fat_liquido = vendas - devolucoes.reindex(vendas.index, fill_value=0)

    # Devoluções extras (query_devo) - mapear colunas quando existir
    if df_devo_mes_extra is not None and not df_devo_mes_extra.empty:
        df_extra = df_devo_mes_extra.copy()
        # Cliente: campo 'cliente' vem "codigo - nome"; extraímos apenas o nome para tentar casar
        if group_col == 'Cliente' and 'cliente' in df_extra.columns:
            df_extra['__match'] = df_extra['cliente'].apply(lambda x: x.split(' - ', 1)[1].strip() if isinstance(x, str) and ' - ' in x else x)
        elif group_col == 'Produto' and 'DESCRICAO' in df_extra.columns:
            # Alguns casos: query_devo usa alias 'descricao' minúsculo; garantir ambas
            col_desc = 'DESCRICAO' if 'DESCRICAO' in df_extra.columns else 'descricao'
            df_extra['__match'] = df_extra[col_desc]
        elif group_col == 'Produto' and 'descricao' in df_extra.columns:
            df_extra['__match'] = df_extra['descricao']
        elif group_col == 'Vendedor' and 'vendedor' in df_extra.columns:
            df_extra['__match'] = df_extra['vendedor']
        else:
            df_extra['__match'] = None

        if df_extra['__match'].notna().any():
            extras_group = df_extra.groupby('__match')['TOTAL_MERCADORIA'].sum().abs()
            # Subtrai devolução extra quando houver chave correspondente
            for k, v in extras_group.items():
                if k in fat_liquido.index:
                    fat_liquido.loc[k] -= v

    df_result = fat_liquido.reset_index().rename(columns={0: 'Faturamento Líquido'})
    df_result.columns = [group_col, 'Faturamento Líquido']
    df_result = df_result.sort_values('Faturamento Líquido', ascending=False).head(top_n)
    return df_result

def plot_top_fat_liquido(df_top: pd.DataFrame, group_col: str, titulo: str):
    if df_top.empty:
        return go.Figure()
    fig = px.bar(
        df_top,
        x='Faturamento Líquido',
        y=group_col,
        orientation='h',
        color=group_col,
        title=titulo,
        hover_data={'Faturamento Líquido':':,.2f', group_col: True}
    )
    for _, row in df_top.iterrows():
        valor_formatado = f"R$ {row['Faturamento Líquido']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        fig.add_annotation(
            x=row['Faturamento Líquido'],
            y=row[group_col],
            text=valor_formatado,
            showarrow=False,
            font=dict(size=14, color="white"),
            xanchor="left"
        )
    fig.update_layout(showlegend=False)
    return fig

# DataFrame do mês atual completo (inclui V e D) já existe: df_mes
# DataFrame de devoluções extras do mês: df_devo_mes_extra

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Top Clientes", "Top Produtos", "Por Estado", "Por Vendedor", "Performance Regional"])

with tab1:
    st.markdown("### 🏆 Top 10 Clientes")
    if not df_vendas.empty:
        df_top_clientes = calcular_top_faturamento_liquido(df_mes, df_devo_mes_extra, 'Cliente', 10)
        fig_cliente = plot_top_fat_liquido(df_top_clientes, 'Cliente', 'Faturamento Líquido por Cliente (Top 10)')
        st.plotly_chart(fig_cliente, use_container_width=True)
        # Métrica: Maior Faturamento Líquido (Cliente) delta vs topo ano anterior
        if not df_top_clientes.empty:
            top_cliente = df_top_clientes.iloc[0]['Cliente']
            fat_liq_top_atual = df_top_clientes.iloc[0]['Faturamento Líquido']
            df_prev_mes_same = df_prev[(df_prev['Mês'] == mes)]
            if not df_prev_mes_same.empty:
                df_prev_top_clientes = calcular_top_faturamento_liquido(df_prev_mes_same, df_devo[(df_devo['Ano']==prev_year) & (df_devo['Mês']==mes)] if not df_devo.empty else pd.DataFrame(), 'Cliente', 10)
                if not df_prev_top_clientes.empty:
                    top_cliente_prev = df_prev_top_clientes.iloc[0]['Cliente']
                    fat_liq_prev_top = df_prev_top_clientes.iloc[0]['Faturamento Líquido']
                else:
                    top_cliente_prev, fat_liq_prev_top = 'N/A', 0
            else:
                top_cliente_prev, fat_liq_prev_top = 'N/A', 0
            delta_fat = fat_liq_top_atual - fat_liq_prev_top
            mc1, mc2 = st.columns(2)
            with mc1:
                st.metric(
                    f"Maior Fat. Líquido {ano}",
                    f"R$ {fat_liq_top_atual:,.2f}",
                    f"R$ {delta_fat:,.2f}",
                    delta_color="normal" if delta_fat >= 0 else "inverse",
                    help=f"Cliente: {top_cliente} (delta vs topo {prev_year})"
                )
            with mc2:
                st.metric(
                    f"Maior Fat. Líq. {prev_year}",
                    f"R$ {fat_liq_prev_top:,.2f}",
                    help=f"Cliente: {top_cliente_prev} (mesmo mês ano anterior)"
                )
        
        # Tabela complementar com mais detalhes
        fat_cliente = df_vendas.groupby('Cliente').agg({
            'Total NF': 'sum',
            '$ Margem': 'sum',
            'Nota': 'nunique'
        }).reset_index()
        fat_cliente.columns = ['Cliente', 'Faturamento', 'Margem', 'Qtd Pedidos']
        fat_cliente = fat_cliente.sort_values('Faturamento', ascending=False).head(10)
        fat_cliente['Margem %'] = (fat_cliente['Margem'] / fat_cliente['Faturamento'] * 100).round(2)
        
        # Formatação para exibição
        fat_cliente_display = fat_cliente.copy()
        fat_cliente_display = fat_cliente_display.rename(columns={
            'Faturamento': 'Faturamento (R$)',
            'Margem': 'Margem (R$)'
        })
        
        with st.expander("📋 Tabela Top Clientes", expanded=False):
            st.dataframe(
                fat_cliente_display, 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "Faturamento (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Margem (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                }
            )
        
        # Comparativo com ano anterior
        df_vendas_prev_clientes = df_prev[df_prev['Flag tipo'] == 'V']
        if not df_vendas_prev_clientes.empty:
            st.markdown("#### Comparativo com Ano Anterior")
            fat_cliente_prev = df_vendas_prev_clientes.groupby('Cliente')['Total NF'].sum().sort_values(ascending=False).head(10)
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Top Cliente Atual", fat_cliente.iloc[0]['Cliente'] if not fat_cliente.empty else "N/A")
            with col_b:
                st.metric("Top Cliente Anterior", fat_cliente_prev.index[0] if not fat_cliente_prev.empty else "N/A")
    else:
        st.info("Sem dados de clientes para o período selecionado")

with tab2:
    st.markdown("### 📦 Top 10 Produtos")
    if not df_vendas.empty:
        df_top_produtos = calcular_top_faturamento_liquido(df_mes, df_devo_mes_extra, 'Produto', 10)
        fig_produto = plot_top_fat_liquido(df_top_produtos, 'Produto', 'Faturamento Líquido por Produto (Top 10)')
        st.plotly_chart(fig_produto, use_container_width=True)
        if not df_top_produtos.empty:
            top_prod = df_top_produtos.iloc[0]['Produto']
            fat_liq_top_atual = df_top_produtos.iloc[0]['Faturamento Líquido']
            df_prev_mes_same = df_prev[(df_prev['Mês'] == mes)]
            if not df_prev_mes_same.empty:
                df_prev_top_produtos = calcular_top_faturamento_liquido(df_prev_mes_same, df_devo[(df_devo['Ano']==prev_year) & (df_devo['Mês']==mes)] if not df_devo.empty else pd.DataFrame(), 'Produto', 10)
                if not df_prev_top_produtos.empty:
                    top_prod_prev = df_prev_top_produtos.iloc[0]['Produto']
                    fat_liq_prev_top = df_prev_top_produtos.iloc[0]['Faturamento Líquido']
                else:
                    top_prod_prev, fat_liq_prev_top = 'N/A', 0
            else:
                top_prod_prev, fat_liq_prev_top = 'N/A', 0
            delta_fat = fat_liq_top_atual - fat_liq_prev_top
            mp1, mp2 = st.columns(2)
            with mp1:
                st.metric(
                    f"Maior Fat. Líquido {ano}",
                    f"R$ {fat_liq_top_atual:,.2f}",
                    f"R$ {delta_fat:,.2f}",
                    delta_color="normal" if delta_fat >= 0 else "inverse",
                    help=f"Produto: {top_prod} (delta vs topo {prev_year})"
                )
            with mp2:
                st.metric(
                    f"Maior Fat. Líq. {prev_year}",
                    f"R$ {fat_liq_prev_top:,.2f}",
                    help=f"Produto: {top_prod_prev} (mesmo mês ano anterior)"
                )
    # Relatório "Faturamento por Grupo de Produtos" removido conforme solicitação do usuário.

        # Comparativo com Ano Anterior (Top Produtos por Faturamento)
        df_vendas_prev_produtos = df_prev[df_prev['Flag tipo'] == 'V'] if not df_prev.empty else pd.DataFrame()
        if not df_vendas_prev_produtos.empty and 'Produto' in df_vendas_prev_produtos.columns:
            st.markdown("#### Comparativo com Ano Anterior")
            fat_produto_atual = df_vendas[df_vendas['Flag tipo'] == 'V'].groupby('Produto')['Total NF'].sum().sort_values(ascending=False)
            fat_produto_prev = df_vendas_prev_produtos.groupby('Produto')['Total NF'].sum().sort_values(ascending=False)
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Top Produto Atual", fat_produto_atual.index[0] if not fat_produto_atual.empty else "N/A")
            with col_b:
                st.metric("Top Produto Anterior", fat_produto_prev.index[0] if not fat_produto_prev.empty else "N/A")
    else:
        st.info("Sem dados de produtos para o período selecionado")

with tab3:
    st.markdown("### 🗺️ Análise por Estado")
    if not df_vendas.empty and 'UF' in df_vendas.columns:
        # Top 10 UF por faturamento líquido
        df_top_uf = calcular_top_faturamento_liquido(df_mes, df_devo_mes_extra, 'UF', 10)
        fig_uf = plot_top_fat_liquido(df_top_uf, 'UF', 'Faturamento Líquido por UF (Top 10)')
        st.plotly_chart(fig_uf, use_container_width=True)
        if not df_top_uf.empty:
            top_uf = df_top_uf.iloc[0]['UF']
            fat_liq_top_atual = df_top_uf.iloc[0]['Faturamento Líquido']
            df_prev_mes_same = df_prev[(df_prev['Mês'] == mes)]
            if not df_prev_mes_same.empty:
                df_prev_top_uf = calcular_top_faturamento_liquido(df_prev_mes_same, df_devo[(df_devo['Ano']==prev_year) & (df_devo['Mês']==mes)] if not df_devo.empty else pd.DataFrame(), 'UF', 10)
                if not df_prev_top_uf.empty:
                    top_uf_prev = df_prev_top_uf.iloc[0]['UF']
                    fat_liq_prev_top = df_prev_top_uf.iloc[0]['Faturamento Líquido']
                else:
                    top_uf_prev, fat_liq_prev_top = 'N/A', 0
            else:
                top_uf_prev, fat_liq_prev_top = 'N/A', 0
            delta_fat = fat_liq_top_atual - fat_liq_prev_top
            mu1, mu2 = st.columns(2)
            with mu1:
                st.metric(
                    f"Maior Fat. Líquido {ano}",
                    f"R$ {fat_liq_top_atual:,.2f}",
                    f"R$ {delta_fat:,.2f}",
                    delta_color="normal" if delta_fat >= 0 else "inverse",
                    help=f"UF: {top_uf} (delta vs topo {prev_year})"
                )
            with mu2:
                st.metric(
                    f"Maior Fat. Líq. {prev_year}",
                    f"R$ {fat_liq_prev_top:,.2f}",
                    help=f"UF: {top_uf_prev} (mesmo mês ano anterior)"
                )
        
        # Distribuição por Região
        st.markdown("#### Distribuição por Região")
        if 'Região' in df_vendas.columns:
            fat_regiao = df_vendas.groupby('Região').agg({
                'Total NF': 'sum',
                '$ Margem': 'sum',
                'Cliente': 'nunique'
            }).reset_index().sort_values('Total NF', ascending=False)
            fat_regiao.columns = ['Região', 'Faturamento', 'Margem', 'Qtd Clientes']
            
            fat_regiao_display = fat_regiao.copy()
            fat_regiao_display = fat_regiao_display.rename(columns={
                'Faturamento': 'Faturamento (R$)',
                'Margem': 'Margem (R$)'
            })
            
            with st.expander("📋 Tabela Distribuição por Região", expanded=False):
                st.dataframe(
                    fat_regiao_display, 
                    hide_index=True,
                    column_config={
                        "Faturamento (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Margem (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                    }
                )
        else:
            st.info("Dados de região não disponíveis")

        # Comparativo com Ano Anterior (Top UF por Faturamento)
        df_vendas_prev_uf = df_prev[df_prev['Flag tipo'] == 'V'] if not df_prev.empty else pd.DataFrame()
        if not df_vendas_prev_uf.empty and 'UF' in df_vendas_prev_uf.columns:
            st.markdown("#### Comparativo com Ano Anterior")
            fat_uf_atual = df_vendas[df_vendas['Flag tipo'] == 'V'].groupby('UF')['Total NF'].sum().sort_values(ascending=False)
            fat_uf_prev = df_vendas_prev_uf.groupby('UF')['Total NF'].sum().sort_values(ascending=False)
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Top UF Atual", fat_uf_atual.index[0] if not fat_uf_atual.empty else "N/A")
            with col_b:
                st.metric("Top UF Anterior", fat_uf_prev.index[0] if not fat_uf_prev.empty else "N/A")
    else:
        st.info("Sem dados geográficos para o período selecionado")

with tab4:
    st.markdown("### 👤 Performance por Vendedor")
    if not df_vendas.empty and 'Vendedor' in df_vendas.columns:
        df_top_vendedor = calcular_top_faturamento_liquido(df_mes, df_devo_mes_extra, 'Vendedor', 10)
        fig_vendedor = plot_top_fat_liquido(df_top_vendedor, 'Vendedor', 'Faturamento Líquido por Vendedor (Top 10)')
        st.plotly_chart(fig_vendedor, use_container_width=True)
        if not df_top_vendedor.empty:
            top_vend = df_top_vendedor.iloc[0]['Vendedor']
            fat_liq_top_atual = df_top_vendedor.iloc[0]['Faturamento Líquido']
            df_prev_mes_same = df_prev[(df_prev['Mês'] == mes)]
            if not df_prev_mes_same.empty:
                df_prev_top_vend = calcular_top_faturamento_liquido(df_prev_mes_same, df_devo[(df_devo['Ano']==prev_year) & (df_devo['Mês']==mes)] if not df_devo.empty else pd.DataFrame(), 'Vendedor', 10)
                if not df_prev_top_vend.empty:
                    top_vend_prev = df_prev_top_vend.iloc[0]['Vendedor']
                    fat_liq_prev_top = df_prev_top_vend.iloc[0]['Faturamento Líquido']
                else:
                    top_vend_prev, fat_liq_prev_top = 'N/A', 0
            else:
                top_vend_prev, fat_liq_prev_top = 'N/A', 0
            delta_fat = fat_liq_top_atual - fat_liq_prev_top
            mv1, mv2 = st.columns(2)
            with mv1:
                st.metric(
                    f"Maior Fat. Líquido {ano}",
                    f"R$ {fat_liq_top_atual:,.2f}",
                    f"R$ {delta_fat:,.2f}",
                    delta_color="normal" if delta_fat >= 0 else "inverse",
                    help=f"Vendedor: {top_vend} (delta vs topo {prev_year})"
                )
            with mv2:
                st.metric(
                    f"Maior Fat. Líq. {prev_year}",
                    f"R$ {fat_liq_prev_top:,.2f}",
                    help=f"Vendedor: {top_vend_prev} (mesmo mês ano anterior)"
                )
        
        # Performance por equipe
        st.markdown("#### Performance por Equipe")
        if 'Equipe' in df_vendas.columns:
            fat_equipe = df_vendas.groupby('Equipe').agg({
                'Total NF': 'sum',
                '$ Margem': 'sum',
                'Cliente': 'nunique',
                'Vendedor': 'nunique'
            }).reset_index()
            fat_equipe.columns = ['Equipe', 'Faturamento', 'Margem', 'Qtd Clientes', 'Qtd Vendedores']
            fat_equipe = fat_equipe.sort_values('Faturamento', ascending=False)
            
            fat_equipe_display = fat_equipe.copy()
            fat_equipe_display = fat_equipe_display.rename(columns={
                'Faturamento': 'Faturamento (R$)',
                'Margem': 'Margem (R$)'
            })
            
            with st.expander("📋 Tabela Performance por Equipe", expanded=False):
                st.dataframe(
                    fat_equipe_display, 
                    hide_index=True,
                    column_config={
                        "Faturamento (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Margem (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                    }
                )
        else:
            st.info("Dados de equipe não disponíveis")

        # Comparativo com Ano Anterior (Top Vendedor por Faturamento)
        df_vendas_prev_vend = df_prev[df_prev['Flag tipo'] == 'V'] if not df_prev.empty else pd.DataFrame()
        if not df_vendas_prev_vend.empty and 'Vendedor' in df_vendas_prev_vend.columns:
            st.markdown("#### Comparativo com Ano Anterior")
            fat_vend_atual = df_vendas[df_vendas['Flag tipo'] == 'V'].groupby('Vendedor')['Total NF'].sum().sort_values(ascending=False)
            fat_vend_prev = df_vendas_prev_vend.groupby('Vendedor')['Total NF'].sum().sort_values(ascending=False)
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Top Vendedor Atual", fat_vend_atual.index[0] if not fat_vend_atual.empty else "N/A")
            with col_b:
                st.metric("Top Vendedor Anterior", fat_vend_prev.index[0] if not fat_vend_prev.empty else "N/A")
    else:
        st.info("Sem dados de vendedores para o período selecionado")

with tab5:
    st.markdown("### 🎯 Performance Regional")
    if not df_vendas.empty and 'Região' in df_vendas.columns:
        
        # Análise por Região - Totais
        st.markdown("#### Faturamento Total por Região")
        fat_regiao_total = df_vendas.groupby('Região').agg({
            'Total NF': 'sum',
            '$ Margem': 'sum',
            'Cliente': 'nunique',
            'Nota': 'nunique'
        }).reset_index().sort_values('Total NF', ascending=False)
        fat_regiao_total.columns = ['Região', 'Faturamento', 'Margem', 'Qtd Clientes', 'Qtd Notas']
        
        # Gráfico de barras - Total por região
        fig_regiao_total = px.bar(
            fat_regiao_total, 
            x='Região', 
            y='Faturamento',
            title='Faturamento Total por Região',
            text='Faturamento',
            color='Região',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_regiao_total.update_traces(texttemplate='R$ %{text:,.0f}', textposition='outside')
        fig_regiao_total.update_layout(
            xaxis_title='Região',
            yaxis_title='R$ Faturamento',
            showlegend=False,
            height=600
        )
        st.plotly_chart(fig_regiao_total, use_container_width=True)
        
        # Tabela com totais por região
        fat_regiao_display = fat_regiao_total.copy()
        fat_regiao_display = fat_regiao_display.rename(columns={
            'Faturamento': 'Faturamento (R$)',
            'Margem': 'Margem (R$)'
        })
        fat_regiao_display['Margem %'] = ((fat_regiao_total['Margem'] / fat_regiao_total['Faturamento']) * 100).round(2)
        fat_regiao_display['Participação %'] = ((fat_regiao_total['Faturamento'] / fat_regiao_total['Faturamento'].sum()) * 100).round(2)
        
        with st.expander("📋 Tabela Totais por Região", expanded=False):
            st.dataframe(
                fat_regiao_display, 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "Faturamento (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Margem (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                }
            )
        
        # Análise cruzada Região x Canal (se existir coluna Atividade)
        if 'Atividade' in df_vendas.columns:
            st.markdown("#### Canais por Região")
            fat_regiao_canal = df_vendas.groupby(['Região', 'Atividade'])['Total NF'].sum().reset_index()
            fat_regiao_canal_pivot = fat_regiao_canal.pivot(index='Região', columns='Atividade', values='Total NF').fillna(0)
            
            # Gráfico de barras empilhadas
            fig_regiao_canal = go.Figure()
            
            for atividade in fat_regiao_canal_pivot.columns:
                fig_regiao_canal.add_trace(go.Bar(
                    name=atividade,
                    x=fat_regiao_canal_pivot.index,
                    y=fat_regiao_canal_pivot[atividade],
                ))
            
            fig_regiao_canal.update_layout(
                barmode='stack',
                title='Faturamento por Região e Canal',
                xaxis_title='Região',
                yaxis_title='R$ Faturamento'
            )
            st.plotly_chart(fig_regiao_canal, use_container_width=True)
            
            # Tabela detalhada por região e canal
            st.markdown("#### Detalhamento por Região e Canal")
            fat_regiao_canal_display = fat_regiao_canal.copy()
            fat_regiao_canal_display = fat_regiao_canal_display.rename(columns={'Total NF': 'Faturamento (R$)'})
            fat_regiao_canal_display = fat_regiao_canal_display.sort_values('Faturamento (R$)', ascending=False)
            with st.expander("📋 Tabela Região x Canal", expanded=False):
                st.dataframe(
                    fat_regiao_canal_display, 
                    hide_index=True,
                    column_config={
                        "Faturamento (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                    }
                )

        # Comparativo com Ano Anterior (Top Região por Faturamento)
        df_vendas_prev_reg = df_prev[df_prev['Flag tipo'] == 'V'] if not df_prev.empty else pd.DataFrame()
        if not df_vendas_prev_reg.empty and 'Região' in df_vendas_prev_reg.columns:
            st.markdown("#### Comparativo com Ano Anterior")
            fat_reg_atual = df_vendas[df_vendas['Flag tipo'] == 'V'].groupby('Região')['Total NF'].sum().sort_values(ascending=False)
            fat_reg_prev = df_vendas_prev_reg.groupby('Região')['Total NF'].sum().sort_values(ascending=False)
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Top Região Atual", fat_reg_atual.index[0] if not fat_reg_atual.empty else "N/A")
            with col_b:
                st.metric("Top Região Anterior", fat_reg_prev.index[0] if not fat_reg_prev.empty else "N/A")
    else:
        st.info("Dados de região não disponíveis para análise")

st.divider()

# ========================
# TABELA DETALHADA
# ========================
with st.expander("📋 Dados Detalhados", expanded=False):
    st.markdown(f"#### Dados do mês de {meses[mes - 1]} de {ano}")
    # Construção do dataframe detalhado:
    # 1. Base: todos os registros do mês selecionado (inclui vendas e devoluções)
    # 2. Garante presença de coluna 'Equipe' (normaliza 'EQUIPE' se vier assim da query)
    # 3. Aplica filtro de equipe/ setor selecionado (filtro_equipe) mesmo que já aplicado antes
    # 4. Exibe TODAS as colunas da query, sem exceção
    df_detalhado = df_mes.copy()
    # Normalizar nome da coluna de equipe
    if 'EQUIPE' in df_detalhado.columns and 'Equipe' not in df_detalhado.columns:
        df_detalhado.rename(columns={'EQUIPE': 'Equipe'}, inplace=True)
    # Aplicar (novamente) filtro de equipe se definido
    if filtro_equipe and 'Equipe' in df_detalhado.columns:
        df_detalhado = df_detalhado[df_detalhado['Equipe'] == filtro_equipe]

    # Removido toggle de filtro; exibimos sempre todos os registros (vendas + devoluções)
    # DataFrames específicos de devoluções serão mostrados abaixo

    # Formatação dinâmica de colunas numéricas em moeda quando fizer sentido
    # Define configuração apenas para algumas colunas conhecidas de valores monetários
    col_config = {}
    money_cols = [c for c in df_detalhado.columns if c.lower() in [
        'total nf', '$ margem', 'valor unit.', 'vlr.icm', 'total_mercadoria', 'total mercadoria', 'mg.líq', 'mg.liq'
    ]]
    for c in money_cols:
        col_config[c] = st.column_config.NumberColumn(format="R$ %.2f")

    st.dataframe(
        df_detalhado,
        hide_index=True,
        use_container_width=True,
        column_config=col_config
    )

    # -------------------------------
    # Devoluções (NF) do mês
    # -------------------------------
    if 'Flag tipo' in df_mes.columns:
        df_devolucoes_normais = df_mes[df_mes['Flag tipo'] == 'D'].copy()
        if filtro_equipe and 'Equipe' in df_devolucoes_normais.columns:
            df_devolucoes_normais = df_devolucoes_normais[df_devolucoes_normais['Equipe'] == filtro_equipe]
        if not df_devolucoes_normais.empty:
            st.markdown("##### Devoluções (Notas Fiscais)")
            col_config_dev = {}
            money_cols_dev = [c for c in df_devolucoes_normais.columns if c.lower() in [
                'total nf', '$ margem', 'valor unit.', 'vlr.icm', 'total_mercadoria', 'total mercadoria', 'mg.líq', 'mg.liq'
            ]]
            for c in money_cols_dev:
                col_config_dev[c] = st.column_config.NumberColumn(format="R$ %.2f")
            st.dataframe(
                df_devolucoes_normais,
                hide_index=True,
                use_container_width=True,
                column_config=col_config_dev
            )
        else:
            st.markdown("_Não há devoluções (NF) no período._")

    # -------------------------------
    # Devoluções Extras (query_devo)
    # -------------------------------
    if 'df_devo_mes_extra' in locals() and df_devo_mes_extra is not None and not df_devo_mes_extra.empty:
        st.markdown("##### Devoluções Extras (Query Complementar)")
        df_devo_display = df_devo_mes_extra.copy()
        # Formatação monetária
        col_config_extra = {}
        money_cols_extra = [c for c in df_devo_display.columns if c.lower() in [
            'total_mercadoria', 'total mercadoria', 'valor', 'vl_total', 'vlr_total'
        ] or 'total' in c.lower()]
        for c in money_cols_extra:
            col_config_extra[c] = st.column_config.NumberColumn(format="R$ %.2f")
        st.dataframe(
            df_devo_display,
            hide_index=True,
            use_container_width=True,
            column_config=col_config_extra
        )
    else:
        st.markdown("_Não há devoluções extras no período._")

    # Guardar no session_state para exportação consistente
    st.session_state['df_detalhado_export'] = df_detalhado

st.divider()

# ========================
# EXPORTAÇÃO
# ========================
st.subheader("📤 Exportar Dados")

# Apenas exportação CSV (funcionalidade de PDF removida)
df_export = st.session_state.get('df_detalhado_export', df_vendas)
csv = df_export.to_csv(index=False)
st.download_button(
    label="📊 Baixar dados em CSV",
    data=csv,
    file_name=f"dados_detalhados_{meses[mes-1]}_{ano}.csv",
    mime="text/csv"
)

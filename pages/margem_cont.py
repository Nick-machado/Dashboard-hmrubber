import streamlit as st
from datetime import datetime, date
from calendar import monthrange
import pandas as pd
from functions.query import run_query
from functions.query_devo import run_query as run_query_devo
from functions.query_ped import run_query as run_query_ped
from functions.menu import menu_with_redirect
import plotly.graph_objects as go

# ========== CONFIGURAÇÃO DE PÁGINA ==========
st.set_page_config(layout="wide")
menu_with_redirect()

# ===========================================
# LÓGICA DE ROLE/SETOR NO INÍCIO DO CÓDIGO
# ===========================================
user_role = st.session_state.get("role", [])

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
        "",
        options=anos_disponiveis,
        index=anos_disponiveis.index(ano_atual),
        key="select_ano"
    )

if ano == ano_atual:
    meses_disponiveis = list(range(1, mes_atual + 1))
else:
    meses_disponiveis = list(range(1, 13))

with col1:
    st.markdown("### Mês")
    mes = st.selectbox(
        "",
        options=meses_disponiveis,
        format_func=lambda m: meses[m - 1],
        index=meses_disponiveis.index(mes_atual) if ano == ano_atual else 0,
        key="select_mes"
    )

# ================================
# Função cacheada - carrega tudo SEM filtro de setor
# ================================
@st.cache_data(ttl=300)
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

    total_devo_extra = abs(df_devo['TOTAL_MERCADORIA'].sum()) if not df_devo.empty else 0

    return df, df_devo, total_devo_extra

# ================================
# Carregando todos os dados (sem filtro de setor!)
# ================================
with st.spinner("🔄 Carregando dados... (o banco só será consultado se mudar o ano)"):
    df_periodo_all, df_devo_all, total_devo_extra_all = buscar_dados_periodo(ano)

# ========================================
# Aplique o filtro de setor apenas em RAM (valores conforme cada base)
# ========================================
if role == "Indústria":
    filtro_equipe = "INDUSTRIAL"   # Para df_periodo (query comum)
    filtro_grupo = "INDUSTRIAL"    # Para df_devo (query_devo)
elif role == "Varejo":
    filtro_equipe = "VAREJO"
    filtro_grupo = "VAREJO"
elif role == "Exportação Varejo":
    filtro_equipe = "EXPORTAÇÃO VAREJO"
    filtro_grupo = "EXPORTAÇÃO VAREJO"
else:  # Admin (todas equipes)
    filtro_equipe = None
    filtro_grupo = None

# Filtro na principal (query comum)
if filtro_equipe and 'Equipe' in df_periodo_all.columns:
    df_periodo = df_periodo_all[df_periodo_all['Equipe'] == filtro_equipe]
else:
    df_periodo = df_periodo_all.copy()

# Filtro na QUERY_DEVO (agora usando EQUIPE e mesmo valor do filtro_equipe)
if filtro_equipe and 'EQUIPE' in df_devo_all.columns:
    df_devo = df_devo_all[df_devo_all['EQUIPE'] == filtro_equipe]
else:
    df_devo = df_devo_all.copy()

# ================================
# O restante do código segue igual,
# mas usando os DataFrames já filtrados em RAM (df_periodo e df_devo)
# ================================

df_atual = df_periodo[df_periodo['Ano'] == ano]
prev_year = ano - 1
df_prev = df_periodo[df_periodo['Ano'] == prev_year]
df_mes = df_atual[df_atual['Mês'] == mes]

def calcular_faturamento_liquido(df, df_devo=None, meses_range=None, ano=None):
    vendas = df[df['Flag tipo'] == 'V'].groupby('Mês')['Total NF'].sum()
    devolucoes_normais = df[df['Flag tipo'] == 'D'].groupby('Mês')['Total NF'].sum()
    fat_liq = pd.Series({m: vendas.get(m, 0) - devolucoes_normais.get(m, 0) for m in range(1, 13)})
    if df_devo is not None and not df_devo.empty:
        if ano:
            devo_ano = df_devo[df_devo['Ano'] == ano]
        else:
            devo_ano = df_devo
        devo_mes = devo_ano.groupby('Mês')['TOTAL_MERCADORIA'].sum()
        for m in range(1, 13):
            fat_liq[m] -= abs(devo_mes.get(m, 0))
    return fat_liq

df_v = df_mes[df_mes['Flag tipo'] == 'V']
df_d = df_mes[df_mes['Flag tipo'] == 'D']

total_vendas = df_v['Total NF'].sum()
total_devolucoes_normais = df_d['Total NF'].sum()
df_devo_mes_extra = df_devo[(df_devo['Ano'] == ano) & (df_devo['Mês'] == mes)] if not df_devo.empty else pd.DataFrame()
devo_extra_mes = df_devo_mes_extra['TOTAL_MERCADORIA'].sum() if not df_devo_mes_extra.empty else 0

total_devolucoes_completo = total_devolucoes_normais + abs(devo_extra_mes)
fat_liquido = total_vendas - total_devolucoes_completo

vend_prev_mes = df_prev[df_prev['Flag tipo'] == 'V'].groupby('Mês')['Total NF'].sum().get(mes, 0)
dev_prev_mes = df_prev[df_prev['Flag tipo'] == 'D'].groupby('Mês')['Total NF'].sum().get(mes, 0)
devo_extra_mes_prev = df_devo[(df_devo['Ano'] == prev_year) & (df_devo['Mês'] == mes)]['TOTAL_MERCADORIA'].sum() if not df_devo.empty else 0
total_devolucoes_prev_completo = dev_prev_mes + abs(devo_extra_mes_prev)
fat_liq_prev_mes = vend_prev_mes - total_devolucoes_prev_completo

delta_fat_liquido = fat_liquido - fat_liq_prev_mes
delta_total_vendas = total_vendas - vend_prev_mes
delta_total_devolucoes_completo = total_devolucoes_completo - total_devolucoes_prev_completo

total_cmv = df_v['Vlr.ICM'].sum()
total_margem = df_v['$ Margem'].sum()
total_cmv_prev = df_prev[(df_prev['Mês'] == mes) & (df_prev['Flag tipo'] == 'V')]['Vlr.ICM'].sum()
total_margem_prev = df_prev[(df_prev['Mês'] == mes) & (df_prev['Flag tipo'] == 'V')]['$ Margem'].sum()
delta_total_cmv = total_cmv - total_cmv_prev
delta_total_margem = total_margem - total_margem_prev

# ========================
# Bloco das métricas
# ========================
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

# ===============================
# AQUI: Filtro por data E por setor (EQUIPE) para os pedidos
# ===============================
@st.cache_data(ttl=300)
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
df_pedidos_mes = df_pedidos[
    (df_pedidos['Data'] >= pd.Timestamp(primeiro_dia)) &
    (df_pedidos['Data'] <= pd.Timestamp(ultimo_dia))
]

# Filtro por setor/coluna EQUIPE, se necessário
if filtro_equipe and 'EQUIPE' in df_pedidos_mes.columns:
    df_pedidos_mes = df_pedidos_mes[df_pedidos_mes['EQUIPE'] == filtro_equipe]

if 'ID_PEDIDO' in df_pedidos_mes.columns:
    total_pedidos_mes = df_pedidos_mes['ID_PEDIDO'].nunique()
else:
    total_pedidos_mes = 0

with col6:
    st.metric("Total Pedidos", total_pedidos_mes)

# ========================
# O restante segue igual (gráficos etc)
# ========================

with st.spinner("📊 Gerando gráfico comparativo..."):
    meses_range = meses_disponiveis
    meses_labels = [meses[m - 1] for m in meses_range]

    fat_prev = calcular_faturamento_liquido(df_prev, df_devo, meses_range, prev_year).loc[meses_range].tolist()
    fat_sel = calcular_faturamento_liquido(df_atual, df_devo, meses_range, ano).loc[meses_range].tolist()
    fmt_prev = [f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") for v in fat_prev]
    fmt_sel = [f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") for v in fat_sel]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=meses_labels,
        y=fat_prev,
        mode="lines+markers+text",
        name=str(prev_year),
        text=fmt_prev,
        textposition="bottom center",
        textfont=dict(size=12),
        line=dict(width=3, dash='dash'),
        marker=dict(size=6)
    ))
    fig.add_trace(go.Scatter(
        x=meses_labels,
        y=fat_sel,
        mode="lines+markers+text",
        name=str(ano),
        text=fmt_sel,
        textposition="top center",
        textfont=dict(size=12),
        line=dict(width=3),
        marker=dict(size=6)
    ))
    fig.update_layout(
        title=f"Faturamento Líquido Mensal: {ano} vs {prev_year}",
        xaxis_title="Mês",
        yaxis_title="R$",
        margin=dict(l=40, r=40, t=50, b=40)
    )
    st.plotly_chart(fig, use_container_width=True)


with st.expander("Visualizar dados detalhados", expanded=False):
    st.markdown(f"#### Dados do mês de {meses[mes - 1]} de {ano}")
    st.dataframe(
        df_mes,
        column_config={
            "Total NF": st.column_config.NumberColumn(format="R$ %.2f"),
            "Vlr.ICM": st.column_config.NumberColumn(format="R$ %.2f"),
            "$ Margem": st.column_config.NumberColumn(format="R$ %.2f"),
        },
        hide_index=True,
        use_container_width=True
    )
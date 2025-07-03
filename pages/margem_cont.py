import streamlit as st
from datetime import datetime, date
import pandas as pd
from functions.query import run_query
from functions.menu import menu_with_redirect
import plotly.graph_objects as go

# ================================
# Configuração da página e menu
# ================================
st.set_page_config(layout="wide")
menu_with_redirect()

# ================================
# Função cacheada - apenas pelo ano
# ================================
@st.cache_data(ttl=300)
def buscar_dados_periodo(ano: int) -> pd.DataFrame:
    print(f"Buscando do banco para ano {ano}")  # Debug
    inicio = date(ano - 1, 1, 1)
    fim = date(ano, 12, 31)
    df = run_query(inicio.strftime("%Y-%m-%d"), fim.strftime("%Y-%m-%d"))
    df['Data'] = pd.to_datetime(df['Data'])
    df['Mês'] = df['Data'].dt.month
    df['Ano'] = df['Data'].dt.year
    return df

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
    meses_disponiveis = list(range(1, mes_atual + 1))  # até o mês atual
else:
    meses_disponiveis = list(range(1, 13))             # todos os meses

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
# Carregando dados
# ================================
with st.spinner("🔄 Carregando dados... (o banco só será consultado se mudar o ano)"):
    df_periodo = buscar_dados_periodo(ano)

df_atual = df_periodo[df_periodo['Ano'] == ano]
prev_year = ano - 1
df_prev = df_periodo[df_periodo['Ano'] == prev_year]
df_mes = df_atual[df_atual['Mês'] == mes]

# ========== Função para calcular faturamento líquido mensal ==========
def calcular_faturamento_liquido(df):
    vendas = df[df['Flag tipo'] == 'V'].groupby('Mês')['Total NF'].sum()
    devolucoes = df[df['Flag tipo'] == 'D'].groupby('Mês')['Total NF'].sum()
    return pd.Series({m: vendas.get(m, 0) - devolucoes.get(m, 0) for m in range(1, 13)})

# ================================
# Cálculo de métricas para o mês selecionado
# ================================
df_v = df_mes[df_mes['Flag tipo'] == 'V']
df_d = df_mes[df_mes['Flag tipo'] == 'D']
total_vendas = df_v['Total NF'].sum()
total_devolucoes = df_d['Total NF'].sum()
fat_liquido = total_vendas - total_devolucoes

# Comparativo mês ano anterior (para todas as métricas relevantes)
vend_prev_mes = df_prev[df_prev['Flag tipo'] == 'V'].groupby('Mês')['Total NF'].sum().get(mes, 0)
dev_prev_mes = df_prev[df_prev['Flag tipo'] == 'D'].groupby('Mês')['Total NF'].sum().get(mes, 0)
fat_liq_prev_mes = vend_prev_mes - dev_prev_mes
delta_fat_liquido = fat_liquido - fat_liq_prev_mes

# NOVO: Cálculo dos deltas para as outras métricas
# Total Faturado
delta_total_vendas = total_vendas - vend_prev_mes
# Total Devoluções
delta_total_devolucoes = total_devolucoes - dev_prev_mes

# CMV e Margem (ano atual)
total_cmv = df_v['Vlr.ICM'].sum()
total_margem = df_v['$ Margem'].sum()

# CMV e Margem do mês correspondente do ano anterior
total_cmv_prev = df_prev[(df_prev['Mês'] == mes) & (df_prev['Flag tipo'] == 'V')]['Vlr.ICM'].sum()
total_margem_prev = df_prev[(df_prev['Mês'] == mes) & (df_prev['Flag tipo'] == 'V')]['$ Margem'].sum()
delta_total_cmv = total_cmv - total_cmv_prev
delta_total_margem = total_margem - total_margem_prev

# Total de pedidos no mês (sem delta)
total_pedidos = len(df_mes)

# ================================
# Exibição de métricas
# ================================
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
        f"R$ {total_devolucoes:,.2f}",
        f"R$ {delta_total_devolucoes:,.2f}",
        delta_color="normal" if delta_total_devolucoes >= 0 else "inverse"
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
    st.metric("Total Pedidos", f"{total_pedidos}")

# ================================
# Gráfico de linha comparativo (faturamento líquido por mês)
# ================================
with st.spinner("📊 Gerando gráfico comparativo..."):
    meses_range = meses_disponiveis
    meses_labels = [meses[m - 1] for m in meses_range]

    fat_prev = calcular_faturamento_liquido(df_prev).loc[meses_range].tolist()
    fat_sel = calcular_faturamento_liquido(df_atual).loc[meses_range].tolist()
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

# ================================
# Exibição dos dados brutos do mês selecionado
# ================================
st.dataframe(df_mes.reset_index(drop=True), use_container_width=True)
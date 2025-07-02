import streamlit as st
from datetime import datetime, date
import plotly.graph_objects as go
import calendar
from functions.query import gerar_planilha_concatenada as query
from functions.query_devo import run_query as query_devo
from functions.menu import menu_with_redirect

st.set_page_config(layout="wide")
menu_with_redirect()

meses = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

hoje = datetime.now()
mes_atual = hoje.month
ano_atual = hoje.year
anos_disponiveis = list(range(ano_atual - 5, ano_atual + 1))

# Filtros
col1, col2 = st.columns([2, 1])

with col2:
    st.markdown("### Ano")
    ano = st.selectbox("", options=anos_disponiveis, index=anos_disponiveis.index(ano_atual))

meses_disponiveis = list(range(1, 13)) if ano < ano_atual else list(range(1, mes_atual + 1))

with col1:
    st.markdown("### Mês")
    mes = st.selectbox(
        "",
        options=meses_disponiveis,
        format_func=lambda m: meses[m - 1],
        index=meses_disponiveis.index(mes_atual if ano == ano_atual else 12)
    )

indice_mes = mes
primeiro_dia = date(ano, indice_mes, 1)
ultimo_dia = date(ano, indice_mes, calendar.monthrange(ano, indice_mes)[1])

if indice_mes == 1:
    mes_anterior = 12
    ano_anterior = ano - 1
else:
    mes_anterior = indice_mes - 1
    ano_anterior = ano

primeiro_dia_ant = date(ano_anterior, mes_anterior, 1)
ultimo_dia_ant = date(ano_anterior, mes_anterior, calendar.monthrange(ano_anterior, mes_anterior)[1])

# Formatação
primeiro_dia_str = primeiro_dia.strftime("%Y-%m-%d")
ultimo_dia_str = ultimo_dia.strftime("%Y-%m-%d")
primeiro_dia_ant_str = primeiro_dia_ant.strftime("%Y-%m-%d")
ultimo_dia_ant_str = ultimo_dia_ant.strftime("%Y-%m-%d")

st.write(f"Mês selecionado: {meses[indice_mes - 1]} de {ano}")
st.write(f"Período: {primeiro_dia_str} a {ultimo_dia_str}")

# Queries com spinner
with st.spinner("🔄 Carregando dados do período selecionado..."):
    df_v = query(primeiro_dia_str, ultimo_dia_str, "V")
    df_d1 = query(primeiro_dia_str, ultimo_dia_str, "D")
    df_d2 = query_devo(primeiro_dia_str, ultimo_dia_str)

    df_v_ant = query(primeiro_dia_ant_str, ultimo_dia_ant_str, "V")
    df_d1_ant = query(primeiro_dia_ant_str, ultimo_dia_ant_str, "D")
    df_d2_ant = query_devo(primeiro_dia_ant_str, ultimo_dia_ant_str)


with st.spinner("🔄 Processando dados..."):
    # Cálculos
    total_fat = df_v["Total NF"].sum()
    total_fat_ant = df_v_ant["Total NF"].sum()
    delta_fat = total_fat - total_fat_ant

    total_dev = df_d1["Total NF"].sum() - df_d2["TOTAL_NF"].sum()
    total_dev_ant = df_d1_ant["Total NF"].sum() - df_d2_ant["TOTAL_NF"].sum()
    delta_dev = total_dev - total_dev_ant

    total_fat_liq = total_fat - total_dev
    total_fat_liq_ant = total_fat_ant - total_dev_ant
    delta_fat_liq = total_fat_liq - total_fat_liq_ant

    total_cmv = df_v["Vlr.ICM"].sum()
    total_cmv_ant = df_v_ant["Vlr.ICM"].sum()
    delta_cmv = total_cmv - total_cmv_ant

    total_margem = df_v["$ Margem"].sum()
    total_margem_ant = df_v_ant["$ Margem"].sum()
    delta_margem = total_margem - total_margem_ant

# Exibição
st.dataframe(df_v, use_container_width=True, hide_index=True)
st.dataframe(df_d1, use_container_width=True, hide_index=True)
st.dataframe(df_d2, use_container_width=True, hide_index=True)

col1_1, col2_1, col3_1 = st.columns(3)
col1_2, col2_2, col3_2 = st.columns(3)

with col1_1:
    with st.container(key="Total_fat", border=True):
        delta_color_fat = "inverse" if delta_fat < 0 else "normal"
        st.metric("Total Faturado", f"R$ {total_fat:,.2f}", f"R$ {delta_fat:,.2f}", delta_color=delta_color_fat)

with col2_1:
    with st.container(key="Total_dev", border=True):
        delta_color_dev = "inverse" if delta_dev < 0 else "normal"
        st.metric("Total Devoluções", f"R$ {total_dev:,.2f}", f"R$ {delta_dev:,.2f}", delta_color=delta_color_dev)

with col3_1:
    with st.container(key="Total_fat_liq", border=True):
        delta_color_liq = "inverse" if delta_fat_liq < 0 else "normal"
        st.metric("Total Faturado Líquido", f"R$ {total_fat_liq:,.2f}", f"R$ {delta_fat_liq:,.2f}", delta_color=delta_color_liq)

with col1_2:
    with st.container(key="Total_cmv", border=True):
        delta_color_cmv = "inverse" if delta_cmv < 0 else "normal"
        st.metric("Total CMV", f"R$ {total_cmv:,.2f}", f"R$ {delta_cmv:,.2f}", delta_color=delta_color_cmv)

with col2_2:
    with st.container(key="Total_margem", border=True):
        delta_color_margem = "inverse" if delta_margem < 0 else "normal"
        st.metric("Total Margem", f"R$ {total_margem:,.2f}", f"R$ {delta_margem:,.2f}", delta_color=delta_color_margem)

with col3_2:
    with st.container(key="Total_pedidos", border=True):
        st.title("Total Pedidos")

# Gráfico com spinner
with st.spinner("📊 Gerando gráfico de faturamento líquido mensal..."):
    meses_hist = meses_disponiveis
    fat_liq_mensal = []

    for mes_i in meses_hist:
        primeiro_dia_i = date(ano, mes_i, 1)
        ultimo_dia_i = date(ano, mes_i, calendar.monthrange(ano, mes_i)[1])

        df_v_i = query(primeiro_dia_i.strftime("%Y-%m-%d"), ultimo_dia_i.strftime("%Y-%m-%d"), "V")
        df_d1_i = query(primeiro_dia_i.strftime("%Y-%m-%d"), ultimo_dia_i.strftime("%Y-%m-%d"), "D")
        df_d2_i = query_devo(primeiro_dia_i.strftime("%Y-%m-%d"), ultimo_dia_i.strftime("%Y-%m-%d"))

        fat_liq_i = df_v_i["Total NF"].sum() - (df_d1_i["Total NF"].sum() - df_d2_i["TOTAL_NF"].sum())
        fat_liq_mensal.append(fat_liq_i)

    meses_labels = [meses[m - 1] for m in meses_hist]
    valores_formatados = [f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") for v in fat_liq_mensal]

    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=meses_labels,
        y=fat_liq_mensal,
        mode="lines+markers+text",
        name="Faturamento Líquido",
        text=valores_formatados,
        textposition="top center",
        textfont=dict(size=16),
        line=dict(width=3),
        marker=dict(size=8)
    ))

    fig_line.update_layout(
        title="Faturamento Líquido Mensal",
        title_x=0.5,
        xaxis_title="Mês",
        yaxis_title="R$",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=40, t=40, b=40)
    )

    fig_line.update_xaxes(
        showgrid=True,
        gridcolor='rgba(255,255,255,0.3)',
        tickfont=dict(size=12)
    )
    fig_line.update_yaxes(
        showgrid=True,
        gridcolor='rgba(255,255,255,0.3)',
        tickfont=dict(size=12)
    )

    st.plotly_chart(fig_line, use_container_width=True)
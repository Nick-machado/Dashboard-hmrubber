import streamlit as st
import datetime
import requests
import plotly.express as px
import pandas as pd
from calendar import monthrange
from functions.query import gerar_planilha_concatenada as query
from functions.menu import menu_with_redirect

menu_with_redirect()

st.title("Mapa de Calor - Faturamento por Estado")

# ==========================
# 🎯 Seletor de mês e ano
# ==========================
hoje = datetime.date.today()
mes_atual = hoje.month
ano_atual = hoje.year

meses = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}
anos = list(range(ano_atual - 5, ano_atual + 1))

col1, col2 = st.columns(2)
with col1:
    mes = st.selectbox("Selecione o mês", options=list(meses.keys()), format_func=lambda m: meses[m], index=mes_atual - 1)
with col2:
    ano = st.selectbox("Selecione o ano", options=anos, index=anos.index(ano_atual))

dia_inicio = datetime.date(ano, mes, 1)
dia_fim = datetime.date(ano, mes, monthrange(ano, mes)[1])

# ==========================
# 📦 Consulta e agregação
# ==========================
df = query(dia_inicio, dia_fim)
df_estado_raw = df.groupby("UF")["Total NF"].sum().reset_index()

ufs_brasil = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT',
    'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO',
    'RR', 'SC', 'SP', 'SE', 'TO'
]
df_ufs = pd.DataFrame(ufs_brasil, columns=["UF"])
df_estado = df_ufs.merge(df_estado_raw, on="UF", how="left").fillna(0)

df_estado["Total NF em R$"] = df_estado["Total NF"].apply(
    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
)
df_estado = df_estado.rename(columns={"UF": "Estado", "Total NF": "Total NF (R$)"})

# ==========================
# 🗺️ Mapa de calor
# ==========================
geojson_url = 'https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson'
geojson_data = requests.get(geojson_url).json()

color_scale = ["#687cff", "#e7f3b5", "#bed62f"]

fig = px.choropleth(
    df_estado,
    geojson=geojson_data,
    locations='Estado',
    locationmode='geojson-id',
    featureidkey='properties.sigla',
    color='Total NF (R$)',
    color_continuous_scale=color_scale,
    title='Faturamento por Estado (R$) - mapa de calor',
    hover_name='Estado',
    hover_data={'Total NF (R$)': False, 'Total NF em R$': True},
)

fig.update_geos(
    fitbounds="locations",
    visible=False,
    bgcolor='rgba(0,0,0,0)'
)

fig.update_layout(
    title='Faturamento por Estado (R$) - mapa de calor',
    title_x=0.5,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin={"r": 0, "t": 40, "l": 0, "b": 0}
)

# ==========================
# 📊 Tabela final
# ==========================
df_estado = df_estado.sort_values(by="Total NF (R$)", ascending=False)
st.dataframe(df_estado[["Estado", "Total NF em R$"]], use_container_width=True, hide_index=True)

# ==========================
# 📍 Exibe gráfico
# ==========================
st.plotly_chart(fig, use_container_width=True)
st.write(dia_fim)
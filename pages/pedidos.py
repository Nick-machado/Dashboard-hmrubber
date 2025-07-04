import streamlit as st
import pandas as pd
import datetime
import calendar
import plotly.express as px

from functions.query_ped import run_query as query
from functions.menu import menu_with_redirect

st.set_page_config(layout="wide")
menu_with_redirect()

# Data inicial: primeiro dia do mês atual
hoje = datetime.date.today()
data_inicial = hoje.replace(day=1)

# Data final: último dia do mesmo mês, ano que vem
ano_que_vem = hoje.year + 1
ultimo_dia_mes = calendar.monthrange(ano_que_vem, hoje.month)[1]
data_final = datetime.date(ano_que_vem, hoje.month, ultimo_dia_mes)

st.info(f"Período exibido: {data_inicial.strftime('%d/%m/%Y')} até {data_final.strftime('%d/%m/%Y')}")

# Query
df = query(data_inicial, data_final)

if not df.empty:
    situacao_count = df['SITUACAO'].value_counts().reset_index()
    situacao_count.columns = ['SITUACAO', 'QTD']

    fig = px.pie(situacao_count, names='SITUACAO', values='QTD', title='Quantidade por Situação')
    st.plotly_chart(fig, use_container_width=True)

    filtro = st.selectbox("Filtrar por situação", options=['Todas'] + situacao_count['SITUACAO'].tolist())

    if filtro == "Todas":
        st.dataframe(df, hide_index=True)
    else:
        st.dataframe(df[df['SITUACAO'] == filtro], hide_index=True)
else:
    st.info("Não há dados para o período selecionado.")
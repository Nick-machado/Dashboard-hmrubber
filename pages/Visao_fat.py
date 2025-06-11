import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
from functions.query import query
from functions.func_margem import grafico_margem, dataframe_margem

# 1) Guarda hoje e ontem como date corretos
hoje = datetime.date.today()
ontem = hoje - datetime.timedelta(days=1)

# 2) Inputs de data (agora com defaults válidos)
col1, col2 = st.columns(2)
with col1:
    data_inicial = st.date_input("Data inicial", ontem)
with col2:
    data_final   = st.date_input("Data final", hoje)

df = query(data_inicial, data_final)

tab1, tab2, tab3, tab4 = st.tabs(["Estado", "Produto", "Cliente", "Vendedor"])

with tab1:
    df_estado = dataframe_margem(df, "UF")
    fig_estado = grafico_margem(df_estado, "UF")
    st.plotly_chart(fig_estado, use_container_width=True)

    
with tab2:
    df_produto = dataframe_margem(df, "Produto")
    fig_produto = grafico_margem(df_produto, "Produto")
    st.plotly_chart(fig_produto, use_container_width=True)
with tab3:
    df_cliente = dataframe_margem(df, "Cliente")
    fig_cliente = grafico_margem(df_cliente, "Cliente")
    st.plotly_chart(fig_cliente, use_container_width=True)
with tab4:
    df_vendedor = dataframe_margem(df, "Vendedor")
    fig_vendedor = grafico_margem(df_vendedor, "Vendedor")
    st.plotly_chart(fig_vendedor, use_container_width=True)
import streamlit as st
import datetime
from functions.query_margem import gerar_planilha_concatenada as query
from functions.func_margem import grafico_margem, dataframe_margem

# 1) Guarda hoje e ontem como date corretos
hoje = datetime.date.today()
ontem = hoje - datetime.timedelta(days=1)

tab1, tab2 = st.tabs(["Diário", "Mensal"])

with tab1:
    st.subheader("Margem de Contribuição - Diário")

    data_diaria = st.date_input("Data", value=hoje, format="DD/MM/YYYY")

    df_diaria = query(data_diaria, data_diaria)

    df_estado = dataframe_margem(df_diaria, "UF")
    fig_estado = grafico_margem(df_estado, "UF")
    st.plotly_chart(fig_estado, use_container_width=True)
with tab2:
    st.subheader("Margem de Contribuição - Mensal")

    df_produto = dataframe_margem(df_diaria, "Produto")
    fig_produto = grafico_margem(df_produto, "Produto")
    st.plotly_chart(fig_produto, use_container_width=True)
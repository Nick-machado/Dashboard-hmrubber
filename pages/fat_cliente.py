import streamlit as st
import datetime
from functions.query import gerar_planilha_concatenada as query
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

df_cliente = dataframe_margem(df, "Cliente")
fig_cliente = grafico_margem(df_cliente, "Cliente")
st.plotly_chart(fig_cliente, use_container_width=True)

soma = df["Total NF"].sum()
st.subheader(f"**Total de Vendas por Cliente: R$ {soma:,.2f}**")

st.subheader("")
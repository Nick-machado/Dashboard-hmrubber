import streamlit as st
import pyodbc
import pandas as pd
import datetime
from functions.query_devo import run_query as query
from functions.menu import menu_with_redirect

menu_with_redirect()

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
st.dataframe(df)
total_nf = df["TOTAL_NF"].sum()

# Exibe o resultado formatado
st.subheader(f"**Total de devoluções: R$ {total_nf:,.2f}**")
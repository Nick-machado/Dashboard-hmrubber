import streamlit as st
import pyodbc
import pandas as pd
import datetime
from functions.query import gerar_planilha_concatenada as query


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
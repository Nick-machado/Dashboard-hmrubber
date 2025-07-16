import streamlit as st
import pandas as pd
import datetime
from functions.query import run_query as query
from functions.query import gerar_soma
from functions.menu import menu_with_redirect

st.set_page_config(layout="wide")
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

df1 = query(data_inicial, data_final, empresa_id=1, flag_tipo='V')

st.dataframe(df1, use_container_width=True, hide_index=True)

st.write(len(df1.index))
st.write(round(gerar_soma(data_inicial, data_final, empresa_id=1, flag_tipo='V'), 2))

df2 = query(data_inicial, data_final, empresa_id=2, flag_tipo='V')

st.dataframe(df2, use_container_width=True, hide_index=True)

st.write(len(df2.index))
st.write(round(gerar_soma(data_inicial, data_final, empresa_id=2, flag_tipo='V'), 2))
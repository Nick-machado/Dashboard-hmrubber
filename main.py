import streamlit as st
import pandas as pd

st.title("Hello Streamlit-er 👋")

df = pd.read_excel('margem junho filial.xls')

st.dataframe(df)
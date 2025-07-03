import streamlit as st
from functions.menu import menu
from functions.connect import test_connection

menu()

# Here goes your normal streamlit app
st.title("Bem vindo ao Dashboard da HM Rubber!")
st.markdown(f"Você está logado como: {st.session_state.username}. Acessos: {st.session_state.role}")


st.write("### Testando conexão com o banco de dados...")
with st.spinner("Gerando conexão"):
    if test_connection():
        st.success("Conexão bem-sucedida!")
    else:
        st.error("Erro ao conectar ao banco de dados.")
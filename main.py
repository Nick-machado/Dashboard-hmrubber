import streamlit as st
from functions.menu import menu
import setup_odbc

# Executar configuração apenas uma vez
if not setup_odbc.setup_firebird_odbc():
    import streamlit as st
    st.error("❌ Erro na configuração do driver ODBC Firebird")
    st.info("Verifique os logs do Heroku para mais detalhes")
    st.stop()

menu()

# Here goes your normal streamlit app
st.title("Bem vindo ao Dashboard da HM Rubber!")
st.markdown(f"Você está logado como: {st.session_state.username}.")
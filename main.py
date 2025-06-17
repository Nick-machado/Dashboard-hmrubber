import streamlit as st
from functions.menu import menu

menu()

# Here goes your normal streamlit app
st.title("Bem vindo ao Dashboard da HM Rubber!")
st.markdown(f"Você está logado como: {st.session_state.username}.")
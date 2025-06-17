import streamlit as st
import requests
from functions.menu import menu_with_redirect

menu_with_redirect()

st.title("Painel Administrativo")
st.write("Esta é a página administrativa, visível apenas para usuários com permissão de administrador.")

tab1, tab2, tab3, tab4 = st.tabs(["Adicionar usuário", "Alterar dados do usuário", "Controlar acessos", "Deletar usuário"])

with tab1:
    st.write(st.session_state.id)
with tab2:
    st.write(st.session_state.id)

    response = requests.get("http://localhost:8080/users")
    if response.status_code == 200:
        data = response.json()
        
        users = data.get("users", [])
    else:
        st.error("Erro ao carregar usuários.")

    if users:
        selected_user = st.selectbox(
            "Selecione um usuário",
            options=[user["nome"] for user in users]
        )
    else:
        st.warning("Nenhum usuário encontrado.")

        
with tab3:

    response = requests.get("http://localhost:8080/users")
    if response.status_code == 200:
        data = response.json()
        
        users = data.get("users", [])
    else:
        st.error("Erro ao carregar usuários.")

    if users:
        selected_user = st.selectbox(
            "Selecione um usuário",
            options=[user["nome"] for user in users]
        )
    else:
        st.warning("Nenhum usuário encontrado.")

with tab4:
    st.write(st.session_state.id)

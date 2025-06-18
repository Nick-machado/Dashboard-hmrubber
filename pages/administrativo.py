import streamlit as st
import time
import requests
from functions.menu import menu_with_redirect

st.set_page_config(layout="wide")
menu_with_redirect()

@st.dialog("Confirmar Alteração")
def confirmar_alteração(nome, permissoes, id):
    st.header("Tem certeza que deseja alterar os acessos desse usuário?")
    st.write(f"Usuário: {nome}")
    st.write(f"Permissões: {', '.join(permissoes)}")
    col1, col2 = st.columns(2)

    with col1:
       confirmar = st.button("Confirmar", key="confirmar", use_container_width=True, type="primary")
    with col2:
        cancelar = st.button("Cancelar", key="cancelar", use_container_width=True, type="secondary")
    
    if confirmar:
        requests_alterar = requests.patch(f"http://localhost:8080/users/update/{id}", json={
            "permissoes": permissoes
        })
        if requests_alterar.status_code != 200:
            st.error("Erro ao alterar permissões do usuário.")
            time.sleep(2)
            st.rerun()
        else:
            st.success("Permissões alteradas com sucesso!")
            time.sleep(2)
            st.rerun()
    
    if cancelar:
        st.error("Alteração cancelada.")
        time.sleep(2)
        st.rerun()

@st.dialog("Deletar Usuário")
def deletar_usuario(nome, id):
    st.header("Tem certeza que deseja alterar os acessos desse usuário?")
    st.write(f"Usuário: {nome}")
    col1, col2 = st.columns(2)
    with col1:
       confirmar_del = st.button("Confirmar", key="confirmar_deletar", use_container_width=True, type="primary")
    with col2:
        cancelar_del = st.button("Cancelar", key="cancelar_deletar", use_container_width=True, type="secondary")
    if confirmar_del:
        requests_deletar = requests.delete(f"http://localhost:8080/users/delete/{id}")
        if requests_deletar.status_code != 200:
            st.error("Erro ao deletar usuário.")
            time.sleep(2)
            st.rerun()
        else:
            st.success("Usuário deletado com sucesso!")
            time.sleep(2)
            st.rerun()
    if cancelar_del:
        st.error("Ação cancelada.")
        time.sleep(2)
        st.rerun()

st.title("Painel Administrativo")
st.write("Esta é a página administrativa, visível apenas para usuários com permissão de administrador.")

tab1, tab2, tab3 = st.tabs(["Adicionar usuário", "Controlar acessos", "Deletar usuário"])

with tab1:
    st.subheader("Adicionar Usuário")

    # Buscar permissões
    response = requests.get("http://localhost:8080/permissions")
    if response.status_code == 200:
        permissions_data = response.json().get("permissoes", [])
        permissions_list = [perm["nome"] for perm in permissions_data]
    else:
        st.error("Erro ao carregar permissões.")
        permissions_list = []

    with st.form("form_adicionar_usuario"):
        nome = st.text_input("Nome")
        email = st.text_input("E-mail")
        permissoes = st.multiselect("Permissões", permissions_list)
        senha = st.text_input("Senha", type="password")
        confirmar_senha = st.text_input("Confirmar Senha", type="password")

        submitted = st.form_submit_button("Adicionar Usuário",type="primary")

        if submitted:
            if not nome or not email or not senha or not confirmar_senha:
                st.warning("Preencha todos os campos.")
            elif senha != confirmar_senha:
                st.error("As senhas não coincidem.")
            elif not permissoes:
                st.warning("Selecione pelo menos uma permissão.")
            else:
                payload = {
                    "nome": nome,
                    "email": email,
                    "senha": senha,
                    "permissoes": permissoes
                }
                response = requests.post("http://localhost:8080/users/add", json=payload)

                if response.status_code == 201:
                    st.success("Usuário adicionado com sucesso!")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error(f"Erro ao adicionar usuário. Código: {response.status_code}")
                    try:
                        st.error(response.json().get("detail", "Erro desconhecido."))
                    except:
                        pass
        
with tab2:
    # Buscar usuários
    response_users = requests.get("http://localhost:8080/users")
    if response_users.status_code == 200:
        data_users = response_users.json()
        users = data_users.get("users", [])
    else:
        st.error("Erro ao carregar usuários.")
        users = []

    # Buscar permissões
    response_permissions = requests.get("http://localhost:8080/permissions")
    if response_permissions.status_code == 200:
        data_permissions = response_permissions.json()
        permissions = data_permissions.get("permissoes", [])
    else:
        st.error("Erro ao carregar permissões.")
        permissions = []

    if users:
        
        user_id_map = {user["nome"]: user["id"] for user in users}

        selected_user = st.selectbox(
            "Selecione um usuário",
            options=[user["nome"] for user in users],
            key="selected_user_2",
        )
    else:
        st.warning("Nenhum usuário encontrado.")

    if permissions:
        selected_permissions = st.multiselect(
            "Selecione as permissões para o usuário",
            options=[perm["nome"] for perm in permissions],
            key="selected_permissions"
        )
    else:
        st.warning("Nenhuma permissão encontrada.")

    confirma_permissoes = st.button(
        "Confirmar Permissões")
    
    if confirma_permissoes:
        if not selected_permissions:
            st.error("Por favor, selecione pelo menos uma permissão.")
        else:
            selected_user_id = user_id_map.get(selected_user)
            if selected_user_id is None:
                st.error("Erro ao obter o ID do usuário selecionado.")
            else:
                confirmar_alteração(selected_user, sorted(selected_permissions), selected_user_id)

with tab3:
    response_users = requests.get("http://localhost:8080/users")
    if response_users.status_code == 200:
        data_users = response_users.json()
        users = data_users.get("users", [])
    else:
        st.error("Erro ao carregar usuários.")
        users = []
    if users:
        
        user_id_map = {user["nome"]: user["id"] for user in users}

        selected_user = st.selectbox(
            "Selecione um usuário",
            options=[user["nome"] for user in users],
            key="selected_user_3",
        )
    else:
        st.warning("Nenhum usuário encontrado.")

    confirma_deletar = st.button(
        "Deletar Usuário", type="primary")
    
    if confirma_deletar:
        if not selected_user:
            st.error("Por favor, selecione um usuário.")
        else:
            selected_user_id = user_id_map.get(selected_user)
            if selected_user_id is None:
                st.error("Erro ao obter o ID do usuário selecionado.")
            else:
                deletar_usuario(selected_user, selected_user_id)
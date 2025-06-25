import streamlit as st
import requests
from dotenv import load_dotenv
import os

load_dotenv()

url_login = os.getenv("url_api")

# ───── Funções de Autenticação ─────
def autenticar_usuario():

    """Authenticate user and manage login state."""
    if st.session_state.get("authenticated"):
        return True

    with st.form("Login"):
        st.subheader("Login")
        st.write("Por favor, faça login para acessar o sistema.")
        username = st.text_input("Usuário (E-mail)")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        url = f"{url_login}/users/login/{username}/{password}"
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                dados = resp.json()
                st.session_state['authenticated'] = True
                st.session_state['id'] = dados['id']
                st.session_state['user_data'] = carregar_dados_usuario(st.session_state['id'])
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")
                return False
        except requests.exceptions.RequestException as e:
            return False, f"Erro na conexão: {e}"

def carregar_dados_usuario(id):
    url = f"{url_login}/users/{id}"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            return resp.json()
        else:
            return None
    except requests.exceptions.RequestException:
        return None
    
def menu_autenticado():
    # Verificação segura dos dados de usuário
    user_data = st.session_state.get('user_data')
    if not user_data or 'permissoes' not in user_data or 'nome' not in user_data:
        st.error("Erro ao carregar dados do usuário. Faça login novamente.")
        logout()
        return

    st.session_state['role'] = user_data['permissoes']
    st.session_state['username'] = user_data['nome']

    st.sidebar.subheader("Menu Principal", divider=True)
    st.sidebar.page_link("main.py", label="Home Page", icon="🏡")

    if "Admin" in st.session_state['role']:
        st.sidebar.subheader("Administração", divider=True)
        st.sidebar.page_link("pages/administrativo.py", label="🛠️ Painel Administrativo")

    st.sidebar.subheader("Relatórios", divider=True)
    st.sidebar.page_link("pages/planilha.py", label="📊 Tabela de Vendas")
    st.sidebar.page_link("pages/margem_cont.py", label="📈 Margem de Contribuição")
    st.sidebar.page_link("pages/Visao_fat.py", label="🔍 Visão Faturamento")
    st.sidebar.page_link("pages/fat_cliente.py", label="👥 Faturamento Cliente")
    st.sidebar.page_link("pages/fat_uf.py", label="🗺️ Faturamento UF")
    st.sidebar.page_link("pages/devolucao.py", label="📦 Devoluções")
    st.sidebar.page_link("pages/pedidos.py", label="📝 Pedidos")

    st.sidebar.divider()

    if st.sidebar.button("🔓 Logout", type="primary", use_container_width=True):
        logout()

def menu_nao_autenticado():
    # Show a navigation menu for unauthenticated users
    # st.sidebar.page_link("home.py", label="Log in")
    pass

def logout():
    st.session_state.clear()
    st.rerun()

# ───── Menu e Controle de Acesso ─────
def menu():
    if not autenticar_usuario():
        menu_nao_autenticado()
        st.stop()
    else:
        menu_autenticado()

def menu_with_redirect():
    # Redirect users to the main page if not logged in, otherwise continue to
    # render the navigation menu
    if not autenticar_usuario():
        st.switch_page("main.py")
    menu()
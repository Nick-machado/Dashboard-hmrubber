import streamlit as st
import requests

# ───── Configuração da página ─────
st.set_page_config(page_title="HMRubber", page_icon="🔑", layout="centered")

# ───── Estados de Sessão ─────
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'usuario' not in st.session_state:
    st.session_state['usuario'] = None
if 'permissoes' not in st.session_state:
    st.session_state['permissoes'] = []

# ───── Funções ─────
def autenticar_usuario(email, senha):
    url = f"http://localhost:8080/users/login/{email}/{senha}"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            dados = resp.json()
            return (True, dados) if dados.get("status") == 200 else (False, dados.get("message", "Erro desconhecido"))
        elif resp.status_code == 404:
            return False, "Usuário não encontrado"
        elif resp.status_code == 401:
            return False, "Senha incorreta"
        else:
            return False, f"Erro HTTP {resp.status_code}: {resp.text}"
    except requests.exceptions.RequestException as e:
        return False, f"Erro na conexão: {e}"

def carregar_dados_usuario(id):
    url = f"http://localhost:8080/users/{id}"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            return resp.json()
        else:
            return None
    except requests.exceptions.RequestException:
        return None

# ───── Fluxo Principal ─────
if st.session_state['logado'] == False:
    # ⛔ Login antes de tudo
    st.title("🔐 Login HMRubber")

    with st.form("login"):
        email = st.text_input("Email")
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar")

    if entrar:
        if not email or not senha:
            st.warning("⚠️ Preencha email e senha.")
        else:
            with st.spinner("🔄 Validando..."):
                sucesso, resultado = autenticar_usuario(email, senha)
            if sucesso:
                st.session_state['logado'] = True
                st.session_state['usuario'] = email
                st.session_state['user_data'] = carregar_dados_usuario(resultado['id'])
                st.session_state['permissoes'] = st.session_state['user_data'].get('permissoes', [])
                st.rerun()
            else:
                st.error(f"❌ {resultado}")

elif st.session_state['logado'] == True and st.session_state['usuario'] is not None:
    # 🚩 Navegação aparece apenas após login
    from streamlit import Page

    paginas = {}

    if any("Admin" in perm for perm in st.session_state['permissoes']):
        paginas["Painel Administrativo"] = [
            Page("pages/administrativo.py", title="Admin")
        ]

    paginas["Tabela de Vendas"] = [
        Page("pages/planilha.py", title="Vendas")
    ]
    paginas["Relatórios"] = [
        Page("pages/margem_cont.py", title="Margem de Contribuição"),
        Page("pages/Visao_fat.py", title="Visão Faturamento"),
        Page("pages/fat_cliente.py", title="Faturamento por Cliente"),
        Page("pages/fat_uf.py", title="Faturamento por UF"),
        Page("pages/devolucao.py", title="Devoluções"),
        Page("pages/pedidos.py", title="Pedidos"),
    ]
    
    st.sidebar.success(f"Logado como {st.session_state['usuario']}")

    if st.sidebar.button("🔓 Logout"):
        st.session_state.clear()
        st.rerun()
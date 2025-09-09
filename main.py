import streamlit as st
from datetime import datetime
from functions.menu import menu
from functions.connect import test_connection

# Render sidebar / auth
menu()

# ----------------------------------------------------------------------------------
# Layout simples focado no usuário final
# ----------------------------------------------------------------------------------
st.title("🏡 Dashboard HM Rubber")
st.write("Bem-vindo! Aqui você encontra um resumo rápido do que pode acessar.")

username = st.session_state.get("username", "Usuário")
roles = st.session_state.get("role", [])

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("👤 Usuário")
    st.write(f"**Nome:** {username}")
    if roles:
        st.write("**Permissões:** " + ", ".join(roles))
    else:
        st.write("Sem permissões registradas.")

with col2:
    st.subheader("🔌 Conexão")
    if "db_status" not in st.session_state:
        with st.spinner("Verificando conexão..."):
            st.session_state.db_status = test_connection()
            st.session_state.db_last_check = datetime.now()
    if st.session_state.db_status:
        st.success("Conectado ao banco")
    else:
        st.error("Falha na conexão")
    if st.button("Re-testar conexão"):
        with st.spinner("Testando novamente..."):
            st.session_state.db_status = test_connection()
            st.session_state.db_last_check = datetime.now()
        st.rerun()

st.divider()

# Funções auxiliares para validação de permissões
def has_permission(roles, permissions):
    """Verifica se o usuário tem alguma das permissões especificadas"""
    return any(role in roles for role in permissions)

def is_admin(roles):
    """Verifica se o usuário é Admin"""
    return "Admin" in roles

def is_manager(roles):
    """Verifica se o usuário é gerente de qualquer setor"""
    manager_roles = ["Admin", "Gerente Varejo", "Gerente Indústria", "Gerente Exportação"]
    return has_permission(roles, manager_roles)

# Páginas acessíveis (regra simples baseada nas permissões já tratadas no menu)
def accessible_pages(roles):
    base = ["Visão Geral de Vendas", "Clientes"]
    gestor = ["Gerenciador de metas"] if is_manager(roles) else []
    admin = ["Painel Administrativo"] if is_admin(roles) else []
    return base + gestor + admin

pages = accessible_pages(roles)
st.subheader("📑 Páginas que você pode acessar")
if pages:
    for p in pages:
        st.write(f"- {p}")
else:
    st.info("Nenhuma página disponível.")

st.caption("Última verificação: " + st.session_state.get("db_last_check", datetime.now()).strftime("%d/%m/%Y %H:%M:%S"))

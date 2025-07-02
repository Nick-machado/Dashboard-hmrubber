import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from functions.menu import menu_with_redirect
from dotenv import load_dotenv
import os

# --- CONFIGURAÇÃO INICIAL ---
load_dotenv()
url_api = os.getenv("url_api")

st.set_page_config(layout="wide")
menu_with_redirect()

st.title("🎯 Gerenciador de Metas")

# --- DADOS E VARIÁVEIS GLOBAIS ---
meses_nomes = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]
hoje = datetime.now()
ano_atual = hoje.year
anos_disponiveis = list(range(ano_atual - 5, ano_atual + 2))

# --- CONTROLE DE ACESSO E SELEÇÃO DE SETOR (LÓGICA ATUALIZADA) ---
setor_final_para_api = None # Esta variável guardará o valor final a ser enviado para a API

# Simulação do st.session_state para teste, caso não esteja logado
if 'role' not in st.session_state:
    st.session_state['role'] = 'Gerente Varejo' # Mude para 'Admin' ou 'Gerente Indústria' para testar

user_role = st.session_state.get("role", "")

if "Admin" in user_role:
    # Admin pode escolher entre os setores base
    setor_base = st.selectbox("Selecione o setor", ["Indústria", "Varejo"])
    if setor_base == "Varejo":
        # Se Admin escolher Varejo, também mostramos o sub-seletor
        st.markdown("---")
        setor_final_para_api = st.radio(
            "Selecione o tipo de operação Varejo:",
            ["Varejo", "Exportação Varejo"],
            horizontal=True,
            key="sub_setor_admin"
        )
    else:
        setor_final_para_api = setor_base # Se for Indústria, usa o valor diretamente

elif "Gerente Indústria" in user_role:
    setor_final_para_api = "Indústria"
    st.markdown("#### Setor: Indústria")

elif "Gerente Varejo" in user_role:
    st.markdown("#### Setor: Varejo")
    # Mostra o seletor de sub-categoria apenas para o gerente de Varejo
    setor_final_para_api = st.radio(
        "Selecione o tipo de operação:",
        ["Varejo", "Exportação Varejo"],
        horizontal=True,
        key="sub_setor_varejo"
    )
else:
    st.error("Acesso negado. Você não tem permissão para visualizar esta página.")
    st.stop()

st.markdown("---") # Linha divisória para separar os controles do conteúdo

# --- CRIAÇÃO DAS ABAS ---
tab1, tab2 = st.tabs(["Gerenciar Meta Mensal", "Visualizar Metas do Ano"])

# --- ABA 1: GERENCIAR META MENSAL ---
with tab1:
    st.header(f"Definir Meta Mensal para: **{setor_final_para_api}**")

    col1, col2 = st.columns(2)
    with col1:
        ano_filtro = st.selectbox("Ano", options=anos_disponiveis, index=anos_disponiveis.index(ano_atual), key="ano_mensal")
    with col2:
        mes_filtro = st.selectbox("Mês", options=range(1, 13), format_func=lambda m: meses_nomes[m-1], index=hoje.month - 1, key="mes_mensal")

    # Usa a variável `setor_final_para_api` na requisição
    params_busca = {"mes": mes_filtro, "ano": ano_filtro, "setor": setor_final_para_api}
    meta_atual = 0.0
    if url_api:
        try:
            response = requests.get(f"{url_api}/metas/buscar", params=params_busca)
            if response.status_code == 200:
                meta_atual = float(response.json().get("valor", 0.0))
        except requests.exceptions.RequestException as e:
            st.warning(f"API indisponível para buscar meta. Erro: {e}")

    st.markdown(f"##### Meta para {meses_nomes[mes_filtro-1]} de {ano_filtro}")
    meta_nova = st.number_input("Valor da meta (R$)", min_value=0.0, value=meta_atual, step=100.0, format="%.2f", key="meta_input")

    if st.button("💾 Salvar Meta Mensal"):
        if not url_api:
            st.error("A URL da API não está configurada.")
        else:
            # Usa a variável `setor_final_para_api` no payload
            payload = {"mes": mes_filtro, "ano": ano_filtro, "setor": setor_final_para_api, "valor": meta_nova}
            try:
                with st.spinner("🔄 Salvando meta..."):
                    resp = requests.post(f"{url_api}/metas/alterar", json=payload)
                    if 200 <= resp.status_code < 300:
                        st.success(resp.json().get("message", "✅ Meta salva com sucesso!"))
                        st.rerun()
                    else:
                        error_message = resp.json().get("message", f"Status {resp.status_code}")
                        st.error(f"Falha ao salvar meta: {error_message}")
            except requests.exceptions.RequestException as e:
                st.error(f"Erro de conexão com a API: {e}")

# --- ABA 2: VISUALIZAR METAS DO ANO ---
with tab2:
    st.header(f"Visualização Anual de Metas para: **{setor_final_para_api}**")

    ano_visualizacao = st.selectbox("Selecione o Ano para Visualizar", options=anos_disponiveis, index=anos_disponiveis.index(ano_atual), key="ano_anual")

    if st.button("📊 Buscar Metas do Ano"):
        if not url_api:
            st.error("A URL da API não está configurada.")
        else:
            # Usa a variável `setor_final_para_api` na requisição
            params_anual = {"ano": ano_visualizacao, "setor": setor_final_para_api}
            try:
                with st.spinner(f"Buscando metas de {ano_visualizacao} para {setor_final_para_api}..."):
                    response = requests.get(f"{url_api}/metas/anual", params=params_anual)
                    if response.status_code == 200:
                        dados_api = response.json()
                        metas_dict = dados_api.get("metas", {})
                        if not metas_dict:
                            st.warning(f"Nenhum dado de meta retornado pela API para {ano_visualizacao}.")
                        else:
                            dados_para_df = sorted(metas_dict.items(), key=lambda item: int(item[0]))
                            df = pd.DataFrame(dados_para_df, columns=["Mês (Num)", "Valor da Meta"])
                            df["Mês"] = df["Mês (Num)"].apply(lambda num: meses_nomes[int(num) - 1])
                            df["Valor da Meta (R$)"] = df["Valor da Meta"].apply(lambda x: f"R$ {float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                            df_display = df[["Mês", "Valor da Meta (R$)"]]
                            st.dataframe(df_display, use_container_width=True, hide_index=True)
                    elif response.status_code == 404:
                        st.info(f"Nenhuma meta encontrada para o ano de {ano_visualizacao} e setor {setor_final_para_api}.")
                    else:
                        error_message = response.json().get("detail", f"Erro com status {response.status_code}")
                        st.error(f"Falha ao buscar metas: {error_message}")
            except requests.exceptions.RequestException as e:
                st.error(f"Erro de conexão com a API: {e}")
            except Exception as e:
                st.error(f"Ocorreu um erro inesperado: {e}")
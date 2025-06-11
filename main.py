import streamlit as st

st.title("Dashboard da HMRubber")

pages = {
    "Tabela de Vendas": [
        st.Page("pages/planilha.py", title="Tabela de Vendas")
    ],
    "Relatórios": [
        st.Page("pages/Visao_fat.py", title="Visão geral do faturamento")
    ]
}

pg = st.navigation(pages)
pg.run()
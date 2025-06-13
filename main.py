import streamlit as st

st.title("Dashboard da HMRubber")

pages = {
    "Tabela de Vendas": [
        st.Page("pages/planilha.py", title="Tabela de Vendas")
    ],
    "Relatórios": [
        st.Page("pages/margem_cont.py", title="Margem de Contribuição"),
        st.Page("pages/Visao_fat.py", title="Visão geral do faturamento"),
        st.Page("pages/fat_cliente.py", title="Faturamento por Cliente"),
        st.Page("pages/fat_uf.py", title="Faturamento por UF"),
        st.Page("pages/devolucao.py", title="Devoluções"),
        st.Page("pages/pedidos.py", title="Pedidos"),
    ]
}

pg = st.navigation(pages)
pg.run()
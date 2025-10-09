from functions.menu import menu_with_redirect
import streamlit as st
import pandas as pd
from datetime import datetime
from functions.query_margem import run_query
import os

st.set_page_config(layout="wide", page_title="Relatório regional")
menu_with_redirect()

# ========================
# Relatório anual - DataFrame original da query
# ========================
st.title("💰 Margem por Cliente - Relatório Anual")

ano_atual = datetime.now().year
anos_disponiveis = list(range(ano_atual - 5, ano_atual + 1))
ano = st.selectbox("Ano", options=anos_disponiveis, index=anos_disponiveis.index(ano_atual))
data_in = f"{ano}-01-01"
data_fin = f"{ano}-12-31"

@st.cache_data(show_spinner=False)
def cached_run_query(data_in: str, data_fin: str):
    # Wrapper around the original run_query so Streamlit can cache results
    return run_query(data_in, data_fin)

with st.spinner("Consultando dados originais da query..."):
    df_query = cached_run_query(data_in, data_fin)

# Garantias de colunas esperadas
for col in ['Mês', 'Cliente', 'Total NF', '$ Margem', 'Cód. Prod', 'Quant.', 'Vlr.Líquido']:
    if col not in df_query.columns:
        # Cria a coluna ausente com valor neutro
        df_query[col] = 0 if col in ['Total NF', '$ Margem', 'Quant.', 'Vlr.Líquido'] else ""

# ========================
# Helpers
# ========================
meses_nome = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
    7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}

def formatar_moeda_brasileira(valor: float) -> str:
    try:
        return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except Exception:
        return "—"

df_query['Mês'] = pd.to_numeric(df_query['Mês'], errors='coerce').fillna(0).astype(int)
df_query['Nome do Mês'] = df_query['Mês'].map(meses_nome)

# ========================
# CMV Padrão (XLSX)
# ========================
@st.cache_data(show_spinner=False)
def calcular_cmv_padrao_xlsx(df_base: pd.DataFrame, xlsx_path: str) -> pd.DataFrame:
    if not os.path.exists(xlsx_path):
        st.error(f"Arquivo de custo não encontrado: {xlsx_path}")
        return df_base.assign(CMV_PADRÃO_XLSX=0.0, Nova_Margem=df_base.get('Vlr.Líquido', 0.0))

    df_custo = pd.read_excel(xlsx_path)

    # Ajustes de nomes/colunas esperadas
    if 'Soma de PREÇO' not in df_custo.columns:
        st.error("Coluna 'Soma de PREÇO' não encontrada no XLSX de custo.")
        return df_base.assign(CMV_PADRÃO_XLSX=0.0, Nova_Margem=df_base.get('Vlr.Líquido', 0.0))

    # Renomeia código de produto para casar com o df_query
    rename_map = {}
    if 'CÓD' in df_custo.columns:
        rename_map['CÓD'] = 'Cód. Prod'
    df_custo = df_custo.rename(columns=rename_map)

    if 'Cód. Prod' not in df_custo.columns:
        st.error("Coluna 'Cód. Prod' não encontrada no XLSX de custo.")
        return df_base.assign(CMV_PADRÃO_XLSX=0.0, Nova_Margem=df_base.get('Vlr.Líquido', 0.0))

    # Calcula CMV padrão unitário a partir do preço
    df_custo['CMV Padrão'] = df_custo['Soma de PREÇO'] * 0.88

    # Prepara chaves
    df_base = df_base.copy()
    df_base['Cód. Prod'] = df_base['Cód. Prod'].astype(str).str.strip()
    df_custo['Cód. Prod'] = df_custo['Cód. Prod'].astype(str).str.strip()

    # Merge
    df_merged = pd.merge(
        df_base,
        df_custo[['Cód. Prod', 'CMV Padrão']],
        on='Cód. Prod',
        how='left'
    )

    # Novo CMV calculado (quantidade * cmv_unit)
    df_merged['Quant.'] = pd.to_numeric(df_merged['Quant.'], errors='coerce').fillna(0.0)
    df_merged['CMV Padrão'] = pd.to_numeric(df_merged['CMV Padrão'], errors='coerce').fillna(0.0)
    df_merged['CMV_PADRÃO_XLSX'] = (df_merged['Quant.'] * df_merged['CMV Padrão'].round(2)).round(2)

    # Nova Margem = Vlr.Líquido - CMV_PADRÃO_XLSX
    df_merged['Vlr.Líquido'] = pd.to_numeric(df_merged['Vlr.Líquido'], errors='coerce').fillna(0.0)
    df_merged['Nova Margem'] = (df_merged['Vlr.Líquido'] - df_merged['CMV_PADRÃO_XLSX']).round(2)

    return df_merged

xlsx_path = 'Custo padrão.xlsx'
with st.spinner("Consultando dados e calculando CMV Padrão pelo XLSX..."):
    df_cmv_padrao = calcular_cmv_padrao_xlsx(df_query.copy(), xlsx_path)

# Garante Nome do Mês no df_cmv_padrao
if 'Nome do Mês' not in df_cmv_padrao.columns:
    df_cmv_padrao['Mês'] = pd.to_numeric(df_cmv_padrao['Mês'], errors='coerce').fillna(0).astype(int)
    df_cmv_padrao['Nome do Mês'] = df_cmv_padrao['Mês'].map(meses_nome)

# ========================
# Agregações Mensais
# ========================
df_mensal_original = (
    df_query
    .groupby(['Mês', 'Nome do Mês', 'Cliente'], as_index=False)
    .agg({
        'Total NF': 'sum',
        '$ Margem': 'sum'
    })
    .rename(columns={'Total NF': 'Total NF Mensal', '$ Margem': 'Margem Mensal'})
    .sort_values(['Mês', 'Cliente'])
)

df_mensal_nova = (
    df_cmv_padrao
    .groupby(['Mês', 'Nome do Mês', 'Cliente'], as_index=False)
    .agg({
        'Total NF': 'sum',
        'Nova Margem': 'sum'
    })
    .rename(columns={'Total NF': 'Total NF Mensal', 'Nova Margem': 'Margem Mensal'})
    .sort_values(['Mês', 'Cliente'])
)

# ========================
# Seleção de Cliente
# ========================
clientes = sorted(set(df_mensal_original['Cliente'].astype(str)).union(set(df_mensal_nova['Cliente'].astype(str))))
cliente_selecionado = st.selectbox("Cliente", options=clientes) if clientes else None

# Formatação monetária (FAÇA SEMPRE DEPOIS dos cálculos)
def aplicar_formatacao(df: pd.DataFrame) -> pd.DataFrame:
    df_fmt = df.copy()
    if 'Total NF Mensal' in df_fmt.columns:
        df_fmt['Total NF Mensal'] = df_fmt['Total NF Mensal'].apply(formatar_moeda_brasileira)
    if 'Margem Mensal' in df_fmt.columns:
        df_fmt['Margem Mensal'] = df_fmt['Margem Mensal'].apply(formatar_moeda_brasileira)
    if '% Margem de contribuição' in df_fmt.columns:
        df_fmt['% Margem de contribuição'] = df_fmt['% Margem de contribuição'].apply(lambda x: f"{x:.2f}%")
    return df_fmt

# ========================
# Exibição por cliente (se houver)
# ========================
if cliente_selecionado:
    df_mensal_original_filtrado = df_mensal_original[df_mensal_original['Cliente'].astype(str) == str(cliente_selecionado)].copy()
    df_mensal_nova_filtrado = df_mensal_nova[df_mensal_nova['Cliente'].astype(str) == str(cliente_selecionado)].copy()
    
    # Adiciona % Margem de contribuição
    df_mensal_original_filtrado['% Margem de contribuição'] = (
        (df_mensal_original_filtrado['Margem Mensal'] / df_mensal_original_filtrado['Total NF Mensal'] * 100)
        .fillna(0).round(2)
    )
    df_mensal_nova_filtrado['% Margem de contribuição'] = (
        (df_mensal_nova_filtrado['Margem Mensal'] / df_mensal_nova_filtrado['Total NF Mensal'] * 100)
        .fillna(0).round(2)
    )

    st.markdown(f"#### Margem Custo Sistema")
    st.dataframe(
        aplicar_formatacao(df_mensal_original_filtrado[['Nome do Mês', 'Total NF Mensal', 'Margem Mensal', '% Margem de contribuição']]),
        hide_index=True, use_container_width=True
    )
    
    # Métricas Margem Custo Sistema
    total_nf_original = df_mensal_original_filtrado['Total NF Mensal'].sum()
    total_margem_original = df_mensal_original_filtrado['Margem Mensal'].sum()
    percentual_original = (total_margem_original / total_nf_original * 100) if total_nf_original != 0 else 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total NF", formatar_moeda_brasileira(total_nf_original))
    with col2:
        st.metric("Total Margem", formatar_moeda_brasileira(total_margem_original))
    with col3:
        st.metric("% Margem Total", f"{percentual_original:.2f}%")

    st.markdown(f"#### Margem Custo Padrão")
    st.dataframe(
        aplicar_formatacao(df_mensal_nova_filtrado[['Nome do Mês', 'Total NF Mensal', 'Margem Mensal', '% Margem de contribuição']]),
        hide_index=True, use_container_width=True
    )
    
    # Métricas Margem Custo Padrão
    total_nf_nova = df_mensal_nova_filtrado['Total NF Mensal'].sum()
    total_margem_nova = df_mensal_nova_filtrado['Margem Mensal'].sum()
    percentual_nova = (total_margem_nova / total_nf_nova * 100) if total_nf_nova != 0 else 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total NF", formatar_moeda_brasileira(total_nf_nova))
    with col2:
        st.metric("Total Margem", formatar_moeda_brasileira(total_margem_nova))
    with col3:
        st.metric("% Margem Total", f"{percentual_nova:.2f}%")

# ========================
# Exibição geral (todos os clientes) - OCULTO
# ========================
# st.markdown("#### Margem Mensal Original (Query) — Geral")
# st.dataframe(
#     aplicar_formatacao(df_mensal_original[['Nome do Mês', 'Cliente', 'Total NF Mensal', 'Margem Mensal']]),
#     hide_index=True, use_container_width=True
# )

# st.markdown("#### Margem Mensal com CMV Padrão (XLSX) — Geral")
# st.dataframe(
#     aplicar_formatacao(df_mensal_nova[['Nome do Mês', 'Cliente', 'Total NF Mensal', 'Margem Mensal']]),
#     hide_index=True, use_container_width=True
# )

# ========================
# Rodapé Padronizado
# ========================
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p><strong>Dashboard de Inteligência Comercial</strong></p>
    <p>Período: 01/01/{ano} a 31/12/{ano}</p>
    <p>Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
</div>
""", unsafe_allow_html=True)
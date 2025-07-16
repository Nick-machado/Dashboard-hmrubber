import streamlit as st
from datetime import datetime, date
from calendar import monthrange
import pandas as pd
import plotly.graph_objects as go
from functions.menu import menu_with_redirect
from functions.query_clientes import run_query

st.set_page_config(layout="wide")
menu_with_redirect()

# ========== ROLE/SETOR ==========
user_role = st.session_state.get("role", [])
role = None

if "Admin" in user_role:
    setores = ["Indústria", "Varejo", "Admin (todas equipes)"]
    setor_base = st.selectbox("Selecione o setor", setores)
    if setor_base == "Varejo":
        st.markdown("---")
        role = st.radio(
            "Selecione o tipo de operação Varejo:",
            ["Varejo", "Exportação Varejo"],
            horizontal=True,
            key="sub_setor_admin"
        )
    elif setor_base == "Indústria":
        role = setor_base
    else:
        role = "Admin (todas equipes)"

elif "Gerente Indústria" in user_role or "Indústria" in user_role:
    role = "Indústria"
    st.markdown("#### Setor: Indústria")

elif "Gerente Varejo" in user_role or "Varejo" in user_role:
    st.markdown("#### Setor: Varejo")
    role = st.radio(
        "Selecione o tipo de operação:",
        ["Varejo", "Exportação Varejo"],
        horizontal=True,
        key="sub_setor_varejo"
    )
else:
    st.error("Acesso negado. Você não tem permissão para visualizar esta página.")
    st.stop()

# ========== Tempo ==========
hoje = datetime.now()
ano_atual = hoje.year
mes_atual = hoje.month
anos_disponiveis = list(range(ano_atual - 5, ano_atual + 1))
meses = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

# ========== Filtro setor (equipe) ==========
if role == "Indústria":
    filtro_equipe = "INDUSTRIAL"
elif role == "Varejo":
    filtro_equipe = "VAREJO"
elif role == "Exportação Varejo":
    filtro_equipe = "EXPORTAÇÃO VAREJO"
else:  # Admin (todas equipes)
    filtro_equipe = None

def aplicar_filtro_equipe(df, filtro_equipe):
    if filtro_equipe and 'NOME_EQUIPE' in df.columns:
        return df[df['NOME_EQUIPE'] == filtro_equipe]
    else:
        return df.copy()

# ========== Cache dados ==========
@st.cache_data(ttl=600)
def buscar_clientes_ano(ano):
    df = run_query()  # agora sem argumentos
    df['ULTIMA_COMPRA'] = pd.to_datetime(df['ULTIMA_COMPRA'], errors='coerce')
    df['DATA_CADASTRO'] = pd.to_datetime(df['DATA_CADASTRO'], errors='coerce')
    # Filtra apenas clientes com compra no ano anterior ou no ano selecionado
    df = df[df['ULTIMA_COMPRA'].dt.year.isin([ano - 1, ano])]
    df['Mês'] = df['ULTIMA_COMPRA'].dt.month
    df['Ano'] = df['ULTIMA_COMPRA'].dt.year
    return df

aba1, aba2 = st.tabs(["Novos x Recorrentes", "Churn de Clientes"])

with aba1:
    st.markdown("### Novos x Recorrentes")
    col1, col2 = st.columns([2, 1])
    with col2:
        st.markdown("#### Ano")
        ano = st.selectbox(
            "",
            options=anos_disponiveis,
            index=anos_disponiveis.index(ano_atual),
            key="select_ano_novos"
        )
    if ano == ano_atual:
        meses_disponiveis = list(range(1, mes_atual + 1))
    else:
        meses_disponiveis = list(range(1, 13))
    with col1:
        st.markdown("#### Mês")
        mes = st.selectbox(
            "",
            options=meses_disponiveis,
            format_func=lambda m: meses[m - 1],
            index=meses_disponiveis.index(mes_atual) if ano == ano_atual else 0,
            key="select_mes_novos"
        )
    with st.spinner("🔄 Carregando dados..."):
        df_clientes = buscar_clientes_ano(ano)
    df_clientes = aplicar_filtro_equipe(df_clientes, filtro_equipe)

    # Se admin e quiser filtrar por equipe específica:
    if "Admin" in user_role and filtro_equipe is None and 'NOME_EQUIPE' in df_clientes.columns:
        equipes_unicas = sorted(df_clientes['NOME_EQUIPE'].dropna().unique())
        equipe_admin = st.selectbox(
            "Filtrar por equipe (opcional):",
            options=["Todas"] + equipes_unicas,
            index=0,
            key="select_equipe_admin_novos"
        )
        if equipe_admin != "Todas":
            df_clientes = df_clientes[df_clientes['NOME_EQUIPE'] == equipe_admin]

    # ============================= NOVA LÓGICA DO GRÁFICO =============================
    # 1. Filtrar apenas clientes que fizeram compra no mês/ano selecionado
    mask_mes = (
        (df_clientes['ULTIMA_COMPRA'].dt.year == ano) &
        (df_clientes['ULTIMA_COMPRA'].dt.month == mes)
    )
    df_mes = df_clientes[mask_mes].copy()

    # 2. Classificar: Novo se DATA_CADASTRO é do mesmo mês/ano da ULTIMA_COMPRA
    df_mes['TIPO_CLIENTE'] = df_mes.apply(
        lambda row: "Novo" if (row['DATA_CADASTRO'].year == row['ULTIMA_COMPRA'].year
                               and row['DATA_CADASTRO'].month == row['ULTIMA_COMPRA'].month)
        else "Recorrente",
        axis=1
    )

    qtd_novos = (df_mes['TIPO_CLIENTE'] == "Novo").sum()
    qtd_recorrentes = (df_mes['TIPO_CLIENTE'] == "Recorrente").sum()

    cores_novos_recorrentes = ['#FFA726', '#1976D2']
    pull_novos_recorrentes = [0.10 if qtd_novos < qtd_recorrentes else 0, 0.10 if qtd_recorrentes <= qtd_novos else 0]
    fig1 = go.Figure(data=[
        go.Pie(
            labels=["Novos", "Recorrentes"],
            values=[qtd_novos, qtd_recorrentes],
            hole=0.5,
            marker=dict(colors=cores_novos_recorrentes, line=dict(color='#fff', width=2)),
            textinfo='label+percent+value',
            insidetextorientation='auto',
            pull=pull_novos_recorrentes,
            hovertemplate='<b>%{label}</b><br>Qtd: %{value}<br>%{percent}',
            showlegend=True,
            textposition='outside',
            textfont=dict(size=13, color='white'),
            automargin=True
        )
    ])
    fig1.update_layout(
        title=f"Clientes Novos x Recorrentes ({meses[mes-1]}/{ano})",
        legend=dict(orientation="h", y=-0.16, x=0.2, font=dict(size=13)),
        margin=dict(l=80, r=80, t=110, b=80),
        font=dict(size=14),
        width=480,
        height=440
    )

    st.plotly_chart(fig1, use_container_width=True)
    st.metric("Clientes Novos", qtd_novos)
    st.metric("Clientes Recorrentes", qtd_recorrentes)

    with st.expander("Visualizar todos os clientes do mês selecionado"):
        st.dataframe(
            df_mes[['ID_CLIENTE', 'RAZAO_SOCIAL', 'NOME_EQUIPE', 'ENDERECO',
                    'ULTIMA_COMPRA', 'DATA_CADASTRO', 'TIPO_CLIENTE',
                    'ULTIMA_NOTA', 'DATA_ULTIMA_NOTA']].drop_duplicates('ID_CLIENTE')
        )

with aba2:
    st.markdown("### Churn de Clientes")
    colc1, colc2 = st.columns([2, 1])
    with colc2:
        st.markdown("#### Ano")
        ano_churn = st.selectbox(
            "",
            options=anos_disponiveis,
            index=anos_disponiveis.index(ano_atual),
            key="select_ano_churn"
        )
    with colc1:
        st.markdown("#### Semestre")
        semestre = st.selectbox(
            "",
            options=[1, 2],
            format_func=lambda x: "1º Semestre (Jan-Jun)" if x == 1 else "2º Semestre (Jul-Dez)",
            key="select_semestre_churn"
        )
    with st.spinner("🔄 Carregando dados..."):
        df_clientes_churn = buscar_clientes_ano(ano_churn)
    df_clientes_churn = aplicar_filtro_equipe(df_clientes_churn, filtro_equipe)

    # Se admin e quiser filtrar por equipe específica:
    if "Admin" in user_role and filtro_equipe is None and 'NOME_EQUIPE' in df_clientes_churn.columns:
        equipes_unicas_churn = sorted(df_clientes_churn['NOME_EQUIPE'].dropna().unique())
        equipe_admin_churn = st.selectbox(
            "Filtrar por equipe (opcional):",
            options=["Todas"] + equipes_unicas_churn,
            index=0,
            key="select_equipe_admin_churn"
        )
        if equipe_admin_churn != "Todas":
            df_clientes_churn = df_clientes_churn[df_clientes_churn['NOME_EQUIPE'] == equipe_admin_churn]

    if semestre == 1:
        mes_ini, mes_fim = 1, 6
    else:
        mes_ini, mes_fim = 7, 12
    inicio_semestre = datetime(ano_churn, mes_ini, 1)
    fim_semestre = datetime(ano_churn, mes_fim, monthrange(ano_churn, mes_fim)[1])
    clientes_base = set(
        df_clientes_churn[df_clientes_churn['ULTIMA_COMPRA'] < inicio_semestre]['ID_CLIENTE'].unique()
    )
    clientes_ativos = set(
        df_clientes_churn[
            (df_clientes_churn['ULTIMA_COMPRA'] >= inicio_semestre) &
            (df_clientes_churn['ULTIMA_COMPRA'] <= fim_semestre)
        ]['ID_CLIENTE'].unique()
    )
    clientes_inativos = clientes_base - clientes_ativos
    qtd_ativos = len(clientes_ativos)
    qtd_inativos = len(clientes_inativos)

    cores_churn_semestre = ['#616161', '#43A047']
    pull_churn_semestre = [0.08, 0.08]
    fig_churn_semestre = go.Figure(data=[
        go.Pie(
            labels=["Inativos", "Ativos"],
            values=[qtd_inativos, qtd_ativos],
            hole=0.5,
            marker=dict(colors=cores_churn_semestre, line=dict(color='#fff', width=2)),
            textinfo='label+percent+value',
            insidetextorientation='auto',
            pull=pull_churn_semestre,
            hovertemplate='<b>%{label}</b><br>Qtd: %{value}<br>%{percent}',
            showlegend=True,
            textposition='outside',
            textfont=dict(size=13, color='white'),
            automargin=True
        )
    ])
    periodo_str = f"1º Semestre" if semestre == 1 else "2º Semestre"
    fig_churn_semestre.update_layout(
        title=f"Clientes Ativos/Inativos ({periodo_str}/{ano_churn})",
        legend=dict(orientation="h", y=-0.16, x=0.25, font=dict(size=13)),
        margin=dict(l=80, r=80, t=110, b=80),
        font=dict(size=14),
        width=480,
        height=440
    )
    st.plotly_chart(fig_churn_semestre, use_container_width=True)
    st.metric("Clientes Inativos (no semestre)", qtd_inativos)
    st.metric("Clientes Ativos (no semestre)", qtd_ativos)

    with st.expander("Visualizar detalhes dos clientes inativos"):
        if qtd_inativos > 0:
            df_inativos = df_clientes_churn[df_clientes_churn['ID_CLIENTE'].isin(clientes_inativos)]
            st.dataframe(
                df_inativos[['ID_CLIENTE', 'RAZAO_SOCIAL', 'NOME_EQUIPE', 'ENDERECO',
                             'ULTIMA_COMPRA', 'DATA_CADASTRO', 'ULTIMA_NOTA', 'DATA_ULTIMA_NOTA']].drop_duplicates('ID_CLIENTE')
            )
        else:
            st.info("Nenhum cliente inativo para este período.")
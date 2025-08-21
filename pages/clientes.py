import streamlit as st
from functions.menu import menu_with_redirect
st.set_page_config(layout="wide")
menu_with_redirect()

"""
Página de Performance de Clientes
Insights implementados (somente usando dados já disponíveis = 'OK'):
1. Top 10 Clientes (R$) – faturamento bruto (sem segmentar direto vs revenda por falta de classificação)
2. Novos x Recorrentes (mês selecionado)
3. Taxa de Recompra (até o mês acumulado no ano)
4. Frequência média de compra e recência média
5. Clientes novos (acumulado YTD) x recorrentes
6. Churn 3 e 6 meses (baseado na data de corte = fim do mês selecionado)
7. Lista detalhada de clientes churned (3m / 6m) e Top 10

Se no futuro houver campo para classificar cliente Direto/Revenda, podemos expandir.
"""

from datetime import datetime
from calendar import monthrange
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Queries de clientes (cadastro / última compra) e vendas (para faturamento/top)
from functions.query_clientes import run_query as run_query_clientes
from functions.query import run_query as run_query_vendas

# =============================
# Controle de Acesso (ROLE/SETOR)
# =============================
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

# =============================
# Definições de tempo
# =============================
hoje = datetime.now()
ano_atual = hoje.year
mes_atual = hoje.month
anos_disponiveis = list(range(ano_atual - 5, ano_atual + 1))
meses_label = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

# =============================
# Mapeamento de equipe (setor)
# =============================
if role == "Indústria":
    filtro_equipe = "INDUSTRIAL"
elif role == "Varejo":
    filtro_equipe = "VAREJO"
elif role == "Exportação Varejo":
    filtro_equipe = "EXPORTAÇÃO VAREJO"
else:  # Admin
    filtro_equipe = None

def aplicar_filtro_equipe(df: pd.DataFrame) -> pd.DataFrame:
    if filtro_equipe and ('NOME_EQUIPE' in df.columns or 'Equipe' in df.columns):
        col_eq = 'NOME_EQUIPE' if 'NOME_EQUIPE' in df.columns else 'Equipe'
        return df[df[col_eq] == filtro_equipe]
    return df.copy()

# =============================
# Cache / Carregamento de Dados
# =============================
@st.cache_data(ttl=900)
def load_clientes_raw():
    df = run_query_clientes()
    # Normalizações de datas
    for col in ["ULTIMA_COMPRA", "DATA_CADASTRO", "DATA_ULTIMA_NOTA"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    return df

@st.cache_data(ttl=900)
def load_vendas_raw(ano: int, mes: int):
    """Carrega vendas desde 01/01 do ano anterior até o fim do mês selecionado do ano atual.
    Necessário para churn (histórico) e YTD.
    """
    from datetime import date as _date
    # Início: 1º jan do ano anterior
    # Usar formato ISO para evitar ambiguidade de locale no Firebird
    data_ini = _date(ano - 1, 1, 1).strftime('%Y-%m-%d')
    # Fim: último dia do mês selecionado (ano atual ou passado se navegando anos históricos)
    ultimo_dia = monthrange(ano, mes)[1]
    data_fim = _date(ano, mes, ultimo_dia).strftime('%Y-%m-%d')
    dv = run_query_vendas(data_ini, data_fim)
    if 'Data' in dv.columns:
        dv['Data'] = pd.to_datetime(dv['Data'], errors='coerce')
    return dv

@st.cache_data(ttl=900)
def get_dados_periodo(ano: int, mes: int):
    """Retorna dataframes filtrados: clientes (última compra ano-1 e ano), vendas YTD."""
    df_cli = load_clientes_raw()
    df_cli = df_cli[df_cli['ULTIMA_COMPRA'].dt.year.isin([ano - 1, ano])]
    df_cli['Ano'] = df_cli['ULTIMA_COMPRA'].dt.year
    df_cli['Mes'] = df_cli['ULTIMA_COMPRA'].dt.month

    dv = load_vendas_raw(ano, mes)
    # Vendas dos anos (para churn preciso de histórico anterior)
    dv = dv[dv['Data'].dt.year.isin([ano - 1, ano])]
    dv['Ano'] = dv['Data'].dt.year
    dv['Mes'] = dv['Data'].dt.month

    # Cutoffs
    ultimo_dia_mes = monthrange(ano, mes)[1]
    fim_mes = datetime(ano, mes, ultimo_dia_mes)
    inicio_ano = datetime(ano, 1, 1)

    # Acumulado YTD até mês
    dv_ytd = dv[(dv['Data'] >= inicio_ano) & (dv['Data'] <= fim_mes)]

    return df_cli, dv, dv_ytd, fim_mes, inicio_ano

# =============================
# Funções de Métricas
# =============================
def classificar_novos_recorrentes(df_mes: pd.DataFrame) -> pd.DataFrame:
    """Novo se DATA_CADASTRO está no mesmo mês/ano da ULTIMA_COMPRA no mês filtrado."""
    if df_mes.empty:
        return df_mes.assign(TIPO_CLIENTE=[])
    df_mes = df_mes.copy()
    df_mes['TIPO_CLIENTE'] = df_mes.apply(
        lambda r: 'Novo' if (
            isinstance(r['DATA_CADASTRO'], pd.Timestamp) and isinstance(r['ULTIMA_COMPRA'], pd.Timestamp)
            and r['DATA_CADASTRO'].year == r['ULTIMA_COMPRA'].year
            and r['DATA_CADASTRO'].month == r['ULTIMA_COMPRA'].month
        ) else 'Recorrente', axis=1
    )
    return df_mes

def calc_recompra(vendas_ytd: pd.DataFrame):
    """Taxa de recompra: % clientes com 2+ compras (notas distintas) no YTD."""
    vendas = vendas_ytd[vendas_ytd['Flag tipo'] == 'V'] if 'Flag tipo' in vendas_ytd.columns else vendas_ytd
    if vendas.empty:
        return 0.0, 0, 0
    # Cliente pode estar identificado por 'Cliente' ou outro campo; fallback para 'Cliente'
    col_cliente = 'Cliente' if 'Cliente' in vendas.columns else vendas.columns[0]
    # Considerar Nota se existir
    col_nota = 'Nota' if 'Nota' in vendas.columns else None
    if col_nota:
        compras_cliente = vendas.groupby(col_cliente)[col_nota].nunique()
    else:
        compras_cliente = vendas.groupby(col_cliente)['Data'].nunique()
    total_clientes = compras_cliente.shape[0]
    clientes_recompra = (compras_cliente >= 2).sum()
    taxa = round(clientes_recompra / total_clientes * 100, 2) if total_clientes else 0.0
    return taxa, clientes_recompra, total_clientes

def recencia_frequencia(vendas_ytd: pd.DataFrame, data_corte: datetime):
    vendas = vendas_ytd[vendas_ytd['Flag tipo'] == 'V'] if 'Flag tipo' in vendas_ytd.columns else vendas_ytd
    if vendas.empty:
        return 0, 0
    col_cliente = 'Cliente' if 'Cliente' in vendas.columns else vendas.columns[0]
    col_nota = 'Nota' if 'Nota' in vendas.columns else None
    grp = vendas.groupby(col_cliente)
    ultima = grp['Data'].max()
    if col_nota:
        freq = grp[col_nota].nunique()
    else:
        freq = grp['Data'].nunique()
    recencia_dias = (data_corte - ultima).dt.days.mean()
    freq_media = freq.mean()
    return round(recencia_dias, 1), round(freq_media, 2)

def churn_clientes(vendas_full: pd.DataFrame, data_corte: datetime, meses: int):
    from dateutil.relativedelta import relativedelta
    limite = data_corte - relativedelta(months=meses)
    vendas = vendas_full[vendas_full['Flag tipo'] == 'V'] if 'Flag tipo' in vendas_full.columns else vendas_full
    if vendas.empty:
        return pd.DataFrame(columns=['Cliente', 'UltimaCompra', 'DiasSemCompra'])
    col_cliente = 'Cliente' if 'Cliente' in vendas.columns else vendas.columns[0]
    last = vendas.groupby(col_cliente)['Data'].max().reset_index(name='UltimaCompra')
    churned = last[last['UltimaCompra'] < limite].copy()
    churned['DiasSemCompra'] = (data_corte - churned['UltimaCompra']).dt.days
    return churned.sort_values('DiasSemCompra', ascending=False)

def top_clientes(vendas_ytd: pd.DataFrame, n=10):
    vendas = vendas_ytd[vendas_ytd['Flag tipo'] == 'V'] if 'Flag tipo' in vendas_ytd.columns else vendas_ytd
    if vendas.empty or 'Total NF' not in vendas.columns:
        return pd.DataFrame(columns=['Cliente', 'Faturamento'])
    col_cliente = 'Cliente'
    top = vendas.groupby(col_cliente)['Total NF'].sum().sort_values(ascending=False).head(n).reset_index()
    top.columns = ['Cliente', 'Faturamento']
    return top

# =============================
# Filtros Principais
# =============================
col_ano, col_mes = st.columns([1, 1])
with col_ano:
    ano_sel = st.selectbox("Ano", anos_disponiveis, index=anos_disponiveis.index(ano_atual))
meses_disponiveis = list(range(1, mes_atual + 1)) if ano_sel == ano_atual else list(range(1, 13))
with col_mes:
    mes_sel = st.selectbox("Mês", meses_disponiveis, format_func=lambda m: meses_label[m-1], index=len(meses_disponiveis)-1)

with st.spinner("🔄 Carregando dados..."):
    df_clientes_raw, df_vendas_full, df_vendas_ytd, data_corte, inicio_ano = get_dados_periodo(ano_sel, mes_sel)

# Aplicar filtro de equipe (clientes não têm faturamento, mas mantemos consistência)
df_clientes_raw = aplicar_filtro_equipe(df_clientes_raw)
df_vendas_full = aplicar_filtro_equipe(df_vendas_full)
df_vendas_ytd = aplicar_filtro_equipe(df_vendas_ytd)

# =============================
# Novos x Recorrentes (mês selecionado)
# =============================
mask_mes_cliente = (
    (df_clientes_raw['ULTIMA_COMPRA'].dt.year == ano_sel) &
    (df_clientes_raw['ULTIMA_COMPRA'].dt.month == mes_sel)
)
df_mes = df_clientes_raw[mask_mes_cliente].copy()
df_mes = classificar_novos_recorrentes(df_mes)
qtd_novos = (df_mes['TIPO_CLIENTE'] == 'Novo').sum()
qtd_recorrentes = (df_mes['TIPO_CLIENTE'] == 'Recorrente').sum()

fig_novos = go.Figure(data=[go.Pie(
    labels=['Novos', 'Recorrentes'],
    values=[qtd_novos, qtd_recorrentes],
    hole=0.5,
    marker=dict(colors=['#FFA726', '#1976D2'], line=dict(color='#fff', width=2)),
    textinfo='label+percent+value',
    pull=[0.08, 0.08]
)])
fig_novos.update_layout(title=f"Clientes Novos x Recorrentes ({meses_label[mes_sel-1]}/{ano_sel})", height=380)

# =============================
# Taxa de Recompra / Recência / Frequência
# =============================
taxa_recompra, clientes_recompra, total_clientes_ativos_ytd = calc_recompra(df_vendas_ytd)
recencia_media, freq_media = recencia_frequencia(df_vendas_ytd, data_corte)

# =============================
# Churn 3m / 6m
# =============================
churn_3 = churn_clientes(df_vendas_full, data_corte, 3)
churn_6 = churn_clientes(df_vendas_full, data_corte, 6)

# =============================
# Top 10 Clientes (YTD)
# =============================
df_top10 = top_clientes(df_vendas_ytd, 10)

# =============================
# KPIs Header
# =============================
st.subheader("📊 Visão Geral de Clientes")
col_k1, col_k2, col_k3, col_k4, col_k5, col_k6 = st.columns(6)
col_k1.metric("Clientes Ativos YTD", f"{total_clientes_ativos_ytd}")
col_k2.metric("Taxa Recompra", f"{taxa_recompra:.1f}%")
col_k3.metric("Recência Média (dias)", recencia_media)
col_k4.metric("Freq. Média (compras)", freq_media)
col_k5.metric("Churn 3m", churn_3.shape[0])
col_k6.metric("Churn 6m", churn_6.shape[0])

st.divider()

# =============================
# Seções em Abas
# =============================
tab1, tab2, tab3, tab4 = st.tabs([
    "Novos x Recorrentes", "Top 10 Clientes", "Churn", "Detalhes"
])

with tab1:
    st.plotly_chart(fig_novos, use_container_width=True)
    col_a, col_b = st.columns(2)
    col_a.metric("Clientes Novos (mês)", qtd_novos)
    col_b.metric("Clientes Recorrentes (mês)", qtd_recorrentes)
    st.markdown("#### Lista (mês)")
    if not df_mes.empty:
        st.dataframe(df_mes[['ID_CLIENTE', 'RAZAO_SOCIAL', 'NOME_EQUIPE', 'ULTIMA_COMPRA', 'DATA_CADASTRO', 'TIPO_CLIENTE']].drop_duplicates('ID_CLIENTE'))
    else:
        st.info("Sem clientes com compra nesse mês.")

with tab2:
    st.markdown("### Top 10 Clientes por Faturamento (YTD)")
    if df_top10.empty:
        st.info("Sem dados de faturamento para o período.")
    else:
        fig_top = px.bar(df_top10, x='Faturamento', y='Cliente', orientation='h', text='Faturamento',
                         color='Faturamento', color_continuous_scale='Blues')
        fig_top.update_layout(yaxis={'categoryorder':'total ascending'}, height=500)
        st.plotly_chart(fig_top, use_container_width=True)
        st.dataframe(df_top10)

with tab3:
    st.markdown(f"### Churn (Data de corte: {data_corte.date()})")
    col_c1, col_c2 = st.columns(2)
    col_c1.subheader("Churn 3 meses")
    if churn_3.empty:
        col_c1.info("Nenhum cliente churn 3m.")
    else:
        col_c1.dataframe(churn_3.rename(columns={'UltimaCompra':'Última Compra'}))
    col_c2.subheader("Churn 6 meses")
    if churn_6.empty:
        col_c2.info("Nenhum cliente churn 6m.")
    else:
        col_c2.dataframe(churn_6.rename(columns={'UltimaCompra':'Última Compra'}))

with tab4:
    st.markdown("### Detalhes YTD")
    st.caption("Base de vendas filtrada YTD (somente colunas principais).")
    if not df_vendas_ytd.empty:
        cols_show = [c for c in ['Data', 'Cliente', 'Nota', 'Total NF', 'Flag tipo', 'Equipe'] if c in df_vendas_ytd.columns]
        st.dataframe(df_vendas_ytd[cols_show])
    else:
        st.info("Sem vendas no período.")

st.divider()

st.download_button(
    label="📥 Exportar Top 10 (CSV)",
    data=df_top10.to_csv(index=False).encode('utf-8'),
    file_name=f"top10_clientes_{ano_sel}_{mes_sel}.csv",
    mime='text/csv'
)

st.download_button(
    label="📥 Exportar Churn 6m (CSV)",
    data=churn_6.to_csv(index=False).encode('utf-8'),
    file_name=f"churn6m_{ano_sel}_{mes_sel}.csv",
    mime='text/csv'
)

st.caption("*Base construída somente com dados disponíveis; segmentação Direto vs Revenda poderá ser adicionada quando houver classificação de cliente.*")

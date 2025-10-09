import streamlit as st
from functions.menu import menu_with_redirect
st.set_page_config(layout="wide")
menu_with_redirect()

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

if "Admin" in user_role or "Consultor" in user_role:
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


# Novo: cache só por ano, mês só filtra dados já carregados
@st.cache_data(ttl=900)
def get_dados_ano(ano: int):
    """Retorna dataframes de clientes e vendas do ano inteiro (e ano anterior para churn)."""
    df_cli = load_clientes_raw()
    df_cli = df_cli[df_cli['ULTIMA_COMPRA'].dt.year.isin([ano - 1, ano])]
    df_cli['Ano'] = df_cli['ULTIMA_COMPRA'].dt.year
    df_cli['Mes'] = df_cli['ULTIMA_COMPRA'].dt.month

    # Vendas: carrega do ano anterior até o fim do ano selecionado
    from datetime import date as _date
    data_ini = _date(ano - 1, 1, 1).strftime('%Y-%m-%d')
    data_fim = _date(ano, 12, 31).strftime('%Y-%m-%d')
    dv = run_query_vendas(data_ini, data_fim)
    if 'Data' in dv.columns:
        dv['Data'] = pd.to_datetime(dv['Data'], errors='coerce')
    dv = dv[dv['Data'].dt.year.isin([ano - 1, ano])]
    dv['Ano'] = dv['Data'].dt.year
    dv['Mes'] = dv['Data'].dt.month
    return df_cli, dv

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
    # Formatar coluna 'UltimaCompra' para 'dd/mm/yyyy'
    if 'UltimaCompra' in churned.columns and pd.api.types.is_datetime64_any_dtype(churned['UltimaCompra']):
        churned['UltimaCompra'] = churned['UltimaCompra'].dt.strftime('%d/%m/%Y')
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


# Carrega dados do ano inteiro (e ano anterior para churn)
with st.spinner("🔄 Carregando dados do ano..."):
    df_clientes_raw, df_vendas_full = get_dados_ano(ano_sel)

# Aplicar filtro de equipe
df_clientes_raw = aplicar_filtro_equipe(df_clientes_raw)
df_vendas_full = aplicar_filtro_equipe(df_vendas_full)

# Filtros dinâmicos por mês (apenas em RAM)
mask_mes_cliente = (
    (df_clientes_raw['ULTIMA_COMPRA'].dt.year == ano_sel) &
    (df_clientes_raw['ULTIMA_COMPRA'].dt.month == mes_sel)
)
df_mes = df_clientes_raw[mask_mes_cliente].copy()
df_mes = classificar_novos_recorrentes(df_mes)
qtd_novos = (df_mes['TIPO_CLIENTE'] == 'Novo').sum()
qtd_recorrentes = (df_mes['TIPO_CLIENTE'] == 'Recorrente').sum()

# Para vendas YTD e métricas, filtra só em RAM
ultimo_dia_mes = monthrange(ano_sel, mes_sel)[1]
data_corte = datetime(ano_sel, mes_sel, ultimo_dia_mes)
inicio_ano = datetime(ano_sel, 1, 1)
df_vendas_ytd = df_vendas_full[(df_vendas_full['Data'] >= inicio_ano) & (df_vendas_full['Data'] <= data_corte)]

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


# Ajuste: labels sempre do lado de fora
fig_novos = go.Figure(data=[go.Pie(
    labels=['Novos', 'Recorrentes'],
    values=[qtd_novos, qtd_recorrentes],
    hole=0.5,
    marker=dict(colors=['#FFA726', '#1976D2'], line=dict(color='#fff', width=2)),
    textinfo='label+percent+value',
    pull=[0.08, 0.08],
    textposition='outside'
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
with col_k1:
    st.metric(
        "Clientes Ativos YTD",
        f"{total_clientes_ativos_ytd}",
        help="Clientes distintos que realizaram pelo menos uma compra entre 01/01 e o mês selecionado (acumulado no ano)."
    )
with col_k2:
    st.metric(
        "Taxa Recompra",
        f"{taxa_recompra:.1f}%",
        help="Percentual dos clientes ativos YTD que compraram 2 ou mais vezes no período acumulado do ano."
    )
with col_k3:
    st.metric(
        "Recência Média (dias)",
        recencia_media,
        help="Média de dias desde a última compra de cada cliente até a data de corte (final do mês selecionado)."
    )
with col_k4:
    st.metric(
        "Freq. Média (compras)",
        freq_media,
        help="Média de compras por cliente no período acumulado do ano até o mês selecionado."
    )
with col_k5:
    st.metric(
        "Churn 3m",
        churn_3.shape[0],
        help="Clientes que estão há 3 meses ou mais sem realizar compras até a data de corte."
    )
with col_k6:
    st.metric(
        "Churn 6m",
        churn_6.shape[0],
        help="Clientes que estão há 6 meses ou mais sem realizar compras até a data de corte."
    )

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
        df_lista = df_mes[['ID_CLIENTE', 'RAZAO_SOCIAL', 'NOME_EQUIPE', 'ULTIMA_COMPRA', 'DATA_CADASTRO', 'TIPO_CLIENTE']].drop_duplicates('ID_CLIENTE').copy()
        for col in ['ULTIMA_COMPRA', 'DATA_CADASTRO']:
            if col in df_lista.columns and pd.api.types.is_datetime64_any_dtype(df_lista[col]):
                df_lista[col] = df_lista[col].dt.strftime('%d/%m/%Y')
        st.dataframe(df_lista, hide_index=True)
    else:
        st.info("Sem clientes com compra nesse mês.")

with tab2:
    st.markdown("### Top 10 Clientes por Faturamento (YTD)")
    if df_top10.empty:
        st.info("Sem dados de faturamento para o período.")
    else:
        # Arredondar valores para exibição no gráfico
        df_top10_plot = df_top10.copy()
        if 'Faturamento' in df_top10_plot.columns:
            df_top10_plot['Faturamento'] = df_top10_plot['Faturamento'].round(2)
        fig_top = px.bar(
            df_top10_plot,
            x='Faturamento',
            y='Cliente',
            orientation='h',
            text='Faturamento',
            color='Faturamento',
            color_continuous_scale='Blues'
        )
        fig_top.update_traces(texttemplate='%{text:.2f}')
        fig_top.update_layout(yaxis={'categoryorder':'total ascending'}, height=500)
        st.plotly_chart(fig_top, use_container_width=True)
    df_top10_fmt = df_top10.copy()
    # Arredondar Faturamento para 2 casas decimais
    if 'Faturamento' in df_top10_fmt.columns:
        df_top10_fmt['Faturamento'] = df_top10_fmt['Faturamento'].round(2)
    for col in df_top10_fmt.columns:
        if pd.api.types.is_datetime64_any_dtype(df_top10_fmt[col]):
            df_top10_fmt[col] = df_top10_fmt[col].dt.strftime('%d/%m/%Y')
    st.dataframe(df_top10_fmt, hide_index=True)


with tab3:
    st.markdown(f"### Churn (Data de corte: {data_corte.date()})")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.subheader("Churn 3 meses")
        if churn_3.empty:
            st.info("Nenhum cliente churn 3m.")
        else:
            churn3_fmt = churn_3.rename(columns={'UltimaCompra':'Última Compra'}).copy()
            col = 'Última Compra'
            if col in churn3_fmt.columns and pd.api.types.is_datetime64_any_dtype(churn3_fmt[col]):
                churn3_fmt[col] = churn3_fmt[col].dt.strftime('%d/%m/%Y')
            st.dataframe(churn3_fmt, hide_index=True)
    with col_c2:
        st.subheader("Churn 6 meses")
        if churn_6.empty:
            st.info("Nenhum cliente churn 6m.")
        else:
            churn6_fmt = churn_6.rename(columns={'UltimaCompra':'Última Compra'}).copy()
            col = 'Última Compra'
            if col in churn6_fmt.columns and pd.api.types.is_datetime64_any_dtype(churn6_fmt[col]):
                churn6_fmt[col] = churn6_fmt[col].dt.strftime('%d/%m/%Y')
            st.dataframe(churn6_fmt, hide_index=True)

with tab4:
    st.markdown("### Detalhes YTD")
    st.caption("Base de vendas filtrada YTD (somente colunas principais).")
    if not df_vendas_ytd.empty:
        cols_show = [c for c in ['Data', 'Cliente', 'Nota', 'Total NF', 'Flag tipo', 'Equipe'] if c in df_vendas_ytd.columns]
        df_show = df_vendas_ytd[cols_show].copy()
        for col in df_show.columns:
            if pd.api.types.is_datetime64_any_dtype(df_show[col]):
                df_show[col] = df_show[col].dt.strftime('%d/%m/%Y')
        st.dataframe(df_show, hide_index=True)
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
st.markdown("---")
# Explicação Clientes Ativos YTD
st.subheader("Como é calculado: Clientes Ativos YTD")
st.markdown(f"""
**Clientes Ativos YTD** representa o número de clientes distintos que realizaram pelo menos uma compra entre 01/01/{ano_sel} e {data_corte.strftime('%d/%m/%Y')}.

Neste período, foram identificados **{total_clientes_ativos_ytd}** clientes ativos.

O cálculo é feito considerando todas as vendas do tipo 'V' (venda) no período acumulado do ano até o mês selecionado. Cada cliente é contado apenas uma vez, independentemente da quantidade de compras.
""")

# Exibir DataFrame com clientes ativos YTD
st.markdown("#### Lista de Clientes Ativos YTD")
if not df_vendas_ytd.empty:
    col_cliente = 'Cliente' if 'Cliente' in df_vendas_ytd.columns else df_vendas_ytd.columns[0]
    clientes_ativos = df_vendas_ytd[[col_cliente]].drop_duplicates().copy()
    # Se houver outras colunas identificadoras, exibir também
    cols_extras = [c for c in ['ID_CLIENTE', 'RAZAO_SOCIAL', 'NOME_EQUIPE'] if c in df_vendas_ytd.columns]
    cols_show = [col_cliente] + cols_extras
    clientes_ativos = df_vendas_ytd[cols_show].drop_duplicates(col_cliente).copy()
    st.dataframe(clientes_ativos, hide_index=True)
else:
    st.info("Sem clientes ativos no período.")

# ========================
# Rodapé Padronizado
# ========================
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p><strong>Dashboard de Inteligência Comercial</strong></p>
    <p>Período: 01/01/{ano_sel} a 31/12/{ano_sel}</p>
    <p>Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
</div>
""", unsafe_allow_html=True)
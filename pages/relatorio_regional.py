import streamlit as st
from functions.menu import menu_with_redirect

# Trecho exigido: deve aparecer primeiro no código
st.set_page_config(layout="wide", page_title="Relatório regional")
menu_with_redirect()

import pandas as pd
import plotly.express as px
import requests
from datetime import date, datetime
from functools import lru_cache

from functions.query import run_query  # Query detalhada existente

# ==============================================================
# Helpers / Cache
# ==============================================================

@st.cache_data(show_spinner=False, ttl=1200)
def buscar_dados_periodo(ano: int) -> pd.DataFrame:
	"""Replica metodologia de cache: carrega ano anterior+ano corrente.
	Retorna dataframe completo para ambos os anos (para gráficos YoY).
	"""
	inicio = date(ano - 1, 1, 1)
	fim = date(ano, 12, 31)
	df = run_query(inicio.strftime("%Y-%m-%d"), fim.strftime("%Y-%m-%d"))
	df['Data'] = pd.to_datetime(df['Data'])
	df['Mês'] = df['Data'].dt.month
	df['Ano'] = df['Data'].dt.year
	
	expected_cols = ['UF', 'Região', 'Total NF', 'Atividade', 'Ano', 'Mês']
	missing = [c for c in expected_cols if c not in df.columns]
	if missing:
		raise ValueError(f"Colunas necessárias ausentes na query: {missing}")
	return df

@lru_cache(maxsize=1)
def get_geojson_estados():
	"""Busca GeoJSON público de estados brasileiros (cache em memória)."""
	url = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
	try:
		r = requests.get(url, timeout=15)
		r.raise_for_status()
		return r.json()
	except Exception as e:
		st.warning(f"Falha ao carregar GeoJSON online: {e}")
		return None

UF_TO_NAME = {
	'AC': 'Acre','AL': 'Alagoas','AP': 'Amapa','AM': 'Amazonas','BA': 'Bahia','CE': 'Ceara',
	'DF': 'Distrito Federal','ES': 'Espirito Santo','GO': 'Goias','MA': 'Maranhao','MT': 'Mato Grosso',
	'MS': 'Mato Grosso do Sul','MG': 'Minas Gerais','PA': 'Para','PB': 'Paraiba','PR': 'Parana','PE': 'Pernambuco',
	'PI': 'Piaui','RJ': 'Rio de Janeiro','RN': 'Rio Grande do Norte','RS': 'Rio Grande do Sul','RO': 'Rondonia',
	'RR': 'Roraima','SC': 'Santa Catarina','SP': 'Sao Paulo','SE': 'Sergipe','TO': 'Tocantins'
}

def classifica_canal(atividade: str) -> str:
	if not isinstance(atividade, str):
		return 'Indefinido'
	a = atividade.upper()
	if 'REVEN' in a or 'DISTRIB' in a:
		return 'Revenda'
	return 'Direto'

def agrega_estado(df: pd.DataFrame) -> pd.DataFrame:
	return (df.groupby(['UF'], as_index=False)
			  .agg({ 'Total NF':'sum' }))

def agrega_regiao(df: pd.DataFrame) -> pd.DataFrame:
	return (df.groupby(['Região'], as_index=False)
			  .agg({ 'Total NF':'sum' }))

def prepara_mensal(df: pd.DataFrame) -> pd.DataFrame:
	dfm = (df.groupby(['Ano','Mês','UF','Região'], as_index=False)
			 .agg({'Total NF':'sum'}))
	dfm['Periodo'] = pd.to_datetime(dfm['Ano'].astype(str) + '-' + dfm['Mês'].astype(str) + '-01')
	return dfm

def variacao_percentual(serie: pd.Series) -> pd.Series:
	return serie.pct_change().fillna(0) * 100

# Layout de seleção (Ano/Mês) padronizado conforme outras páginas.

st.title('Relatório Regional')
st.caption('Mapa de calor e indicadores de faturamento por Estado e Região.')

# ⚠️ AVISO DE DESENVOLVIMENTO
st.warning("""
⚠️ **PÁGINA EM DESENVOLVIMENTO** ⚠️  
Esta página ainda está em fase de desenvolvimento e testes.  
**Os dados apresentados NÃO devem ser considerados para tomada de decisões.**  
Aguarde a versão final para uso oficial.
""")

# ===========================================
# LÓGICA DE ROLE/SETOR NO INÍCIO DO CÓDIGO
# ===========================================
user_role = st.session_state.get("role", [])
username = st.session_state.get("username", "Usuário Desconhecido")

role = None

if "Admin" in user_role or "Consultor" in user_role:
    setores = ["Indústria", "Varejo", "Exportação", "Admin (todas equipes)"]
    setor_base = st.selectbox("Selecione o setor", setores)
    if setor_base == "Varejo":
        st.markdown("---")
        role = "Varejo"
    elif setor_base == "Indústria":
        role = "Indústria"
    elif setor_base == "Exportação":
        role = "Exportação"
    else:
        role = "Admin (todas equipes)"

elif "Gerente Indústria" in user_role or "Indústria" in user_role:
    role = "Indústria"
    st.markdown(f"#### Setor: Indústria")

elif "Gerente Varejo" in user_role or "Varejo" in user_role:
    st.markdown("#### Setor: Varejo")
    role = "Varejo"
else:
    st.error("Acesso negado. Você não tem permissão para visualizar esta página.")
    st.stop()

hoje = date.today()
ano_atual = hoje.year
mes_atual = hoje.month
anos_disponiveis = list(range(ano_atual - 5, ano_atual + 1))
meses_ext = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
meses_labels = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]

col1, col2 = st.columns([2,1])
with col2:
	st.markdown("### Ano")
	ano = st.selectbox(
		"Ano",
		options=anos_disponiveis,
		index=anos_disponiveis.index(ano_atual),
		key="select_ano",
		label_visibility="collapsed"
	)

if ano == ano_atual:
	meses_disponiveis = list(range(1, mes_atual + 1))
else:
	meses_disponiveis = list(range(1, 13))

with col1:
	st.markdown("### Mês")
	mes = st.selectbox(
		"Mês",
		options=meses_disponiveis,
		format_func=lambda m: meses_ext[m - 1],
		index=meses_disponiveis.index(mes_atual) if ano == ano_atual else 0,
		key="select_mes",
		label_visibility="collapsed"
	)

with st.spinner('🔄 Carregando dados... (o banco só será consultado se mudar o ano)'):
	try:
		df_full = buscar_dados_periodo(ano).copy()
	except Exception as e:
		st.error(f'Falha ao carregar dados: {e}')
		st.stop()

# ========================================
# Aplique o filtro de setor apenas em RAM
# ========================================
if role == "Indústria":
    filtro_equipe = "INDUSTRIAL"
elif role == "Varejo":
    filtro_equipe = "VAREJO"
elif role == "Exportação":
    filtro_equipe = ["EXPORTAÇÃO VAREJO", "EXPORTAÇÃO INDUSTRIA"]
else:  # Admin (todas equipes)
    filtro_equipe = None

# Aplicar filtro de equipe se definido
if isinstance(filtro_equipe, list):
    if 'Equipe' in df_full.columns:
        df_full = df_full[df_full['Equipe'].isin(filtro_equipe)]
    else:
        df_full = df_full.copy()
elif filtro_equipe and 'Equipe' in df_full.columns:
    df_full = df_full[df_full['Equipe'] == filtro_equipe]

# Filtros derivados
df_full['Canal'] = df_full['Atividade'].apply(classifica_canal)
df_full['estado_nome'] = df_full['UF'].map(UF_TO_NAME)

# Recorte para análise principal (apenas mês; acumulado não exigido para layout idêntico)
df_ano = df_full[df_full['Ano'] == ano]
df_sel = df_ano[df_ano['Mês'] == mes]

if df_sel.empty:
	st.warning('Sem dados para o período selecionado.')
	st.stop()

# Select dinâmico de regiões
regioes_opcoes = sorted(df_sel['Região'].dropna().unique())
regiao_sel = st.multiselect('Filtrar Regiões', options=regioes_opcoes, default=[])
if regiao_sel:
	df_sel = df_sel[df_sel['Região'].isin(regiao_sel)]
	if df_sel.empty:
		st.warning('Nenhum dado após aplicar filtro de região.')
		st.stop()

st.title('KPIs Principais')
total_fat = df_sel['Total NF'].sum()
df_estado = agrega_estado(df_sel)
df_regiao = agrega_regiao(df_sel)
top_estado = df_estado.sort_values('Total NF', ascending=False).head(1)
top_nome = top_estado['UF'].iloc[0] if not top_estado.empty else '-'
top_val = top_estado['Total NF'].iloc[0] if not top_estado.empty else 0
share_top3 = df_estado.sort_values('Total NF', ascending=False).head(3)['Total NF'].sum() / total_fat * 100 if total_fat else 0

st.markdown(f"**Período Atual:** {meses_ext[mes-1]} / **Ano:** {ano}")

k1,k2,k3,k4 = st.columns(4)
k1.metric('Faturamento Total', f"R$ {total_fat:,.0f}".replace(',', '.'))
k2.metric('UFs com venda', df_estado['UF'].nunique())
k3.metric('Maior UF', f"{top_nome} | R$ {top_val:,.0f}".replace(',', '.'))
k4.metric('Top 3 UF Share', f"{share_top3:,.1f}%")

#
st.title('Mapa de Calor - Faturamento por Estado')
geojson = get_geojson_estados()
if geojson is not None:
	# IMPORTANTE: Antes usávamos o nome do estado sem acentuação para casar com properties.name (que tem acentos).
	# Isso fazia com que estados como Paraná, Goiás, São Paulo etc. não fossem reconhecidos.
	# Ajuste: usar a sigla (UF) e o campo properties.sigla do GeoJSON garante correspondência exata de todos os 27 estados.
	all_states_df = pd.DataFrame({
		'UF': list(UF_TO_NAME.keys()),
		'estado_nome': list(UF_TO_NAME.values())
	})
	df_estado_plot = all_states_df.merge(df_estado, on='UF', how='left')
	df_estado_plot['Total NF'] = df_estado_plot['Total NF'].fillna(0)
	vmax = df_estado_plot['Total NF'].max()
	fig_map = px.choropleth(
		df_estado_plot,
		geojson=geojson,
		locations='UF',              # agora usando UF
		featureidkey='properties.sigla',  # corresponde às siglas no GeoJSON
		color='Total NF',
		color_continuous_scale='YlOrRd',
		range_color=(0, vmax if vmax > 0 else 1),
		labels={'Total NF':'Faturamento'},
		hover_data={'estado_nome':True,'UF':True,'Total NF':':,.0f'}
	)
	fig_map.update_geos(fitbounds='locations', visible=False)
	fig_map.update_layout(
		margin=dict(l=0,r=0,t=0,b=0),
		geo=dict(bgcolor='rgba(0,0,0,0)'),
		paper_bgcolor='rgba(0,0,0,0)',
		plot_bgcolor='rgba(0,0,0,0)'
	)
	# Contorno branco uniforme para todos os estados
	fig_map.update_traces(marker_line_color='#FFFFFF', marker_line_width=1.1)
	st.plotly_chart(fig_map, use_container_width=True)
else:
	st.info('GeoJSON indisponível. Exibindo tabela simples.')
	st.dataframe(df_estado)

#
st.title('Distribuição por Região e UF')
c1,c2 = st.columns(2)
with c1:
	fig_bar_reg = px.bar(df_regiao.sort_values('Total NF', ascending=False), x='Região', y='Total NF', text_auto='.2s', title='Faturamento por Região')
	fig_bar_reg.update_traces(textposition='outside')
	st.plotly_chart(fig_bar_reg, use_container_width=True)
with c2:
	fig_bar_uf = px.bar(df_estado.sort_values('Total NF', ascending=False), x='UF', y='Total NF', text_auto='.2s', title='Faturamento por UF')
	fig_bar_uf.update_traces(textposition='outside')
	st.plotly_chart(fig_bar_uf, use_container_width=True)

#
st.title('Canais por Região')
df_canal = (df_sel.groupby(['Região','Canal'], as_index=False)
			  .agg({'Total NF':'sum'}))
fig_canal = px.bar(df_canal, x='Região', y='Total NF', color='Canal', barmode='stack', text_auto='.2s')
st.plotly_chart(fig_canal, use_container_width=True)

#
st.title('Variação Mensal (MoM) e Ano a Ano (YoY)')
df_mensal = prepara_mensal(df_ano)  # ano corrente para MoM
df_mensal_reg = (df_mensal.groupby(['Periodo','Região'], as_index=False)
						   .agg({'Total NF':'sum'}))
df_mensal_reg['MoM %'] = df_mensal_reg.groupby('Região')['Total NF'].transform(variacao_percentual)

# Construção YoY: comparar mês contra mesmo mês ano anterior (usando df_full)
df_mensal_full = prepara_mensal(df_full)
df_mensal_full_reg = (df_mensal_full.groupby(['Ano','Mês','Região'], as_index=False)
								 .agg({'Total NF':'sum'}))
df_yoy_curr = df_mensal_full_reg[df_mensal_full_reg['Ano'] == ano]
df_yoy_prev = df_mensal_full_reg[df_mensal_full_reg['Ano'] == (ano - 1)][['Região','Mês','Total NF']].rename(columns={'Total NF':'Total NF_prev'})
df_yoy_merge = pd.merge(df_yoy_curr, df_yoy_prev, on=['Região','Mês'], how='left')
df_yoy_merge['YoY %'] = ((df_yoy_merge['Total NF'] - df_yoy_merge['Total NF_prev']) / df_yoy_merge['Total NF_prev'] * 100)
df_yoy_merge['Periodo'] = pd.to_datetime(df_yoy_merge['Ano'].astype(str) + '-' + df_yoy_merge['Mês'].astype(str) + '-01')

tab1, tab2 = st.tabs(['MoM', 'YoY'])
with tab1:
	fig_mom = px.line(df_mensal_reg, x='Periodo', y='Total NF', color='Região', markers=True)
	st.plotly_chart(fig_mom, use_container_width=True)
	st.dataframe(df_mensal_reg.pivot_table(index='Periodo', columns='Região', values='MoM %'))
with tab2:
	fig_yoy = px.line(df_yoy_merge, x='Periodo', y='YoY %', color='Região', markers=True)
	st.plotly_chart(fig_yoy, use_container_width=True)
	st.dataframe(df_yoy_merge.pivot_table(index='Periodo', columns='Região', values='YoY %'))

with st.expander('Detalhe (amostra de linhas cruas do período selecionado)'):
	st.dataframe(df_sel.head(200))

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

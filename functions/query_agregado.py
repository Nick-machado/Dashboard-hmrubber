import pandas as pd
from datetime import date
from functions.connect import get_connection

"""
Consultas agregadas para otimizar carregamento da página visao_geral_vendas
Mantém a lógica original (somas de Total NF, $ Margem e Vlr.ICM) porém já sumariza
no banco por Ano/Mês/Flag_Tipo/Equipe/Atividade, reduzindo volume de linhas.
Ainda NÃO substitui a query detalhada existente; serve como base para migração gradual.
"""

BASE_EXPRESSOES = """
    (I.TOTMERC + ABS(I.VALORIPI) - (I.ICMS_ZF + I.PIS_COFINS_ZF) + I.NFE_VFRETE) AS TOTAL_NF_LINHA,
    -COALESCE(I.VALORICM, 0) AS VLR_ICM_LINHA,
    (
        ROUND((
            I.TOTMERC
            - (I.VALOR_PIS + I.VALOR_COFINS)
            - COALESCE(I.VALORICM, 0)
            - COALESCE(N.VALOR_FRETE_PAGO * (I.TOTMERC / NULLIF(N.TOTMERC, 0)), 0)
            - (((I.TOTMERC - I.ICMS_ZF + I.PIS_COFINS_ZF) * I.COMISSAO) / 100)
            - (I.ICMS_ZF + I.PIS_COFINS_ZF)
            + I.NFE_VFRETE
        ), 5)
        - (
            I.QUANT * CAST((
                SELECT FIRST 1 COALESCE(PM.VALOR, 0)
                FROM PRECO_MEDIO_DIA PM
                WHERE PM.ID_MATERIAL = MC.REGISTRO
                  AND PM.DATA BETWEEN '01/01/2010' AND N.DATA
                ORDER BY PM.DATA DESC
            ) AS NUMERIC(15,4))
        )
    ) AS MARGEM_LINHA
"""

def run_query_agregado(data_in: str, data_fin: str) -> pd.DataFrame:
    """Retorna dados agregados por Ano/Mês/Flag_Tipo/Equipe/Atividade.

    Args:
        data_in: data inicial (YYYY-MM-DD)
        data_fin: data final (YYYY-MM-DD)
    """
    cnxn = get_connection()

    # Ajustado: inclui EQUIPE já na subquery, evitando expressão não agrupada
    query = f"""
    SELECT
        EXTRACT(YEAR FROM X.DATA) AS ANO,
        EXTRACT(MONTH FROM X.DATA) AS MES,
        X.FLAG_TIPO,
        X.EQUIPE,
        X.ATIVIDADE,
        SUM(X.TOTAL_NF_LINHA) AS TOTAL_NF,
        SUM(X.VLR_ICM_LINHA) AS VLR_ICM,
        SUM(X.MARGEM_LINHA) AS MARGEM
    FROM (
        SELECT
            N.DATA,
            T.FLAG_TIPO,
            P.ATIVIDADE,
            COALESCE(EQ.EQUIPE, 'SEM EQUIPE') AS EQUIPE,
            {BASE_EXPRESSOES}
        FROM ITEMNOTA I
        INNER JOIN NOTAS N ON N.REGISTRO = I.NOTA
        INNER JOIN EMPRESAS E ON E.REGISTRO = N.EMPRESA
        INNER JOIN TIPO_VENDA T ON T.REGISTRO = I.ID_TIPONOTA
        INNER JOIN CLIENTES C ON (C.PESSOA = N.CLIENTE AND C.EMPRESA = E.TAB_CLIENTES)
        INNER JOIN PESSOAS P ON P.CODIGO = N.CLIENTE
        INNER JOIN MATERIAIS M ON M.REGISTRO = I.PRODUTO
        INNER JOIN MATERIAIS_COMPL MC ON (MC.REG_MATERIAL = I.PRODUTO AND MC.REG_EMPRESA = N.EMPRESA)
        LEFT JOIN VENDEDORES VD ON VD.PESSOA = N.VENDEDOR
        LEFT JOIN EQUIPES EQ ON EQ.REGISTRO = VD.EQUIPE
        WHERE
          N.EMPRESA IN (1,2)
          AND N.SITUACAO <> 'C'
          AND N.DATA BETWEEN ? AND ?
          AND T.FLAG_TIPO IN ('V','D')
    ) X
    GROUP BY 1,2,3,4,5
    ORDER BY 1,2,3;
    """

    df = pd.read_sql(query, cnxn, params=[data_in, data_fin])
    return df


def run_query_agregado_ano(ano: int) -> pd.DataFrame:
    """Busca agregados de (ano-1-01-01) até (ano-12-31) para comparar ano atual x anterior."""
    data_in = date(ano-1, 1, 1).strftime('%Y-%m-%d')
    data_fin = date(ano, 12, 31).strftime('%Y-%m-%d')
    df = run_query_agregado(data_in, data_fin)
    return df


def get_detalhe_mes(ano: int, mes: int) -> pd.DataFrame:
    """Carrega somente o detalhe (linhas) de um mês específico do ano informado
    usando a query detalhada já existente (run_query) para futuros drill-downs.
    """
    from calendar import monthrange
    from functions.query import run_query as run_query_detalhe
    dia_fim = monthrange(ano, mes)[1]
    data_in = date(ano, mes, 1).strftime('%Y-%m-%d')
    data_fin = date(ano, mes, dia_fim).strftime('%Y-%m-%d')
    df = run_query_detalhe(data_in, data_fin)
    return df

__all__ = [
    'run_query_agregado',
    'run_query_agregado_ano',
    'get_detalhe_mes'
]

import pandas as pd
from functions.connect import get_connection

# ===================================================================
# SOLUÇÃO CORRIGIDA - ANÁLISE DE MARGENS
# ===================================================================
# 
# PROBLEMA IDENTIFICADO:
# - A query original não aplicava filtro de data (parâmetros ignorados)
# - CTEs desnecessárias estavam incluídas
# - INNER JOINs estavam excluindo registros válidos
# - Resultado: apenas 15 registros em vez dos 72 esperados
#
# SOLUÇÃO APLICADA:
# - Adicionado filtro de data na cláusula WHERE
# - Removidas CTEs não utilizadas
# - Alterados JOINs opcionais para LEFT JOIN
# - Mantido filtro de situação 'Liberado'
# ===================================================================

def run_query(data_in, data_fin):
    """
    Executa a query de análise de margens com filtro de data
    
    Args:
        data_in (str): Data inicial no formato 'YYYY-MM-DD'
        data_fin (str): Data final no formato 'YYYY-MM-DD'
    
    Returns:
        DataFrame: Dados dos pedidos no período especificado
    """
    cnxn = get_connection()

    query = f"""
    SELECT 
        C.DATA,
        C.SITUACAO,
        EMP.RAZAOSOC AS EMPRESA,
        C.PROGRAMADO,
        C.REGISTRO AS ID_PEDIDO,
        V.DESCRICAO AS TIPO_MOVIMENTO,
        ((I.VALOR - COALESCE(I.DESC_VALOR, 0)) * I.QUANT) AS VALOR_LIQUIDO,
        ((I.VALOR - COALESCE(I.DESC_VALOR, 0)) * I.QUANT) + COALESCE(I.VALORIPI, 0) AS VALOR_TOTAL_COM_IPI,
        PV.RAZAOSOC AS VENDEDOR,
        E.EQUIPE,
        C.CLIENTE || ' - ' || P.RAZAOSOC AS CLIENTE

    FROM PEDIDOS C
    INNER JOIN ITEMPED I ON I.PEDIDO = C.REGISTRO
    LEFT JOIN MATERIAIS_UNIDADES U ON U.REGISTRO = I.REG_UNIDADE
    INNER JOIN MATERIAIS M ON M.REGISTRO = I.PRODUTO
    LEFT JOIN MATERIAIS_COMPL MC ON MC.REG_MATERIAL = M.REGISTRO AND MC.REG_EMPRESA = C.EMPRESA
    LEFT JOIN TIPO_VENDA V ON V.REGISTRO = I.ID_TIPONOTA
    INNER JOIN EMPRESAS EMP ON EMP.REGISTRO = C.EMPRESA
    LEFT JOIN PESSOAS P ON P.CODIGO = C.CLIENTE
    LEFT JOIN VENDEDORES VEN ON VEN.PESSOA = C.VENDEDOR
    LEFT JOIN PESSOAS PV ON PV.CODIGO = VEN.PESSOA
    LEFT JOIN EQUIPES E ON E.REGISTRO = VEN.EQUIPE

    WHERE C.DATA >= '{data_in}' 
      AND C.DATA <= '{data_fin}'
      AND C.SITUACAO IN ('Liberado')
    
    ORDER BY C.DATA, C.REGISTRO, I.REGISTRO
    """

    # Executa a query
    df = pd.read_sql(query, cnxn)
    df['DATA'] = pd.to_datetime(df['DATA']).dt.date
    return df

# ===================================================================
# EXEMPLO DE USO:
# ===================================================================
# df = run_query('2025-06-01', '2025-06-30')
# print(f'Registros retornados: {len(df)}')
# print(f'Pedidos únicos: {df["ID_PEDIDO"].nunique()}')
# print(f'Total VALOR_LIQUIDO: {df["VALOR_LIQUIDO"].sum():,.2f}')
#
# RESULTADO ESPERADO (baseado no relatório Excel):
# - Registros: 72
# - Pedidos únicos: 14
# - Total VALOR_LIQUIDO: R$ 1,232,829.27
# - Total VALOR_TOTAL_COM_IPI: R$ 1,238,557.53
# ===================================================================


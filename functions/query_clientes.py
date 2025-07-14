import pandas as pd
from functions.connect import get_connection  # Adicionado

# ===================================================================
# Helper: executa a query parametrizada por empresa e tipo de movimento
# ===================================================================
def run_query(data_in, data_fin):
    cnxn = get_connection()  # Alterado para usar get_connection
    query = f"""
SELECT 
    c.REGISTRO AS ID_CLIENTE,
    c.ULTCOMPRA AS ULTIMA_COMPRA,
    c.DATACAD AS DATA_CADASTRO,
    c.VENDEDOR AS ID_VENDEDOR,
    v.EQUIPE AS CODIGO_EQUIPE,
    e.EQUIPE AS NOME_EQUIPE,
    p.RAZAOSOC AS RAZAO_SOCIAL,
    p.ENDERECO || ', ' ||
    p.NUMERO || ' - ' ||
    p.BAIRRO || ', ' ||
    p.CIDADE || ' - ' ||
    p.ESTADO || ', ' ||
    p.CEP AS ENDERECO,

    -- Última nota do cliente
    (
        SELECT FIRST 1 n.NOTA
        FROM NOTAS n
        WHERE n.CLIENTE = c.REGISTRO
        ORDER BY n.DATA DESC
    ) AS ULTIMA_NOTA,

    (
        SELECT FIRST 1 n.DATA
        FROM NOTAS n
        WHERE n.CLIENTE = c.REGISTRO
        ORDER BY n.DATA DESC
    ) AS DATA_ULTIMA_NOTA

FROM 
    CLIENTES c
JOIN 
    PESSOAS p ON c.REGISTRO = p.CODIGO
LEFT JOIN 
    VENDEDORES v ON c.VENDEDOR = v.PESSOA
LEFT JOIN
    EQUIPES e ON v.EQUIPE = e.REGISTRO
WHERE 
    c.ULTCOMPRA BETWEEN '{data_in}' AND '{data_fin}'
"""
    df = pd.read_sql(query, cnxn)
    df['ULTIMA_COMPRA'] = pd.to_datetime(df['ULTIMA_COMPRA']).dt.date
    df['DATA_CADASTRO'] = pd.to_datetime(df['DATA_CADASTRO']).dt.date
    return df
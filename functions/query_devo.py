import pandas as pd
from functions.connect import get_connection  # Adicionado

# ===================================================================
# Helper: executa a query parametrizada por empresa e tipo de movimento
# ===================================================================
def run_query(data_in, data_fin):
    cnxn = get_connection()  # Alterado para usar get_connection
    query = f"""
SELECT
    n.DATA,
    n.nota || '/' || n.serie AS nota,
    V.DESCRICAO AS TIPO_MOVIMENTO,
    m.codigo AS cod_prod,
    m.descricao,
    I.QUANT AS QUANT,
    CAST(
        IIF(
            v.registro IN (01,70,71,79,83,98,120,122,128,143,154,156,160,164,179,181,184,223,224,22),
            ((i.valor + i.pis_cofins_zf - (i.desconto / 100) * (i.valor + i.pis_cofins_zf)) * -1),
            (i.valor - (i.desconto / 100) * i.valor)
        ) AS DECIMAL(10, 2)
    ) AS valor_unitario,
    CAST(
        IIF(
            v.registro IN (01,70,71,79,83,98,120,122,128,143,154,156,160,164,179,181,184,223,224,22),
            ((i.valor - (i.desconto / 100) * i.valor) * I.QUANT + COALESCE(i.valoripi, 0)) * -1,
            ((i.valor - (i.desconto / 100) * i.valor) * I.QUANT + COALESCE(i.valoripi, 0))
        ) - (i.icms_zf + i.pis_cofins_zf)
        AS DECIMAL(10, 2)
    ) AS total_mercadoria,
    (i.val_frete + i.totmerc) * -1 AS total_NF,
    G.GRUPO,
    S.SUBGRUPO,
    i.nfe_cfop AS cfop,
    EXTRACT(MONTH FROM n.DATA) AS mes,
    EXTRACT(YEAR FROM n.DATA) AS ano,
    i.lote,
    emp.razaosoc AS empresa,
    i.registro,
    n.fornecedor || ' - ' || p.razaosoc AS cliente,
    pv.razaosoc AS vendedor,
    e.equipe
FROM compras n
INNER JOIN it_compras i ON i.nota = n.REGISTRO
INNER JOIN MATERIAIS m ON m.REGISTRO = i.produto
INNER JOIN GRUPOS G ON G.REGISTRO = m.GRUPO
INNER JOIN SUBGRUPOS S ON S.REGISTRO = m.SUBGRUPO
INNER JOIN TIPO_VENDA V ON V.REGISTRO = i.ID_TIPONOTA
INNER JOIN empresas emp ON emp.registro = n.empresa
INNER JOIN pessoas p ON p.codigo = n.fornecedor
LEFT JOIN clientes c ON c.pessoa = n.fornecedor
LEFT JOIN vendedores ven ON ven.pessoa = c.vendedor
LEFT JOIN pessoas pv ON pv.codigo = ven.pessoa
LEFT JOIN equipes e ON e.registro = ven.equipe
WHERE n.DATA BETWEEN '{data_in}' AND '{data_fin}'
  AND n.situacao <> 'C'
  AND v.registro IN (01,70,71,79,83,98,120,122,128,143,154,156,160,164,179,181,184,223,224,22)
"""
    df = pd.read_sql(query, cnxn)
    df['DATA'] = pd.to_datetime(df['DATA']).dt.date
    return df
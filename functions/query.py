# ================================
# query_margem.py
# ================================
import pandas as pd
from functions.connect import get_connection  # Importa a função correta

# Função que executa a consulta com filtro por empresa e tipo de movimento
def run_query(data_in, data_fin):
    cnxn = get_connection()  # Usa a função get_connection

    query = f"""
SELECT
  N.DATA AS "Data",
  CAST(N.NOTA AS VARCHAR(10)) || '/' || N.SERIE AS "Nota",
  T.DESCRICAO AS "Tipo Movimento",
  T.FLAG_TIPO AS "Flag tipo",
  N.CLIENTE AS "Cód. Cli",
  P.RAZAOSOC AS "Cliente",
  M.CODIGO AS "Cód. Prod",
  M.DESCRICAO AS "Produto",
  I.QUANT AS "Quant.",
  CAST((I.TOTMERC / NULLIF(I.QUANT, 0)) AS NUMERIC(15,4)) AS "Valor Unit.",
  -COALESCE(I.NFE_VDESC, 0) AS "Desconto.",
  CAST((-I.QUANT * (I.VALOR * (I.DESCONTO / 100))) AS NUMERIC(15,2)) AS "Total Desc.",
  (I.TOTMERC + ABS(I.VALORIPI) - (I.ICMS_ZF + I.PIS_COFINS_ZF) + I.NFE_VFRETE) AS "Total NF",
  I.TOTMERC AS "Total Merc.",
  I.NFE_VFRETE AS "Frete+Seg",
  -COALESCE(I.VALORICM, 0) AS "Vlr.ICM",
  I.NFE_VICMSUFDEST AS "Part.Dest.",
  -(I.VALOR_PIS + I.VALOR_COFINS) AS "Vlr.Pis/Cofins",
  -COALESCE((N.VALOR_FRETE_PAGO * (I.TOTMERC / NULLIF(N.TOTMERC, 0))), 0) AS "Vlr.Frete",
  -(((I.TOTMERC - I.ICMS_ZF + I.PIS_COFINS_ZF) * I.COMISSAO) / 100) AS "Vlr.Comissão",
  -(I.ICMS_ZF + I.PIS_COFINS_ZF) AS "Vlr.ZF",

  -- CÁLCULO CORRIGIDO DO VALOR LÍQUIDO
  ROUND((
    I.TOTMERC
    - (I.VALOR_PIS + I.VALOR_COFINS)
    - COALESCE(I.VALORICM, 0)
    - COALESCE(N.VALOR_FRETE_PAGO * (I.TOTMERC / NULLIF(N.TOTMERC, 0)), 0)
    - (((I.TOTMERC - I.ICMS_ZF + I.PIS_COFINS_ZF) * I.COMISSAO) / 100)
    - (I.ICMS_ZF + I.PIS_COFINS_ZF)
    + I.NFE_VFRETE
  ), 5) AS "Vlr.Líquido",

  -(
    I.QUANT * CAST((
      SELECT FIRST 1 COALESCE(PM.VALOR, 0)
      FROM PRECO_MEDIO_DIA PM
      WHERE PM.ID_MATERIAL = MC.REGISTRO
        AND PM.DATA BETWEEN '01/01/2010' AND N.DATA
      ORDER BY PM.DATA DESC
    ) AS NUMERIC(15,4))
  ) AS "Vlr.CMV",

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
  -
  (
    I.QUANT * CAST((
      SELECT FIRST 1 COALESCE(PM.VALOR, 0)
      FROM PRECO_MEDIO_DIA PM
      WHERE PM.ID_MATERIAL = MC.REGISTRO
        AND PM.DATA BETWEEN '01/01/2010' AND N.DATA
      ORDER BY PM.DATA DESC
    ) AS NUMERIC(15,4))
  )
) AS "$ Margem",

  ROUND((
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
    -
    (
      I.QUANT * CAST((
        SELECT FIRST 1 COALESCE(PM.VALOR, 0)
        FROM PRECO_MEDIO_DIA PM
        WHERE PM.ID_MATERIAL = MC.REGISTRO
          AND PM.DATA BETWEEN '01/01/2010' AND N.DATA
        ORDER BY PM.DATA DESC
      ) AS NUMERIC(15,4))
    )
  ) / NULLIF((I.TOTMERC + ABS(I.VALORIPI) - (I.ICMS_ZF + I.PIS_COFINS_ZF) + I.NFE_VFRETE), 0) * 100
), 2) AS "Mg.Líq",

  ROUND((
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
    -
    (
      I.QUANT * CAST((
        SELECT FIRST 1 COALESCE(PM.VALOR, 0)
        FROM PRECO_MEDIO_DIA PM
        WHERE PM.ID_MATERIAL = MC.REGISTRO
          AND PM.DATA BETWEEN '01/01/2010' AND N.DATA
        ORDER BY PM.DATA DESC
      ) AS NUMERIC(15,4))
    )
  ) / NULLIF(I.TOTMERC, 0) * 100
), 2) AS "Mg.Bruta",

  ABS(I.VALORIPI) AS "Vlr.IPI",
  CT.CATEGORIA AS "Categoria",
  P.ATIVIDADE AS "Atividade",
  R.REGIAO AS "Região",
  G.GRUPO AS "Grupo",
  S.SUBGRUPO AS "Subgrupo",
  PV.FANTASIA AS "Vendedor",

  (
    SELECT FIRST 1 EQ.EQUIPE
    FROM VENDEDORES VD
    JOIN EQUIPES EQ ON EQ.REGISTRO = VD.EQUIPE
    WHERE VD.PESSOA = N.VENDEDOR
  ) AS "Equipe",

  I.NFE_CFOP AS "CFOP",
  P.ESTADO AS "UF",
  P.CIDADE AS "Cidade",
  EXTRACT(MONTH FROM N.DATA) AS "Mês",
  EXTRACT(YEAR FROM N.DATA) AS "Ano",
  L.DESCRICAO AS "Estoque",
  M.MARCA AS "Marca",
  N.REGISTRO AS "Id"

FROM ITEMNOTA I
INNER JOIN NOTAS N ON N.REGISTRO = I.NOTA
INNER JOIN EMPRESAS E ON E.REGISTRO = N.EMPRESA
INNER JOIN TIPO_VENDA T ON T.REGISTRO = I.ID_TIPONOTA
INNER JOIN CLIENTES C ON (C.PESSOA = N.CLIENTE AND C.EMPRESA = E.TAB_CLIENTES)
INNER JOIN PESSOAS P ON P.CODIGO = N.CLIENTE
INNER JOIN MATERIAIS M ON M.REGISTRO = I.PRODUTO
INNER JOIN MATERIAIS_COMPL MC ON (MC.REG_MATERIAL = I.PRODUTO AND MC.REG_EMPRESA = N.EMPRESA)
INNER JOIN GRUPOS G ON G.REGISTRO = M.GRUPO
INNER JOIN SUBGRUPOS S ON S.REGISTRO = M.SUBGRUPO
INNER JOIN LOCAIS_ESTOQUE L ON L.REGISTRO = I.REG_ESTOQUE
LEFT JOIN PESSOAS PV ON PV.CODIGO = N.VENDEDOR
LEFT JOIN CATEGORIAS CT ON CT.REGISTRO = C.CATEGORIA
LEFT JOIN VENDAS_REGIAO R ON R.REGISTRO = C.ID_REGIAO

WHERE
  N.EMPRESA IN (1, 2)
  AND N.SITUACAO <> 'C'
  AND N.DATA BETWEEN '{data_in}' AND '{data_fin}'
  AND T.FLAG_TIPO IN ('V', 'D')

ORDER BY N.DATA, N.NOTA;
    """
    df = pd.read_sql(query, cnxn)
    df['Data'] = pd.to_datetime(df['Data']).dt.date
    return df


# ====================================================
# Função principal com 3 argumentos corretamente
# ====================================================
def gerar_planilha_concatenada(data_in, data_fin):
    df = run_query(data_in, data_fin)
    return df

def gerar_soma(data_in, data_fin, empresa_id, flag_tipo):
    df = run_query(data_in, data_fin, empresa_id, flag_tipo)
    df_soma = df["Mg.Líq"].sum()
    return df_soma
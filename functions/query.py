# ================================
# query_margem.py
# ================================
import pyodbc
import pandas as pd

# Função que executa a consulta com filtro por empresa e tipo de movimento
def run_query(data_in, data_fin, empresa_id, flag_tipo):
    conn_str = (
        "DRIVER=Firebird/InterBase(r) driver;"
        "UID=CONSULTORIA;"
        "PWD=HM#2024!;"
        "DBNAME=mk.rpsolution.com.br/30509:/banco/hmrubber/hmrubber.fdb;"
        "CHARSET=UTF8;"
    )
    cnxn = pyodbc.connect(conn_str)

    query = f"""
    SELECT
      N.DATA AS "Data",
      CAST(N.NOTA AS VARCHAR(10)) || '/' || N.SERIE AS "Nota",
      T.DESCRICAO AS "Tipo Movimento",
      N.CLIENTE AS "Cód. Cli",
      P.RAZAOSOC AS "Cliente",
      M.CODIGO AS "Cód. Prod",
      M.DESCRICAO AS "Produto",
      I.QUANT AS "Quant.",
      CAST((I.TOTMERC / NULLIF(I.QUANT, 0)) AS NUMERIC(15,4)) AS "Valor Unit.",
      -COALESCE(I.NFE_VDESC, 0) AS "Desconto.",
      CAST((-I.QUANT * (I.VALOR * (I.DESCONTO / 100))) AS NUMERIC(15,2)) AS "Total Desc.",
      (I.TOTMERC + ABS(I.VALORIPI)) AS "Total NF",
      I.TOTMERC AS "Total Merc.",
      -COALESCE(I.VALORICM, 0) AS "Vlr.ICM",
      I.NFE_VICMSUFDEST AS "Part.Dest.",
      -(I.VALOR_PIS + I.VALOR_COFINS) AS "Vlr.Pis/Cofins",
      -COALESCE((N.VALOR_FRETE_PAGO * (I.TOTMERC / NULLIF(N.TOTMERC, 0))), 0) AS "Vlr.Frete",
      -(((I.TOTMERC - I.ICMS_ZF + I.PIS_COFINS_ZF) * I.COMISSAO) / 100) AS "Vlr.Comissão",
      -(I.ICMS_ZF + I.PIS_COFINS_ZF) AS "Vlr.ZF",
      (I.TOTMERC + ABS(I.VALORIPI)
       - ABS(COALESCE(I.VALORICM, 0))
       - ABS(I.NFE_VICMSUFDEST)
       - ABS(I.VALOR_PIS + I.VALOR_COFINS)
       - ABS(COALESCE(N.VALOR_FRETE_PAGO * (I.TOTMERC / NULLIF(N.TOTMERC, 0)), 0))
       - ABS(((I.TOTMERC - I.ICMS_ZF + I.PIS_COFINS_ZF) * I.COMISSAO) / 100)
      ) AS "Vlr.Líquido",
      -- (Vlr.CMV e Margem seguem aqui...)

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
      N.EMPRESA = {empresa_id}
      AND N.SITUACAO = 'N'
      AND N.DATA BETWEEN '{data_in}' AND '{data_fin}'
      AND T.FLAG_TIPO IN ('{flag_tipo}')
    ORDER BY N.DATA, N.NOTA;
    """
    df = pd.read_sql(query, cnxn)
    df['Data'] = pd.to_datetime(df['Data']).dt.date
    return df


# ====================================================
# Função principal com 3 argumentos corretamente
# ====================================================
def gerar_planilha_concatenada(data_in, data_fin):
    df1 = run_query(data_in, data_fin, empresa_id=1, flag_tipo='V')
    df2 = run_query(data_in, data_fin, empresa_id=2, flag_tipo='V')
    df_total = pd.concat([df1, df2], ignore_index=True)
    return df_total
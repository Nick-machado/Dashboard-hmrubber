import pyodbc
import pandas as pd
import json

# ===================================================================
# Helper: executa a query parametrizada por empresa e tipo de movimento
# ===================================================================
def run_query(data_in, data_fin):
    conn_str = (
        "DRIVER=Firebird/InterBase(r) driver;"
        "UID=CONSULTORIA;"
        "PWD=HM#2024!;"
        "DBNAME=mk.rpsolution.com.br/30509:/banco/hmrubber/hmrubber.fdb;"
        "CHARSET=UTF8;"
    )
    cnxn = pyodbc.connect(conn_str)

    query = f"""
WITH EstoqueCTE AS (
    SELECT
        M.REGISTRO AS ID_PRODUTO,
        m.empresa as empresa,
        M.CODIGO,
        M.DESCRICAO,
        SUM(E.QUANTIDADE) AS QUANT_ESTOQUE,
      SUM(COALESCE(E.RESERVA, 0)) AS QUANT_RESERVADA_ESTOQUE
    FROM MOV_ESTOQUE E
    INNER JOIN MATERIAIS M ON M.REGISTRO = E.REG_MATERIAL
    INNER JOIN LOCAIS_ESTOQUE L ON L.REGISTRO = E.REG_ESTOQUE
    inner join empresas emp on emp.registro=m.empresa
    WHERE L.ESTOQUE_DISPONIVEL = 'S'
    and l.registro in (1,35,129)
    GROUP BY M.REGISTRO,empresa,  M.CODIGO, M.DESCRICAO
) ,
Reservado AS (
    SELECT 
        M.REGISTRO AS ID_PRODUTO,
         c.empresa as empresa ,
       max(C.REGISTRO )pedido,
        SUM(I.QUANT) AS QUANT_RESERVADA
    FROM 
        PEDIDOS C
        INNER JOIN ITEMPED I ON I.PEDIDO = C.REGISTRO
        INNER JOIN MATERIAIS M ON M.REGISTRO = I.PRODUTO
        inner join empresas emp on emp.registro=c.empresa
    WHERE 
        C.SITUACAO IN ('Liberado', 'Parcial', 'Faturar','Bloqueado')
      AND C.PROGRAMADO BETWEEN ? AND ?
      --   AND C.PROGRAMADO BETWEEN '01.01.2025' and '06.11.2025'
  -- and m.codigo='P17'
    GROUP BY  M.REGISTRO,empresa
)

SELECT 
    C.DATA,
    C.SITUACAO,
    emp.razaosoc as empresa ,
    C.PROGRAMADO,
    C.REGISTRO AS ID_PEDIDO,
--    c.flag_etapa as etapa,
    V.DESCRICAO AS TIPO_MOVIMENTO,
   -- M.CODIGO AS ID_PRODUTO,
   -- M.DESCRICAO,
 --   I.QUANT AS QUANT_PEDIDO,
 --   r.QUANT_RESERVADA  AS QUANT_RESERVADA,
  ---  COALESCE(EC.QUANT_ESTOQUE, 0) AS QUANT_ESTOQUE ,
 /*    COALESCE(EC.QUANT_ESTOQUE, 0) - r.QUANT_RESERVADA disponivel ,
     CASE
        WHEN COALESCE(EC.QUANT_ESTOQUE, 0) - r.QUANT_RESERVADA <= 0 THEN
         'Não Supre '   ||'N° Pedido:'|| max(C.REGISTRO)
        ELSE   'Supre'
    END AS STATUS_SUPRIMENTO,

    U.UNIDADE,   */
    (((i.valor - coalesce( i.desc_valor,0) )
    * I.QUANT )) as valor_liquido,

    (((i.valor - coalesce( i.desc_valor,0) )
    * I.QUANT ))    +
    coalesce(i.valoripi,0)  as valor_total_com_IPI,

  --  i.faturado,
 --    I.QUANT -  i.faturado falta
    pv.razaosoc vendedor,
    e.equipe,
    c.cliente ||' - '|| p.razaosoc cliente

FROM 
    PEDIDOS C
    INNER JOIN ITEMPED I ON I.PEDIDO = C.REGISTRO
    INNER JOIN MATERIAIS_UNIDADES U ON U.REGISTRO = I.REG_UNIDADE
    INNER JOIN MATERIAIS M ON M.REGISTRO = I.PRODUTO
    INNER JOIN MATERIAIS_COMPL MC ON MC.REG_MATERIAL = M.REGISTRO AND MC.REG_EMPRESA = C.EMPRESA
    INNER JOIN TIPO_VENDA V ON V.REGISTRO = I.ID_TIPONOTA
    inner join empresas emp on emp.registro=c.empresa
    inner join pessoas p on p.codigo = c.cliente
    inner join vendedores ven on ven.pessoa = c.vendedor
    inner join pessoas pv on pv.codigo = ven.pessoa
    inner join equipes e on e.registro = ven.equipe

LEFT JOIN EstoqueCTE EC ON M.REGISTRO = EC.ID_PRODUTO
and m.empresa=ec.empresa
LEFT JOIN Reservado R ON M.REGISTRO = r.ID_PRODUTO
and m.empresa=r.empresa

WHERE 
    C.SITUACAO IN ('Liberado', 'Parcial', 'Faturar','Bloqueado')
  AND C.PROGRAMADO BETWEEN ? AND ?
--  AND C.PROGRAMADO BETWEEN '01.01.2025' and '06.11.2025'
   --  c.registro=37378
--   and m.codigo='P17'
--group by 1,2,3,4,5,6,7,8,9,10,11,12,15,16,17,18
"""
    data_in_str = data_in.strftime("%d.%m.%Y")
    data_fin_str = data_fin.strftime("%d.%m.%Y")

    df = pd.read_sql(query, cnxn, params=[data_in_str, data_fin_str])
    df['DATA'] = pd.to_datetime(df['DATA']).dt.date
    return df
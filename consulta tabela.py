import pyodbc
import pandas as pd
from datetime import date

# Conexão com o banco Firebird
conn_str = (
    "DRIVER=Firebird/InterBase(r) driver;"
    "UID=CONSULTORIA;"
    "PWD=HM#2024!;"
    "DBNAME=mk.rpsolution.com.br/30509:/banco/hmrubber/hmrubber.fdb;"
    "CHARSET=UTF8;"
)

# Datas fixas de 01-06 até 13-06 do ano atual
ano_atual = date.today().year
data_in_str = f"{ano_atual}-06-01"
data_fin_str = f"{ano_atual}-06-13"

print(f"Data inicial: {data_in_str}, Data final: {data_fin_str}")

# Conexão
cnxn = pyodbc.connect(conn_str)

# Consulta SQL com filtro na coluna PROGRAMADO
query = """
WITH EstoqueCTE AS (
    SELECT
        M.REGISTRO AS ID_PRODUTO,
        M.EMPRESA,
        M.CODIGO,
        M.DESCRICAO,
        SUM(E.QUANTIDADE) AS QUANT_ESTOQUE,
        SUM(COALESCE(E.RESERVA, 0)) AS QUANT_RESERVADA_ESTOQUE
    FROM MOV_ESTOQUE E
    INNER JOIN MATERIAIS M ON M.REGISTRO = E.REG_MATERIAL
    INNER JOIN LOCAIS_ESTOQUE L ON L.REGISTRO = E.REG_ESTOQUE
    INNER JOIN EMPRESAS EMP ON EMP.REGISTRO = M.EMPRESA
    WHERE L.ESTOQUE_DISPONIVEL = 'S'
      AND L.REGISTRO IN (1,35,129)
    GROUP BY M.REGISTRO, M.EMPRESA, M.CODIGO, M.DESCRICAO
),
Reservado AS (
    SELECT 
        M.REGISTRO AS ID_PRODUTO,
        C.EMPRESA,
        MAX(C.REGISTRO) AS PEDIDO,
        SUM(I.QUANT) AS QUANT_RESERVADA
    FROM PEDIDOS C
    INNER JOIN ITEMPED I ON I.PEDIDO = C.REGISTRO
    INNER JOIN MATERIAIS M ON M.REGISTRO = I.PRODUTO
    INNER JOIN EMPRESAS EMP ON EMP.REGISTRO = C.EMPRESA
    WHERE C.SITUACAO IN ('Liberado', 'Parcial', 'Faturar', 'Bloqueado')
      AND C.PROGRAMADO BETWEEN ? AND ?
    GROUP BY M.REGISTRO, C.EMPRESA
)

SELECT 
    C.DATA,
    C.SITUACAO,
    EMP.RAZAOSOC AS EMPRESA,
    C.PROGRAMADO,
    C.REGISTRO AS ID_PEDIDO,
    V.DESCRICAO AS TIPO_MOVIMENTO,
    ((I.VALOR - COALESCE(I.DESC_VALOR, 0)) * I.QUANT) AS VALOR_LIQUIDO,
    ((I.VALOR - COALESCE(I.DESC_VALOR, 0)) * I.QUANT + COALESCE(I.VALORIPI, 0)) AS VALOR_TOTAL_COM_IPI,
    PV.RAZAOSOC AS VENDEDOR,
    E.EQUIPE,
    C.CLIENTE || ' - ' || P.RAZAOSOC AS CLIENTE
FROM PEDIDOS C
INNER JOIN ITEMPED I ON I.PEDIDO = C.REGISTRO
INNER JOIN MATERIAIS_UNIDADES U ON U.REGISTRO = I.REG_UNIDADE
INNER JOIN MATERIAIS M ON M.REGISTRO = I.PRODUTO
INNER JOIN MATERIAIS_COMPL MC ON MC.REG_MATERIAL = M.REGISTRO AND MC.REG_EMPRESA = C.EMPRESA
INNER JOIN TIPO_VENDA V ON V.REGISTRO = I.ID_TIPONOTA
INNER JOIN EMPRESAS EMP ON EMP.REGISTRO = C.EMPRESA
INNER JOIN PESSOAS P ON P.CODIGO = C.CLIENTE
INNER JOIN VENDEDORES VEN ON VEN.PESSOA = C.VENDEDOR
INNER JOIN PESSOAS PV ON PV.CODIGO = VEN.PESSOA
INNER JOIN EQUIPES E ON E.REGISTRO = VEN.EQUIPE
LEFT JOIN EstoqueCTE EC ON M.REGISTRO = EC.ID_PRODUTO AND M.EMPRESA = EC.EMPRESA
LEFT JOIN Reservado R ON M.REGISTRO = R.ID_PRODUTO AND M.EMPRESA = R.EMPRESA
WHERE C.SITUACAO IN ('Liberado', 'Parcial', 'Faturar', 'Bloqueado')
  AND C.PROGRAMADO BETWEEN ? AND ?
"""

# Executando com os 4 parâmetros necessários
params = [data_in_str, data_fin_str, data_in_str, data_fin_str]
df = pd.read_sql(query, cnxn, params=params)

# Exporta para Excel
df.to_excel("pedidos.xlsx", index=False)
print("Exportado com sucesso para 'pedidos.xlsx'")

# Fecha a conexão
cnxn.close()
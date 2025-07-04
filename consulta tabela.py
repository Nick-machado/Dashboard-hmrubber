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

# Datas fixas do mês de junho do ano atual
ano_atual = date.today().year
data_in_str = f"{ano_atual}-01-01"
data_fin_str = f"{ano_atual}-07-13"

print(f"Data inicial: {data_in_str}, Data final: {data_fin_str}")

# Conexão
cnxn = pyodbc.connect(conn_str)

# Query parametrizada com f-string
query = f"""
WITH MovrecParsed AS (
    SELECT
        numero,
        datadesc,
        SUBSTRING(numero FROM 1 FOR
            CASE
                WHEN POSITION('-' IN numero) > 0 THEN POSITION('-' IN numero) - 1
                ELSE CHAR_LENGTH(numero)
            END
        ) AS numero_base_parsed,
        CAST(SUBSTRING(numero FROM POSITION('-' IN numero) + 1 FOR CHAR_LENGTH(numero)) AS INTEGER) AS parcela_parsed
    FROM MOVREC
    WHERE datadesc >= '{ano_atual}-01-01'
),
MainData AS (
    SELECT
        m.numero,
        SUM(i.valor * i.quant) AS valor,
        n.VALORIPI,
        CAST(c.avg_comissao AS DECIMAL(10,3)) AS comissao,
        SUBSTRING(m.numero FROM 1 FOR
            CASE
                WHEN POSITION('-' IN m.numero) > 0 THEN POSITION('-' IN m.numero) - 1
                ELSE CHAR_LENGTH(m.numero)
            END
        ) AS numero_base,
        pv.razaosoc vendedor,
        e.equipe,
        m.EMPRESA,
        SUM(CAST((i.valor * i.quant) * (i.desconto / 100) AS DECIMAL(10,2))) AS desconto
    FROM MOVREC m
    INNER JOIN empresas emp ON emp.registro = m.empresa
    INNER JOIN pessoas p ON p.codigo = m.cliente
    INNER JOIN vendedores ven ON ven.pessoa = m.vendedor
    INNER JOIN pessoas pv ON pv.codigo = ven.pessoa
    INNER JOIN equipes e ON e.registro = ven.equipe
    LEFT JOIN NOTAS n ON n.REGISTRO = m.NOTA
    INNER JOIN itemnota i ON i.nota = n.REGISTRO
    INNER JOIN (
        SELECT
            m_inner.numero,
            MIN(i_inner.comissao) AS min_comissao,
            MAX(i_inner.comissao) AS max_comissao,
            AVG(i_inner.comissao) AS avg_comissao
        FROM MOVREC m_inner
        INNER JOIN NOTAS n_inner ON n_inner.REGISTRO = m_inner.NOTA
        INNER JOIN itemnota i_inner ON i_inner.nota = n_inner.REGISTRO
        WHERE m_inner.PAGAMENTO BETWEEN '{data_in_str}' AND '{data_fin_str}'
        GROUP BY m_inner.numero
    ) c ON m.numero = c.numero
    WHERE m.PAGAMENTO BETWEEN '{data_in_str}' AND '{data_fin_str}'
    GROUP BY 1, 3, 4, 5, 6, 7, 8
)
SELECT
    md.numero,
    md.valor,
    md.VALORIPI,
    MAX(mp.parcela_parsed) AS parcela,
    md.comissao,
    md.vendedor,
    md.equipe,
    md.empresa,
    md.desconto
FROM MainData md
INNER JOIN MovrecParsed mp ON md.numero_base = mp.numero_base_parsed
GROUP BY 1,2,3,5,6,7,8,9
"""

# Se quiser, pode colocar o print(query) aqui para conferir a query gerada

# Executa a query (sem parâmetros adicionais pois as datas já estão no texto)
df = pd.read_sql(query, cnxn)

# Exporta para Excel
df.to_excel("pedidos.xlsx", index=False)
print("Exportado com sucesso para 'pedidos.xlsx'")

# Fecha a conexão
cnxn.close()
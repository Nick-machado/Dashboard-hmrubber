import pyodbc
import pandas as pd
from datetime import date

conn_str = (
    "DRIVER=Firebird/InterBase(r) driver;"
    "UID=CONSULTORIA;"
    "PWD=HM#2024!;"
    "DBNAME=mk.rpsolution.com.br/30509:/banco/hmrubber/hmrubber.fdb;"
    "CHARSET=UTF8;"
)

ano_atual = date.today().year
data_in_str = f"{ano_atual}-01-01"
data_fin_str = f"{ano_atual}-07-13"

print(f"Data inicial: {data_in_str}, Data final: {data_fin_str}")

cnxn = pyodbc.connect(conn_str)

# Veja as colunas e os tipos
query_colunas_compras = "SELECT * FROM COMPRAS WHERE 1=0"
df_colunas_compras = pd.read_sql(query_colunas_compras, cnxn)
print(list(df_colunas_compras.columns))
print(df_colunas_compras.dtypes)

# Agora tente encontrar pelas colunas corretas (ajuste o nome da coluna se precisar!)
# Exemplo comum: NOTA e SERIE
query_dados_nota = "SELECT * FROM COMPRAS WHERE NOTA = 535 AND SERIE = 1"
df_nota_compras = pd.read_sql(query_dados_nota, cnxn)
print(df_nota_compras)

# (Opcional) Salva o resultado em Excel
df_nota_compras.to_excel("compras_nota_535_1.xlsx", index=False)
print("Exportado com sucesso para 'compras_nota_535_1.xlsx'")

cnxn.close()
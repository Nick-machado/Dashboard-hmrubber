import pyodbc
import pandas as pd

# Conexão com o banco Firebird
conn_str = (
    "DRIVER=Firebird/InterBase(r) driver;"
    "UID=CONSULTORIA;"
    "PWD=HM#2024!;"
    "DBNAME=mk.rpsolution.com.br/30509:/banco/hmrubber/hmrubber.fdb;"
    "CHARSET=UTF8;"
)

try:
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()

    # Consulta SQL simplificada para teste de conexão e dados
    query_test = """
    SELECT FIRST 10 * FROM NOTAS
    """

    # Executando a consulta de teste
    df_test = pd.read_sql(query_test, cnxn)
    print("Consulta de teste executada com sucesso!")
    print(f"Número de linhas retornadas: {len(df_test)}")
    if not df_test.empty:
        print("Primeiras 5 linhas:\n", df_test.head())
    else:
        print("Nenhuma linha retornada pela consulta de teste.")
    df_test.to_excel("notas_exportadas_teste.xlsx", index=False)
    print("Exportado com sucesso para \'notas_exportadas_teste.xlsx\'")

except pyodbc.Error as ex:
    sqlstate = ex.args[0]
    print(f"Erro de conexão ou execução da query: {sqlstate} - {ex.args[1]}")
except Exception as e:
    print(f"Ocorreu um erro inesperado: {e}")
finally:
    # Fechando a conexão
    if 'cnxn' in locals() and cnxn:
        if 'cursor' in locals() and cursor:
            cursor.close()
        cnxn.close()
        print("Conexão com o banco de dados fechada.")


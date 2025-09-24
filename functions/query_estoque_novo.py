# ================================
# query_estoque.py
# ================================
import pandas as pd
import os
from functions.connect import get_connection  # Importa a função correta

# Função que executa a consulta de estoque
def run_query():
    cnxn = get_connection()  # Usa a função get_connection

    query = """
SELECT
        M.REGISTRO AS ID_PRODUTO,
        m.empresa as empresa,

        M.CODIGO,
        M.DESCRICAO,
        SUM(E.QUANTIDADE) AS QUANT_ESTOQUE,
        SUM(COALESCE(E.RESERVA, 0)) AS QUANT_RESERVADA_ESTOQUE,
        SUM(E.QUANTIDADE) + COALESCE(LEAD(SUM(E.QUANTIDADE)) OVER (ORDER BY M.REGISTRO), 0) AS FISICO
    FROM MOV_ESTOQUE E
    INNER JOIN MATERIAIS M ON M.REGISTRO = E.REG_MATERIAL
    INNER JOIN LOCAIS_ESTOQUE L ON L.REGISTRO = E.REG_ESTOQUE
    inner join empresas emp on emp.registro=m.empresa
    WHERE L.ESTOQUE_DISPONIVEL = 'S'
    and l.registro in (1,35)
    and E.MODULO != 'Produção'
    GROUP BY M.REGISTRO,empresa,  M.CODIGO, M.DESCRICAO
    """
    df = pd.read_sql(query, cnxn)
    cnxn.close()
    return df

# Função para gerar e salvar Excel
def gerar_excel_estoque(nome_arquivo='estoque_consulta.xlsx'):
    """
    Executa a consulta de estoque e salva em Excel
    
    Args:
        nome_arquivo (str): Nome do arquivo Excel a ser gerado
    
    Returns:
        tuple: (DataFrame, caminho_do_arquivo)
    """
    try:
        df = run_query()
        
        # Define o caminho do arquivo na pasta consultas
        pasta_consultas = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'consultas')
        caminho_arquivo = os.path.join(pasta_consultas, nome_arquivo)
        
        # Cria a pasta se não existir
        os.makedirs(pasta_consultas, exist_ok=True)
        
        # Salva o Excel
        df.to_excel(caminho_arquivo, index=False, sheet_name='Estoque')
        
        print(f"Arquivo Excel gerado com sucesso: {caminho_arquivo}")
        print(f"Total de registros: {len(df)}")
        
        return df, caminho_arquivo
        
    except Exception as e:
        print(f"Erro ao gerar Excel: {str(e)}")
        return None, None

# Função principal para obter dados de estoque
def obter_dados_estoque():
    """
    Função principal para obter dados de estoque
    
    Returns:
        DataFrame: Dados de estoque
    """
    return run_query()

# Função para executar diretamente e gerar Excel (para testes)
if __name__ == "__main__":
    print("Executando consulta de estoque...")
    df, arquivo = gerar_excel_estoque()
    if df is not None:
        print("\nPrimeiras 5 linhas do resultado:")
        print(df.head())
        print(f"\nArquivo salvo em: {arquivo}")
    else:
        print("Erro ao executar a consulta.")

# ================================
# teste_query_estoque.py
# Script para testar a consulta de estoque
# ================================

import sys
import os

# Adiciona o diretório do projeto ao path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    import pandas as pd
    from functions.connect import get_connection
    
    def executar_consulta_estoque():
        """
        Executa a consulta de estoque e salva em Excel
        """
        print("Conectando ao banco de dados...")
        cnxn = get_connection()
        
        query = """
        SELECT
            M.REGISTRO AS ID_PRODUTO,
            M.EMPRESA AS EMPRESA,
            M.CODIGO,
            M.DESCRICAO,
            SUM(E.QUANTIDADE) AS QUANT_ESTOQUE,
            SUM(COALESCE(E.RESERVA, 0)) AS QUANT_RESERVADA_ESTOQUE,
            (SUM(E.QUANTIDADE) * 2) AS FISICO
        FROM MOV_ESTOQUE E
        INNER JOIN MATERIAIS M ON M.REGISTRO = E.REG_MATERIAL
        INNER JOIN LOCAIS_ESTOQUE L ON L.REGISTRO = E.REG_ESTOQUE
        INNER JOIN EMPRESAS EMP ON EMP.REGISTRO = M.EMPRESA
        WHERE L.ESTOQUE_DISPONIVEL = 'S'
        AND L.REGISTRO IN (1,35)
        AND E.MODULO != 'Produção'
        GROUP BY M.REGISTRO, M.EMPRESA, M.CODIGO, M.DESCRICAO
        """
        
        print("Executando consulta...")
        df = pd.read_sql(query, cnxn)
        cnxn.close()
        
        # Define o caminho do arquivo na pasta consultas
        pasta_consultas = os.path.join(project_root, 'consultas')
        nome_arquivo = 'estoque_consulta.xlsx'
        caminho_arquivo = os.path.join(pasta_consultas, nome_arquivo)
        
        # Cria a pasta se não existir
        os.makedirs(pasta_consultas, exist_ok=True)
        
        # Salva o Excel
        print("Salvando arquivo Excel...")
        df.to_excel(caminho_arquivo, index=False, sheet_name='Estoque')
        
        print(f"\n✅ Arquivo Excel gerado com sucesso!")
        print(f"📁 Localização: {caminho_arquivo}")
        print(f"📊 Total de registros: {len(df)}")
        
        if len(df) > 0:
            print(f"\n📋 Primeiras 5 linhas do resultado:")
            print(df.head().to_string())
            
            print(f"\n📈 Resumo dos dados:")
            print(f"   - Total de produtos únicos: {df['ID_PRODUTO'].nunique()}")
            print(f"   - Empresas encontradas: {df['EMPRESA'].nunique()}")
            print(f"   - Quantidade total em estoque: {df['QUANT_ESTOQUE'].sum():,.2f}")
            print(f"   - Quantidade total reservada: {df['QUANT_RESERVADA_ESTOQUE'].sum():,.2f}")
        
        return df, caminho_arquivo
    
    if __name__ == "__main__":
        print("🔍 Iniciando consulta de estoque...")
        print("=" * 50)
        
        try:
            df, arquivo = executar_consulta_estoque()
            print(f"\n✅ Processo concluído com sucesso!")
            
        except Exception as e:
            print(f"\n❌ Erro durante a execução: {str(e)}")
            import traceback
            traceback.print_exc()

except ImportError as e:
    print(f"❌ Erro de importação: {str(e)}")
    print("💡 Certifique-se de que todas as dependências estão instaladas:")
    print("   - pandas")
    print("   - openpyxl") 
    print("   - pyodbc ou firebirdsql (dependendo do banco)")

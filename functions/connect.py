import firebirdsql
import sys

def get_connection():
    """
    Estabelece conexão com o banco Firebird usando pyfirebirdsql
    """
    try:
        conn = firebirdsql.connect(
            host='mk.rpsolution.com.br',
            port=30509,
            database='/banco/hmrubber/hmrubber.fdb',
            user='CONSULTORIA',
            password='HM#2024!',
            charset='UTF8'
        )
        return conn
    except Exception as e:
        print(f"Erro na conexão com banco: {e}")
        raise

def test_connection():
    """
    Testa conectividade básica com o banco Firebird
    """
    try:
        print("Testando conexão com Firebird...")
        conn = get_connection()
        
        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_TIMESTAMP FROM RDB$DATABASE")
        result = cursor.fetchone()
        
        print(f"✅ Conexão bem-sucedida! Timestamp do servidor: {result[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
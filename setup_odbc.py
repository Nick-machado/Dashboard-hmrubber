import os
import subprocess
import sys
import streamlit as st

def setup_firebird_odbc():
    """Configura driver Firebird ODBC no Heroku"""
    
    print("🔧 Configurando Firebird ODBC...")
    
    # Verificar se já foi configurado
    if os.environ.get("FIREBIRD_ODBC_CONFIGURED"):
        print("✅ Firebird ODBC já configurado")
        return True
    
    # Criar diretório para configurações ODBC
    odbc_dir = "/app/.odbc"
    try:
        os.makedirs(odbc_dir, exist_ok=True)
        print(f"📁 Diretório ODBC criado: {odbc_dir}")
    except Exception as e:
        print(f"❌ Erro ao criar diretório ODBC: {e}")
        return False
    
    # Procurar pelo driver Firebird
    possible_drivers = [
        "/usr/lib/x86_64-linux-gnu/odbc/libOdbcFb.so",
        "/usr/lib/odbc/libOdbcFb.so", 
        "/usr/lib/x86_64-linux-gnu/libfbodbc.so",
        "/usr/lib/libfbodbc.so",
        "/usr/lib/x86_64-linux-gnu/odbc/libodbcfb.so",
        "/usr/lib/odbc/libodbcfb.so"
    ]
    
    driver_path = None
    for path in possible_drivers:
        if os.path.exists(path):
            driver_path = path
            print(f"✅ Driver encontrado: {driver_path}")
            break
    
    if not driver_path:
        print("❌ Driver Firebird não encontrado nos caminhos padrão!")
        print("🔍 Procurando drivers disponíveis...")
        
        # Procurar drivers alternativos
        try:
            # Procurar por arquivos relacionados ao Firebird
            result = subprocess.run(
                ["find", "/usr", "-name", "*firebird*", "-o", "-name", "*odbc*fb*", "-o", "-name", "*fbodbc*"], 
                capture_output=True, text=True, timeout=15
            )
            
            if result.stdout.strip():
                print("📋 Arquivos relacionados encontrados:")
                for line in result.stdout.strip().split('\n'):
                    print(f"   {line}")
                    
                # Tentar usar o primeiro arquivo .so encontrado
                for line in result.stdout.strip().split('\n'):
                    if line.endswith('.so') and ('firebird' in line.lower() or 'fb' in line.lower()):
                        driver_path = line
                        print(f"🎯 Tentando usar: {driver_path}")
                        break
            else:
                print("❌ Nenhum arquivo relacionado ao Firebird encontrado")
                
        except subprocess.TimeoutExpired:
            print("⏰ Timeout na busca por drivers")
        except Exception as e:
            print(f"❌ Erro na busca: {e}")
    
    if not driver_path:
        print("❌ Não foi possível encontrar o driver Firebird ODBC")
        print("💡 Verifique se os pacotes firebird estão no Aptfile:")
        print("   - firebird3.0-client")
        print("   - firebird3.0-client-core") 
        print("   - libfbclient2")
        print("   - odbc-firebird")
        return False
    
    # Criar odbcinst.ini
    odbcinst_content = f"""[ODBC Drivers]
Firebird/InterBase(r) driver = Installed

[Firebird/InterBase(r) driver]
Description = Firebird/InterBase(r) driver
Driver = {driver_path}
Setup = {driver_path}
FileUsage = 1
CPTimeout = 
CPReuse = 

[Firebird]
Description = Firebird ODBC Driver
Driver = {driver_path}
Setup = {driver_path}
FileUsage = 1

[FirebirdODBC]
Description = Firebird ODBC Driver Alternative
Driver = {driver_path}
Setup = {driver_path}
FileUsage = 1
"""
    
    try:
        with open(f"{odbc_dir}/odbcinst.ini", "w") as f:
            f.write(odbcinst_content)
        print(f"✅ Arquivo odbcinst.ini criado")
    except Exception as e:
        print(f"❌ Erro ao criar odbcinst.ini: {e}")
        return False
    
    # Criar odbc.ini básico
    odbc_content = """[ODBC Data Sources]
FirebirdDSN = Firebird/InterBase(r) driver

[FirebirdDSN]
Description = Firebird Database
Driver = Firebird/InterBase(r) driver
"""
    
    try:
        with open(f"{odbc_dir}/odbc.ini", "w") as f:
            f.write(odbc_content)
        print(f"✅ Arquivo odbc.ini criado")
    except Exception as e:
        print(f"❌ Erro ao criar odbc.ini: {e}")
        return False
    
    # Definir variáveis de ambiente
    os.environ["ODBCSYSINI"] = odbc_dir
    os.environ["ODBCINI"] = f"{odbc_dir}/odbc.ini"
    os.environ["FIREBIRD_ODBC_CONFIGURED"] = "1"
    
    print("✅ Variáveis de ambiente configuradas:")
    print(f"   ODBCSYSINI = {odbc_dir}")
    print(f"   ODBCINI = {odbc_dir}/odbc.ini")
    
    # Verificar configuração
    try:
        result = subprocess.run(["odbcinst", "-q", "-d"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and "Firebird" in result.stdout:
            print("✅ Driver Firebird registrado com sucesso!")
            print("📋 Drivers ODBC disponíveis:")
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    print(f"   {line}")
        else:
            print("⚠️ Driver pode não estar registrado corretamente")
            if result.stderr:
                print(f"   Erro: {result.stderr}")
    except Exception as e:
        print(f"⚠️ Não foi possível verificar registro do driver: {e}")
    
    print("✅ Configuração Firebird ODBC concluída!")
    return True

def test_firebird_connection(connection_string=None):
    """Testa conexão Firebird ODBC"""
    
    if not connection_string:
        print("⚠️ String de conexão não fornecida para teste")
        return False
    
    try:
        import pyodbc
        print("🧪 Testando conexão Firebird...")
        
        # Tentar conectar
        conn = pyodbc.connect(connection_string, timeout=30)
        print("✅ Conexão Firebird bem-sucedida!")
        
        # Testar query simples
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM RDB$DATABASE")
        result = cursor.fetchone()
        
        if result:
            print("✅ Query de teste executada com sucesso!")
            
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro na conexão Firebird: {e}")
        return False

def get_firebird_connection_template():
    """Retorna template de string de conexão para Firebird"""
    
    template = """
# Template de String de Conexão Firebird ODBC

# Opção 1: Driver por nome
DRIVER={Firebird/InterBase(r) driver};DBNAME=servidor:porta/caminho/database.fdb;UID=usuario;PWD=senha;CHARSET=UTF8;

# Opção 2: Driver alternativo
DRIVER={Firebird};DBNAME=servidor:porta/caminho/database.fdb;UID=usuario;PWD=senha;CHARSET=UTF8;

# Opção 3: DSN
DSN=FirebirdDSN;UID=usuario;PWD=senha;

# Exemplo prático:
DRIVER={Firebird/InterBase(r) driver};DBNAME=192.168.1.100:3050/var/lib/firebird/data/database.fdb;UID=SYSDBA;PWD=masterkey;CHARSET=UTF8;
"""
    
    return template

if __name__ == "__main__":
    # Executar configuração
    success = setup_firebird_odbc()
    
    if success:
        print("\n" + "="*50)
        print("🎉 Configuração concluída com sucesso!")
        print("="*50)
        print("\n📝 Template de conexão:")
        print(get_firebird_connection_template())
    else:
        print("\n" + "="*50)
        print("❌ Falha na configuração!")
        print("="*50)
        sys.exit(1)


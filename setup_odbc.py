import os
import subprocess
import sys

def setup_firebird_odbc():
    """Configura driver Firebird ODBC no Heroku Ubuntu 24.04"""
    
    print("🔧 Configurando Firebird ODBC para Ubuntu 24.04...")
    
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
    
    # Verificar se libfbclient2 está instalada
    fbclient_paths = [
        "/usr/lib/x86_64-linux-gnu/libfbclient.so.2",
        "/usr/lib/x86_64-linux-gnu/libfbclient.so",
        "/usr/lib/libfbclient.so.2",
        "/usr/lib/libfbclient.so"
    ]
    
    fbclient_path = None
    for path in fbclient_paths:
        if os.path.exists(path):
            fbclient_path = path
            print(f"✅ Biblioteca Firebird encontrada: {fbclient_path}")
            break
    
    if not fbclient_path:
        print("❌ Biblioteca libfbclient não encontrada!")
        print("🔍 Procurando bibliotecas Firebird...")
        
        try:
            result = subprocess.run(
                ["find", "/usr", "-name", "*fbclient*", "-type", "f"], 
                capture_output=True, text=True, timeout=15
            )
            
            if result.stdout.strip():
                print("📋 Bibliotecas encontradas:")
                for line in result.stdout.strip().split('\n'):
                    print(f"   {line}")
                    if line.endswith('.so') or '.so.' in line:
                        fbclient_path = line
                        print(f"🎯 Usando: {fbclient_path}")
                        break
            else:
                print("❌ Nenhuma biblioteca Firebird encontrada")
                
        except Exception as e:
            print(f"❌ Erro na busca: {e}")
    
    if not fbclient_path:
        print("❌ Não foi possível encontrar a biblioteca Firebird")
        print("💡 Verifique se o pacote libfbclient2 está no Aptfile")
        return False
    
    # Tentar baixar driver ODBC Firebird
    print("📥 Tentando baixar driver ODBC Firebird...")
    
    try:
        # URL do driver ODBC Firebird para Linux
        driver_url = "https://github.com/FirebirdSQL/firebird-odbc-driver/releases/download/v3-0-0-release/linux_libs.zip"
        
        # Criar diretório temporário
        temp_dir = "/tmp/firebird_odbc"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Download do driver
        result = subprocess.run([
            "wget", "-q", "-O", f"{temp_dir}/linux_libs.zip", driver_url
        ], timeout=60)
        
        if result.returncode == 0:
            print("✅ Driver baixado com sucesso")
            
            # Extrair
            result = subprocess.run([
                "unzip", "-q", "-o", f"{temp_dir}/linux_libs.zip", "-d", temp_dir
            ], timeout=30)
            
            if result.returncode == 0:
                print("✅ Driver extraído com sucesso")
                
                # Procurar pela biblioteca ODBC
                result = subprocess.run([
                    "find", temp_dir, "-name", "*.so", "-type", "f"
                ], capture_output=True, text=True, timeout=10)
                
                odbc_driver_path = None
                if result.stdout.strip():
                    for line in result.stdout.strip().split('\n'):
                        if 'odbc' in line.lower() or 'fb' in line.lower():
                            odbc_driver_path = line
                            break
                
                if odbc_driver_path:
                    # Copiar driver para local permanente
                    driver_dir = "/app/.heroku/odbc/lib"
                    os.makedirs(driver_dir, exist_ok=True)
                    
                    import shutil
                    final_driver_path = f"{driver_dir}/libOdbcFb.so"
                    shutil.copy2(odbc_driver_path, final_driver_path)
                    
                    print(f"✅ Driver ODBC copiado para: {final_driver_path}")
                    
                    # Usar o driver baixado
                    driver_path = final_driver_path
                else:
                    print("⚠️ Driver ODBC não encontrado no arquivo baixado")
                    # Fallback para biblioteca cliente
                    driver_path = fbclient_path
            else:
                print("⚠️ Falha ao extrair driver")
                driver_path = fbclient_path
        else:
            print("⚠️ Falha no download do driver")
            driver_path = fbclient_path
            
    except Exception as e:
        print(f"⚠️ Erro no download do driver: {e}")
        driver_path = fbclient_path
    
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
    
    # Adicionar ao LD_LIBRARY_PATH se necessário
    if "/app/.heroku/odbc/lib" not in os.environ.get("LD_LIBRARY_PATH", ""):
        current_path = os.environ.get("LD_LIBRARY_PATH", "")
        new_path = "/app/.heroku/odbc/lib" + (":" + current_path if current_path else "")
        os.environ["LD_LIBRARY_PATH"] = new_path
    
    print("✅ Variáveis de ambiente configuradas:")
    print(f"   ODBCSYSINI = {odbc_dir}")
    print(f"   ODBCINI = {odbc_dir}/odbc.ini")
    print(f"   LD_LIBRARY_PATH = {os.environ.get('LD_LIBRARY_PATH', '')}")
    
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

def get_firebird_connection_template():
    """Retorna template de string de conexão para Firebird"""
    
    template = """
# Template de String de Conexão Firebird ODBC - Ubuntu 24.04

# Opção 1: Driver por nome (recomendado)
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
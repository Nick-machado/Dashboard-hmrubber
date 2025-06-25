import os
import subprocess
import sys

def setup_firebird_odbc():
    """Configura driver Firebird ODBC no Heroku Ubuntu 24.04 - Versão Melhorada"""
    
    print("🔧 Configurando Firebird ODBC para Ubuntu 24.04 (Versão Melhorada)...")
    
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
    
    # Verificar se pacotes foram instalados
    print("🔍 Verificando instalação de pacotes...")
    
    try:
        # Verificar se libfbclient2 foi instalado
        result = subprocess.run(["dpkg", "-l", "libfbclient2"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Pacote libfbclient2 está instalado")
        else:
            print("❌ Pacote libfbclient2 NÃO está instalado")
            
        # Verificar firebird-dev
        result = subprocess.run(["dpkg", "-l", "firebird-dev"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Pacote firebird-dev está instalado")
        else:
            print("❌ Pacote firebird-dev NÃO está instalado")
            
    except Exception as e:
        print(f"⚠️ Erro ao verificar pacotes: {e}")
    
    # Lista expandida de possíveis localizações da biblioteca
    fbclient_paths = [
        # Firebird 3.0 (Ubuntu 24.04)
        "/usr/lib/x86_64-linux-gnu/libfbclient.so.3",
        "/usr/lib/x86_64-linux-gnu/libfbclient.so",
        
        # Firebird 2.5 (compatibilidade)
        "/usr/lib/x86_64-linux-gnu/libfbclient.so.2",
        
        # Locais alternativos
        "/usr/lib/libfbclient.so.3",
        "/usr/lib/libfbclient.so.2",
        "/usr/lib/libfbclient.so",
        
        # Locais específicos do Firebird
        "/usr/lib/firebird/3.0/lib/libfbclient.so",
        "/usr/lib/firebird/lib/libfbclient.so",
    ]
    
    fbclient_path = None
    print("🔍 Procurando biblioteca libfbclient...")
    
    for path in fbclient_paths:
        if os.path.exists(path):
            fbclient_path = path
            print(f"✅ Biblioteca Firebird encontrada: {fbclient_path}")
            break
        else:
            print(f"   ❌ Não encontrada: {path}")
    
    if not fbclient_path:
        print("❌ Biblioteca libfbclient não encontrada nos locais padrão!")
        print("🔍 Executando busca abrangente...")
        
        try:
            # Busca mais abrangente
            search_commands = [
                ["find", "/usr", "-name", "*fbclient*", "-type", "f"],
                ["find", "/lib", "-name", "*fbclient*", "-type", "f"],
                ["locate", "libfbclient"],
                ["dpkg", "-L", "libfbclient2"]
            ]
            
            for cmd in search_commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        print(f"📋 Resultado de '{' '.join(cmd)}':")
                        for line in result.stdout.strip().split('\n'):
                            print(f"   {line}")
                            if line.endswith('.so') or '.so.' in line:
                                if not fbclient_path:  # Usar o primeiro encontrado
                                    fbclient_path = line
                                    print(f"🎯 Usando: {fbclient_path}")
                except:
                    continue
                    
        except Exception as e:
            print(f"❌ Erro na busca abrangente: {e}")
    
    if not fbclient_path:
        print("❌ Não foi possível encontrar a biblioteca Firebird")
        print("💡 Tentando download direto do driver ODBC...")
        
        # Tentar download direto como fallback
        fbclient_path = download_firebird_driver()
        
        if not fbclient_path:
            print("❌ Todas as tentativas falharam")
            print("💡 Verifique se o pacote libfbclient2 está no Aptfile:")
            print("   unixodbc")
            print("   unixodbc-dev")
            print("   libfbclient2")
            print("   firebird-dev")
            print("   firebird3.0-common")
            return False
    
    # Configurar ODBC com a biblioteca encontrada
    return configure_odbc_driver(fbclient_path, odbc_dir)

def download_firebird_driver():
    """Baixa driver ODBC Firebird diretamente do GitHub"""
    
    print("📥 Baixando driver ODBC Firebird do GitHub...")
    
    try:
        # Criar diretório temporário
        temp_dir = "/tmp/firebird_odbc"
        os.makedirs(temp_dir, exist_ok=True)
        
        # URL do driver ODBC Firebird para Linux
        driver_url = "https://github.com/FirebirdSQL/firebird-odbc-driver/releases/download/v3-0-0-release/linux_libs.zip"
        
        # Verificar se wget está disponível
        result = subprocess.run(["which", "wget"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ wget não está disponível")
            return None
        
        # Download do driver
        print("📥 Fazendo download...")
        result = subprocess.run([
            "wget", "-q", "--timeout=60", "-O", f"{temp_dir}/linux_libs.zip", driver_url
        ], timeout=120)
        
        if result.returncode == 0:
            print("✅ Driver baixado com sucesso")
            
            # Verificar se unzip está disponível
            result = subprocess.run(["which", "unzip"], capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ unzip não está disponível")
                return None
            
            # Extrair
            print("📦 Extraindo driver...")
            result = subprocess.run([
                "unzip", "-q", "-o", f"{temp_dir}/linux_libs.zip", "-d", temp_dir
            ], timeout=30)
            
            if result.returncode == 0:
                print("✅ Driver extraído com sucesso")
                
                # Procurar pela biblioteca ODBC
                result = subprocess.run([
                    "find", temp_dir, "-name", "*.so", "-type", "f"
                ], capture_output=True, text=True, timeout=10)
                
                if result.stdout.strip():
                    print("📋 Bibliotecas encontradas no download:")
                    for line in result.stdout.strip().split('\n'):
                        print(f"   {line}")
                        
                    # Procurar especificamente pelo driver ODBC
                    for line in result.stdout.strip().split('\n'):
                        if any(keyword in line.lower() for keyword in ['odbc', 'odbcfb', 'firebird']):
                            # Copiar driver para local permanente
                            driver_dir = "/app/.heroku/odbc/lib"
                            os.makedirs(driver_dir, exist_ok=True)
                            
                            import shutil
                            final_driver_path = f"{driver_dir}/libOdbcFb.so"
                            shutil.copy2(line, final_driver_path)
                            
                            print(f"✅ Driver ODBC copiado para: {final_driver_path}")
                            return final_driver_path
                
                print("⚠️ Driver ODBC específico não encontrado, usando primeira biblioteca")
                # Usar qualquer biblioteca .so encontrada como fallback
                for line in result.stdout.strip().split('\n'):
                    if line.endswith('.so'):
                        return line
            else:
                print("❌ Falha ao extrair driver")
        else:
            print("❌ Falha no download do driver")
            
    except Exception as e:
        print(f"❌ Erro no download do driver: {e}")
    
    return None

def configure_odbc_driver(driver_path, odbc_dir):
    """Configura o driver ODBC com o caminho especificado"""
    
    print(f"⚙️ Configurando ODBC com driver: {driver_path}")
    
    # Criar odbcinst.ini com múltiplas opções
    odbcinst_content = f"""[ODBC Drivers]
Firebird/InterBase(r) driver = Installed
Firebird = Installed
FirebirdODBC = Installed

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
    driver_dir = os.path.dirname(driver_path)
    if driver_dir not in os.environ.get("LD_LIBRARY_PATH", ""):
        current_path = os.environ.get("LD_LIBRARY_PATH", "")
        new_path = driver_dir + (":" + current_path if current_path else "")
        os.environ["LD_LIBRARY_PATH"] = new_path
    
    print("✅ Variáveis de ambiente configuradas:")
    print(f"   ODBCSYSINI = {odbc_dir}")
    print(f"   ODBCINI = {odbc_dir}/odbc.ini")
    print(f"   LD_LIBRARY_PATH = {os.environ.get('LD_LIBRARY_PATH', '')}")
    
    # Verificar configuração
    try:
        result = subprocess.run(["odbcinst", "-q", "-d"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Verificação ODBC:")
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    print(f"   {line}")
                    
            if "Firebird" in result.stdout:
                print("✅ Driver Firebird registrado com sucesso!")
            else:
                print("⚠️ Driver Firebird pode não estar registrado corretamente")
        else:
            print("⚠️ Não foi possível verificar drivers ODBC")
            if result.stderr:
                print(f"   Erro: {result.stderr}")
    except Exception as e:
        print(f"⚠️ Erro na verificação ODBC: {e}")
    
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
# Dockerfile Corrigido para Dashboard-hmrubber
# Resolve conflitos de pacotes ODBC

FROM python:3.10-slim

# Definir diretório de trabalho
WORKDIR /app

# Definir variáveis de ambiente para evitar prompts interativos
ENV DEBIAN_FRONTEND=noninteractive
ENV ACCEPT_EULA=Y

# Atualizar sistema e instalar dependências básicas
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    ca-certificates \
    apt-transport-https \
    lsb-release && \
    rm -rf /var/lib/apt/lists/*

# Adicionar chave e repositório Microsoft
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg && \
    echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list

# Atualizar lista de pacotes
RUN apt-get update

# Remover pacotes ODBC conflitantes se existirem
RUN apt-get remove -y --purge libodbc2 libodbcinst2 unixodbc-common || true

# Instalar Microsoft ODBC Driver 18 e dependências
RUN apt-get install -y --no-install-recommends \
    msodbcsql18 \
    unixodbc-dev \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

# Verificar instalação do driver
RUN odbcinst -q -d -n "ODBC Driver 18 for SQL Server"

# Atualizar pip
RUN pip install --upgrade pip

# Copiar requirements.txt primeiro (para cache do Docker )
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Expor porta que o Streamlit usa
EXPOSE 8501

# Comando para executar a aplicação
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]

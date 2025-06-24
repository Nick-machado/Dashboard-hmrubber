# Dockerfile Corrigido para Dashboard-hmrubber
# Configurado para SQL Server com Microsoft ODBC Driver 18

# Usar Python 3.10 slim baseado em Debian 11
FROM python:3.10-slim

# Definir diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    apt-utils \
    gnupg2 \
    unixodbc-dev && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --upgrade pip

# Adicionar repositório Microsoft para ODBC Driver
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list

# Atualizar lista de pacotes
RUN apt-get update

# Instalar Microsoft ODBC Driver 18 for SQL Server
RUN env ACCEPT_EULA=Y apt-get install -y msodbcsql18

# Verificar instalação do driver
RUN odbcinst -q -d -n "ODBC Driver 18 for SQL Server"

# Copiar requirements.txt primeiro (para cache do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Expor porta que o Streamlit usa
EXPOSE 8501

# Comando para executar a aplicação
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]


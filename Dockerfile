
# Imagem base
FROM python:3.10-slim

# Instala dependências do sistema
RUN apt-get update && \
    apt-get install -y unixodbc unixodbc-dev libfirebird-dev firebird-dev firebird3.0-utils libfbclient2 && \
    apt-get clean

# Define diretório de trabalho
WORKDIR /app

# Copia os arquivos do projeto
COPY . /app

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Expõe a porta padrão do Streamlit
EXPOSE 8501

# Comando para rodar o Streamlit
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]

#!/usr/bin/env bash

# Script de configuração ODBC para SQL Server
# Dashboard-hmrubber - Versão corrigida

echo "=== Configurando Microsoft ODBC Driver 18 for SQL Server ==="

# Configurar Microsoft ODBC Driver 18 for SQL Server
echo "[ODBC Driver 18 for SQL Server]" >> /etc/odbcinst.ini
echo "Description=Microsoft ODBC Driver 18 for SQL Server" >> /etc/odbcinst.ini
echo "Driver=/opt/microsoft/msodbcsql18/lib64/libmsodbcsql-18.3.so.1.1" >> /etc/odbcinst.ini
echo "UsageCount=1" >> /etc/odbcinst.ini

echo "Configuração ODBC adicionada com sucesso!"

# Verificar configuração
echo ""
echo "=== Verificando drivers ODBC instalados ==="
odbcinst -q -d

echo ""
echo "=== Verificando driver específico do SQL Server ==="
odbcinst -q -d -n "ODBC Driver 18 for SQL Server"

echo ""
echo "=== Configuração ODBC concluída com sucesso! ==="


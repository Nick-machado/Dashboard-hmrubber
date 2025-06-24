#!/usr/bin/env bash
apt-get update
apt-get install -y unixodbc unixodbc-dev libfirebird-dev firebird-dev firebird3.0-utils libfbclient2

# Verificar se o driver foi instalado
odbcinst -j

#!/usr/bin/env bash

echo "[Firebird]" >> /etc/odbcinst.ini
echo "Description=Firebird ODBC driver" >> /etc/odbcinst.ini
echo "Driver=/usr/lib/x86_64-linux-gnu/libOdbcFb.so" >> /etc/odbcinst.ini
echo "Setup=/usr/lib/x86_64-linux-gnu/libOdbcFb.so" >> /etc/odbcinst.ini
echo "FileUsage=1" >> /etc/odbcinst.ini
echo "CPTimeout=60" >> /etc/odbcinst.ini
echo "CPReuse=1" >> /etc/odbcinst.ini

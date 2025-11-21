@echo off
REM Script para gerar relatórios de produção
REM Este script deve estar registrado no PATH do sistema

REM Muda para o diretório raiz do projeto
cd /d "C:\Users\vm.script\Desktop\Projetos\Gerador-de-relatorios"

REM Executa o módulo Python a partir da raiz do projeto
python -m relatorios.producaoPrimaria.producaoPrimariaContadorAutomatico %*

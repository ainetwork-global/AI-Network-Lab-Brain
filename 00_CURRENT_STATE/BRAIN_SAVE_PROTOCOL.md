# BRAIN SAVE PROTOCOL

## Local do repositorio

C:\Users\AP10\AI-Network-Lab-Brain

ou:

$env:USERPROFILE\AI-Network-Lab-Brain

## Pasta correta para estados

00_CURRENT_STATE

## Regra obrigatoria

Antes de salvar qualquer arquivo no Brain, verificar a estrutura real:

Get-ChildItem -Directory

Nunca assumir 90_CURRENT_STATE ou CURRENT_STATE sem validar.

## Metodo preferido

Criar arquivos via PowerShell com Set-Content:

Set-Content ".\00_CURRENT_STATE\nome-do-arquivo.md" -Encoding UTF8

## Publicacao

git add .
git commit -m "Brain update"
git push origin main

## Verificacao

git status

Resultado esperado:

nothing to commit, working tree clean

## Preferencias do Gilson

- PowerShell
- Um comando por vez
- Arquivos completos
- Caminho local: C:\Users\AP10\AI-Network-Lab-Brain
- Pasta padrao: 00_CURRENT_STATE

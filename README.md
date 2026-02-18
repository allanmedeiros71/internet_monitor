# Monitor de Internet

Dashboard em tempo real para monitoramento de conexão de internet, com detecção automática de quedas e registro histórico.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Dash](https://img.shields.io/badge/Dash-Plotly-green) ![SQLite](https://img.shields.io/badge/SQLite-Database-lightgrey)

## Funcionalidades

- **Monitoramento contínuo** via ping (Google DNS 8.8.8.8 + Cloudflare 1.1.1.1 como fallback)
- **Dashboard web** com atualização automática a cada 5 segundos
- **Gráfico de latência** com marcação visual de quedas
- **Filtro por período** — última hora, 24h, semana, mês ou todos os dados
- **Detecção inteligente de quedas** — agrupa falhas consecutivas e calcula duração
- **Tabela detalhada** com as últimas 50 quedas registradas
- **Armazenamento local** em SQLite para histórico persistente

## Requisitos

- Python 3.10+
- Dependências:

```
dash
pandas
plotly
```

## Instalação

```bash
git clone https://github.com/allanmedeiros71/internet_monitor.git
cd internet_monitor
python -m venv .venv
source .venv/bin/activate
pip install dash pandas plotly
```

## Uso

```bash
python internet_monitor.py
```

Acesse o dashboard em: **http://127.0.0.1:8050**

## Como funciona

1. Uma thread em background executa pings a cada 1 segundo
2. Se o alvo principal (8.8.8.8) falhar, testa o secundário (1.1.1.1) para confirmar a queda
3. Os resultados são gravados em `internet_log.db` (SQLite)
4. O dashboard Dash lê o banco e atualiza o gráfico e as métricas em tempo real

## Screenshot

O dashboard exibe:
- **Status atual** — latência em ms ou OFFLINE
- **Última queda** — timestamp da queda mais recente
- **Total de quedas** — contagem no período selecionado
- **Gráfico interativo** — histórico de latência com marcadores de falha
- **Tabela de quedas** — início, fim, duração e tipo de cada evento

## Licença

Este projeto é de uso livre.

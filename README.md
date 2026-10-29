# internet_monitor

A real-time dashboard that watches your internet connection, detects
outages and keeps a history you can show to your ISP.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Dash](https://img.shields.io/badge/Dash-Plotly-green) ![SQLite](https://img.shields.io/badge/SQLite-local-lightgrey)

## Features

- Pings every second, with Google DNS (8.8.8.8) as the main target and
  Cloudflare (1.1.1.1) as a fallback, so one slow host is not counted as an
  outage.
- Groups consecutive failures into a single outage with start, end and
  duration.
- Web dashboard that refreshes every 5 seconds: current latency, last outage,
  outage count and a latency chart with failures marked.
- Filters for the last hour, 24 hours, week, month or everything.
- Table of the latest 50 outages.
- History stored locally in SQLite (`internet_log.db`).

## Run

```bash
git clone https://github.com/allanmedeiros71/internet_monitor.git
cd internet_monitor
python -m venv .venv && source .venv/bin/activate
pip install dash pandas plotly
python internet_monitor.py
```

Open <http://127.0.0.1:8050>.

## How it works

A background thread pings the targets and writes each result to SQLite. The
Dash app reads the database on every refresh and redraws the metrics, chart
and outage table.

## License

Free to use.

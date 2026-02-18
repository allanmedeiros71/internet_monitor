import subprocess
import platform
import time
import sqlite3
import threading
import datetime
import sys
import pandas as pd
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import plotly.express as px

# --- CONFIGURAÇÕES ---
DB_FILE = "internet_log.db"
TARGETS = ["8.8.8.8", "1.1.1.1"]  # Google e Cloudflare
PING_INTERVAL = 1.0  # Segundos entre testes (Alta frequência para pegar micro-quedas)
TIMEOUT = 1000  # Milissegundos para considerar timeout

# --- BACKEND: Monitoramento e Banco de Dados ---

def init_db():
    """Inicializa o banco de dados SQLite."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS pings
                 (timestamp TEXT, target TEXT, latency REAL, status TEXT)''')
    conn.commit()
    conn.close()

def ping_host(host):
    """Executa o comando ping compatível com SO (Windows/Linux/Mac)."""
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    timeout_param = '-w' if platform.system().lower() == 'windows' else '-W'
    
    # Ajuste de timeout (Windows usa ms, Linux/Mac usa s)
    timeout_val = str(TIMEOUT) if platform.system().lower() == 'windows' else str(TIMEOUT/1000)
    
    command = ['ping', param, '1', timeout_param, timeout_val, host]
    
    try:
        # Executa o ping e captura a saída
        start_time = time.time()
        output = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        end_time = time.time()
        
        duration = (end_time - start_time) * 1000 # ms
        
        if output.returncode == 0:
            return duration, "OK"
        else:
            return None, "TIMEOUT"
    except Exception as e:
        return None, "ERROR"

def monitor_loop():
    """Loop infinito que roda em uma thread separada monitorando a conexão."""
    print(f"📡 Iniciando monitoramento em: {TARGETS}")
    print(f"💾 Salvando dados em: {DB_FILE}")
    
    init_db()
    
    while True:
        timestamp = datetime.datetime.now().isoformat()
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        all_failed = True
        
        # Testamos o primeiro alvo principal
        target = TARGETS[0]
        latency, status = ping_host(target)
        
        # Se falhar, tentamos o secundário para confirmar se é a internet ou o DNS do Google
        if status != "OK":
            target_backup = TARGETS[1]
            lat_bkp, stat_bkp = ping_host(target_backup)
            if stat_bkp == "OK":
                # Internet funciona, foi só o alvo 1
                status = "OK"
                latency = lat_bkp
                target = target_backup
        
        # Grava no banco
        c.execute("INSERT INTO pings (timestamp, target, latency, status) VALUES (?, ?, ?, ?)",
                  (timestamp, target, latency if latency else 0, status))
        
        conn.commit()
        conn.close()
        
        if status != "OK":
            print(f"[{timestamp[11:19]}] ❌ Queda detectada!")
        
        time.sleep(PING_INTERVAL)

# --- FRONTEND: Dashboard Dash ---

app = dash.Dash(__name__, title="Monitor de Internet")

app.layout = html.Div([
    html.Div([
        html.H1("Monitoramento de Conexão", style={'textAlign': 'center', 'color': '#2c3e50'}),
        html.P("Relatório de estabilidade para provedor de acesso.", style={'textAlign': 'center'}),
    ], style={'padding': '20px', 'backgroundColor': '#ecf0f1'}),

    html.Div([
        html.Div([
            html.H3("Status Atual"),
            html.Div(id='live-status', style={'fontSize': '24px', 'fontWeight': 'bold'})
        ], style={'width': '30%', 'display': 'inline-block', 'textAlign': 'center', 'padding': '20px'}),
        
        html.Div([
            html.H3("Última Queda"),
            html.Div(id='last-drop', style={'fontSize': '20px', 'color': '#e74c3c'})
        ], style={'width': '30%', 'display': 'inline-block', 'textAlign': 'center', 'padding': '20px'}),
        
        html.Div([
            html.H3("Total de Quedas (período)"),
            html.Div(id='total-drops', style={'fontSize': '24px'})
        ], style={'width': '30%', 'display': 'inline-block', 'textAlign': 'center', 'padding': '20px'}),
    ]),

    html.Div([
        html.Label('Período:', style={'fontWeight': 'bold', 'marginRight': '10px'}),
        dcc.Dropdown(
            id='time-range',
            options=[
                {'label': 'Última Hora', 'value': '1h'},
                {'label': 'Últimas 24h', 'value': '24h'},
                {'label': 'Última Semana', 'value': '7d'},
                {'label': 'Último Mês', 'value': '30d'},
                {'label': 'Todos os Dados', 'value': 'all'},
            ],
            value='24h',
            clearable=False,
            style={'width': '200px', 'display': 'inline-block', 'verticalAlign': 'middle'}
        ),
    ], style={'padding': '10px 20px', 'display': 'flex', 'alignItems': 'center'}),

    dcc.Graph(id='latency-graph'),

    html.H3("Registro Detalhado de Quedas (Últimas 50)", style={'marginTop': '30px', 'marginLeft': '20px'}),
    html.Div(id='outage-table-container', style={'padding': '20px'}),

    # Atualiza a cada 5 segundos
    dcc.Interval(
        id='interval-component',
        interval=5*1000, 
        n_intervals=0
    )
], style={'fontFamily': 'Arial, sans-serif'})

@app.callback(
    [Output('latency-graph', 'figure'),
     Output('live-status', 'children'),
     Output('live-status', 'style'),
     Output('last-drop', 'children'),
     Output('total-drops', 'children'),
     Output('outage-table-container', 'children')],
    [Input('interval-component', 'n_intervals'),
     Input('time-range', 'value')]
)
def update_metrics(n, time_range):
    conn = sqlite3.connect(DB_FILE)

    if time_range == 'all':
        df = pd.read_sql_query("SELECT * FROM pings ORDER BY timestamp DESC", conn)
    else:
        range_map = {'1h': 1, '24h': 24, '7d': 168, '30d': 720}
        hours = range_map.get(time_range, 24)
        cutoff = (datetime.datetime.now() - datetime.timedelta(hours=hours)).isoformat()
        df = pd.read_sql_query(
            "SELECT * FROM pings WHERE timestamp >= ? ORDER BY timestamp DESC",
            conn, params=(cutoff,)
        )

    conn.close()

    if df.empty:
        return go.Figure(), "Sem dados", {}, "-", "0", "Sem dados"

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')

    # --- Análise de Quedas ---
    # Identificar blocos de falhas consecutivas
    df['is_failure'] = df['status'] != 'OK'
    # Agrupa falhas consecutivas criando um ID de grupo
    df['group'] = (df['is_failure'] != df['is_failure'].shift()).cumsum()
    
    outages = []
    failure_groups = df[df['is_failure']].groupby('group')
    
    for _, group in failure_groups:
        start = group['timestamp'].min()
        end = group['timestamp'].max()
        duration = (end - start).total_seconds() + PING_INTERVAL # Adiciona o intervalo base
        if duration >= 1: # Filtra glitches minúsculos se necessário
            outages.append({
                'Início': start.strftime('%d/%m %H:%M:%S'),
                'Fim': end.strftime('%H:%M:%S'),
                'Duração (s)': round(duration, 1),
                'Tipo': 'Timeout/Perda de Pacote'
            })
    
    if outages:
        outages_df = pd.DataFrame(outages).sort_values('Início', ascending=False)
    else:
        outages_df = pd.DataFrame(columns=['Início', 'Fim', 'Duração (s)', 'Tipo'])

    # --- Gráfico ---
    fig = go.Figure()

    # Linha de Latência
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['latency'],
        mode='lines',
        name='Latência (ms)',
        line=dict(color='#3498db', width=1),
        connectgaps=False # Não conecta pontos se houver buraco (falha)
    ))

    # Marcar falhas no gráfico com linhas vermelhas verticais
    failures = df[df['status'] != 'OK']
    fig.add_trace(go.Scatter(
        x=failures['timestamp'],
        y=[0] * len(failures), # Plota no zero
        mode='markers',
        name='Perda de Pacote',
        marker=dict(color='red', size=8, symbol='x')
    ))

    fig.update_layout(
        title='Histórico de Latência e Estabilidade',
        xaxis_title='Horário',
        yaxis_title='Latência (ms)',
        template='plotly_white',
        height=400,
        margin=dict(l=40, r=40, t=40, b=40)
    )

    # --- Cards de Status ---
    last_ping = df.iloc[-1]
    is_online = last_ping['status'] == 'OK'
    
    status_text = f"{last_ping['latency']:.1f} ms" if is_online else "OFFLINE"
    status_style = {'color': '#27ae60'} if is_online else {'color': '#c0392b'}
    
    last_drop_text = outages_df.iloc[0]['Início'] if not outages_df.empty else "Nenhuma registrada"
    total_drops_text = str(len(outages_df))

    # --- Tabela ---
    if not outages_df.empty:
        table = dash_table.DataTable(
            data=outages_df.head(50).to_dict('records'),
            columns=[{'name': i, 'id': i} for i in outages_df.columns],
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_header={'backgroundColor': 'white', 'fontWeight': 'bold'},
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}
            ]
        )
    else:
        table = html.Div("Nenhuma queda registrada no período.")

    return fig, status_text, status_style, last_drop_text, total_drops_text, table

# --- EXECUÇÃO ---

if __name__ == '__main__':
    # Inicia a thread de monitoramento (daemon para fechar quando o app fechar)
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    
    print("\n🚀 Servidor do Dashboard rodando!")
    print("👉 Acesse no navegador: http://127.0.0.1:8050")
    print("Pressione Ctrl+C no terminal para encerrar.\n")
    
    # Inicia o servidor do Dashboard
    # debug=False é importante quando usando threads
    app.run(debug=False, port=8050)
    
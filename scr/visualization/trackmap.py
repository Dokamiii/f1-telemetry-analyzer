import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import fastf1
import os

# --- 1. Configuração do Cache do FastF1 ---
if not os.path.exists('cache'):
    os.makedirs('cache')
fastf1.Cache.enable_cache('cache')

# --- 2. Obter Telemetria Real da Fórmula 1 ---
def obter_telemetria(ano, gp, tipo_sessao='R'):
    print(f"Carregando dados: {ano} {gp}...")
    sessao = fastf1.get_session(ano, gp, tipo_sessao)
    sessao.load(telemetry=True, weather=False, messages=False)
    
    # Pega a volta mais rápida da corrida
    volta_rapida = sessao.laps.pick_fastest()
    tel = volta_rapida.get_telemetry()
    
    # Adiciona info do piloto para as legendas
    tel['Driver'] = volta_rapida['Driver']
    return tel

# AGORA SIM: Baixamos os dados primeiro!
tel_ref = obter_telemetria(2018, 'Brazil', 'R')  # Vermelho (Referência - Bottas)
tel_cur = obter_telemetria(2024, 'Brazil', 'R')  # Azul (Atual - 2024)

# --- 3. Gerar Bordas da Pista via Telemetria ---
def gerar_bordas_pista(telemetria, largura_metros=8.0):
    """Gera limites de pista perfeitos baseados na volta do FastF1"""
    x = telemetria['X'].values
    y = telemetria['Y'].values
    
    # Calcula os vetores de direção do carro
    dx = np.gradient(x)
    dy = np.gradient(y)
    
    # Calcula o vetor perpendicular (normal)
    norm = np.sqrt(dx**2 + dy**2)
    norm[norm == 0] = 1 # Evita divisão por zero
    
    nx = -dy / norm
    ny = dx / norm
    
    # Expande para a esquerda e direita
    left_x = x + nx * largura_metros
    left_y = y + ny * largura_metros
    right_x = x - nx * largura_metros
    right_y = y - ny * largura_metros
    
    return left_x, left_y, right_x, right_y

# Agora podemos usar tel_ref com segurança para gerar as bordas
left_x, left_y, right_x, right_y = gerar_bordas_pista(tel_ref, largura_metros=8.0)

# --- 4. Inicialização do Dashboard Dash ---
app = dash.Dash(__name__)

# Encontra a distância máxima para configurar o controle deslizante
max_dist = int(max(tel_ref['Distance'].max(), tel_cur['Distance'].max()))

app.layout = html.Div([
    html.H1("🏎️ Sistema de Telemetria F1 (Estilo RaceStudio)", 
            style={'textAlign': 'center', 'color': '#f4f4f4', 'fontFamily': 'Arial'}),
    
    # Slider de Distância (Sincronização principal)
    html.Div([
        html.Label("Posição na Pista (Distância em Metros):", style={'color': 'white', 'fontWeight': 'bold'}),
        dcc.Slider(
            id='distance-slider',
            min=0, max=max_dist, step=5, value=0,
            marks={i: f'{i}m' for i in range(0, max_dist, 500)},
            tooltip={"placement": "bottom", "always_visible": True}
        )
    ], style={'padding': '20px', 'backgroundColor': '#2a2a2a', 'borderRadius': '10px', 'marginBottom': '20px'}),

    # Container flexível para Mapa e Gráficos lado a lado
    html.Div([
        # ESQUERDA: Mapa da Pista
        html.Div([dcc.Graph(id='track-map', style={'height': '800px'})], 
                 style={'width': '40%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        
        # DIREITA: Gráficos de Telemetria
        html.Div([dcc.Graph(id='telemetry-graphs')], 
                 style={'width': '60%', 'display': 'inline-block', 'verticalAlign': 'top'})
    ])
], style={'backgroundColor': '#121212', 'padding': '20px'})

# --- 5. Lógica de Atualização Sincronizada ---
@app.callback(
    [Output('track-map', 'figure'),
     Output('telemetry-graphs', 'figure')],
    [Input('distance-slider', 'value')]
)
def update_dashboard(current_distance):
    # Encontra o índice de telemetria mais próximo da distância atual do slider
    idx_ref = (tel_ref['Distance'] - current_distance).abs().idxmin()
    idx_cur = (tel_cur['Distance'] - current_distance).abs().idxmin()

    # ==========================================
    # 5.1 MAPA DA PISTA (X / Y)
    # ==========================================
    fig_map = go.Figure()

    # Desenha as bordas da pista perfeitamente alinhadas (Cor cinza estilo asfalto)
    fig_map.add_trace(go.Scatter(x=left_x, y=left_y, mode='lines', line=dict(color='#666666', width=2), name='Limite Pista Esq.'))
    fig_map.add_trace(go.Scatter(x=right_x, y=right_y, mode='lines', line=dict(color='#666666', width=2), name='Limite Pista Dir.'))

    # Desenha as Racing Lines (Trajetórias da F1)
    fig_map.add_trace(go.Scatter(x=tel_ref['X'], y=tel_ref['Y'], mode='lines', line=dict(color='red', width=1.5), name=f"Ref ({tel_ref['Driver'].iloc[0]})"))
    fig_map.add_trace(go.Scatter(x=tel_cur['X'], y=tel_cur['Y'], mode='lines', line=dict(color='cyan', width=1.5), name=f"Atual ({tel_cur['Driver'].iloc[0]})"))

    # Marcadores dinâmicos dos Carros
    fig_map.add_trace(go.Scatter(
        x=[tel_ref['X'].iloc[idx_ref], tel_cur['X'].iloc[idx_cur]],
        y=[tel_ref['Y'].iloc[idx_ref], tel_cur['Y'].iloc[idx_cur]],
        mode='markers',
        marker=dict(size=14, color=['red', 'cyan'], line=dict(color='white', width=2)),
        name='Posição (Cursor)'
    ))

    # Configuração do Layout do Mapa
    fig_map.update_layout(
        title="Traçado de Interlagos (Alinhamento Automático)",
        plot_bgcolor='#1e1e1e', paper_bgcolor='#121212', font=dict(color='white'),
        # IMPORTANTE: scaleanchor garante que a pista não fique distorcida/esticada
        xaxis=dict(showgrid=False, zeroline=False, scaleanchor="y", scaleratio=1, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0.5)")
    )

    # ==========================================
    # 5.2 GRÁFICOS DE TELEMETRIA
    # ==========================================
    fig_graphs = make_subplots(
        rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04, 
        subplot_titles=("Velocidade (km/h)", "Acelerador (Throttle %)", "Freio (Brake)", "RPM (Motor)")
    )

    metrics = ['Speed', 'Throttle', 'Brake', 'RPM']
    colors = {'Ref': 'red', 'Cur': 'cyan'}
    dataframes = {'Ref': tel_ref, 'Cur': tel_cur}

    for i, metric in enumerate(metrics):
        for name, df in dataframes.items():
            fig_graphs.add_trace(go.Scatter(
                x=df['Distance'], y=df[metric], mode='lines', 
                line=dict(color=colors[name], width=1.5), 
                name=f"{name} ({df['Driver'].iloc[0]})" if i == 0 else "",
                showlegend=(i==0) # Mostra legenda apenas no topo
            ), row=i+1, col=1)

        # Linha Vertical (Cursor de Sincronização)
        fig_graphs.add_vline(x=current_distance, line_width=2, line_dash="dash", line_color="yellow", row=i+1, col=1)

    fig_graphs.update_layout(
        height=800, plot_bgcolor='#1e1e1e', paper_bgcolor='#121212', font=dict(color='white'),
        margin=dict(l=40, r=20, t=40, b=20),
        hovermode="x unified" # Mostra dados dos dois carros juntos ao passar o mouse
    )
    
    fig_graphs.update_xaxes(showgrid=True, gridcolor='#333')
    fig_graphs.update_yaxes(showgrid=True, gridcolor='#333')

    return fig_map, fig_graphs

if __name__ == '__main__':
    app.run(debug=True)
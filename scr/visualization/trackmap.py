import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import fastf1
import os

# --- 1. Configuração do Cache do FastF1 ---
if not os.path.exists(r'data/cache'):
    os.makedirs(r'data/cache')
fastf1.Cache.enable_cache(r'data/cache')

# --- 2. Obter Telemetria Real da Fórmula 1 ---
def obter_telemetria(ano, gp, tipo_sessao='R'):
    print(f"Carregando dados: {ano} {gp}...")
    sessao = fastf1.get_session(ano, gp, tipo_sessao)
    sessao.load(telemetry=True, weather=False, messages=False)
    
    volta_rapida = sessao.laps.pick_fastest()
    tel = volta_rapida.get_telemetry()
    tel['Driver'] = volta_rapida['Driver']
    return tel

tel_ref = obter_telemetria(2018, 'Brazil', 'R')  
tel_cur = obter_telemetria(2024, 'Brazil', 'R')  

# --- 3. Criar Fundo da Pista Perfeito via Telemetria ---
def gerar_fundo_pista_plotly(telemetria, largura_metros=10.0):
    x = telemetria['X'].values
    y = telemetria['Y'].values
    
    dx = np.gradient(x)
    dy = np.gradient(y)
    norm = np.sqrt(dx**2 + dy**2)
    norm[norm == 0] = 1 
    
    nx = -dy / norm
    ny = dx / norm
    
    left_x = x + nx * largura_metros
    left_y = y + ny * largura_metros
    right_x = x - nx * largura_metros
    right_y = y - ny * largura_metros
    
    fig = go.Figure()

    # Preenchimento do asfalto (Unindo borda esquerda com direita invertida)
    x_asfalto = np.concatenate([left_x, right_x[::-1], [left_x[0]]])
    y_asfalto = np.concatenate([left_y, right_y[::-1], [left_y[0]]])

    fig.add_trace(go.Scatter(
        x=x_asfalto, y=y_asfalto,
        fill='toself', 
        fillcolor='rgba(100, 100, 100, 0.4)', # Cinza estilo asfalto
        line=dict(color='rgba(255,255,255,0)'), 
        name='Asfalto',
        hoverinfo='skip'
    ))

    # Bordas Brancas
    fig.add_trace(go.Scatter(x=left_x, y=left_y, mode='lines', line=dict(color='white', width=2), name='Limite Esq.'))
    fig.add_trace(go.Scatter(x=right_x, y=right_y, mode='lines', line=dict(color='white', width=2), name='Limite Dir.'))
    # Linha Central
    fig.add_trace(go.Scatter(x=x, y=y, mode='lines', line=dict(color='yellow', width=1, dash='dash'), name='Centro'))

    return fig

# Gera o mapa base usando o carro mais recente como âncora
fig_mapa_base = gerar_fundo_pista_plotly(tel_cur, largura_metros=8.0)

# --- 4. Inicialização do Dashboard Dash ---
app = dash.Dash(__name__)
max_dist = int(max(tel_ref['Distance'].max(), tel_cur['Distance'].max()))

app.layout = html.Div([
    html.H1("🏎️ Sistema de Telemetria F1", style={'textAlign': 'center', 'color': '#f4f4f4', 'fontFamily': 'Arial'}),
    
    html.Div([
        html.Label("Posição na Pista (Distância em Metros):", style={'color': 'white', 'fontWeight': 'bold'}),
        dcc.Slider(
            id='distance-slider',
            min=0, max=max_dist, step=5, value=0,
            marks={i: f'{i}m' for i in range(0, max_dist, 500)},
            tooltip={"placement": "bottom", "always_visible": True}
        )
    ], style={'padding': '20px', 'backgroundColor': '#2a2a2a', 'borderRadius': '10px', 'marginBottom': '20px'}),

    html.Div([
        html.Div([dcc.Graph(id='track-map', style={'height': '800px'})], style={'width': '40%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        html.Div([dcc.Graph(id='telemetry-graphs')], style={'width': '60%', 'display': 'inline-block', 'verticalAlign': 'top'})
    ])
], style={'backgroundColor': '#121212', 'padding': '20px'})

# --- 5. Lógica de Atualização ---
@app.callback(
    [Output('track-map', 'figure'), Output('telemetry-graphs', 'figure')],
    [Input('distance-slider', 'value')]
)
def update_dashboard(current_distance):
    idx_ref = (tel_ref['Distance'] - current_distance).abs().idxmin()
    idx_cur = (tel_cur['Distance'] - current_distance).abs().idxmin()

    # MAPA DA PISTA
    fig_map = go.Figure(fig_mapa_base)

    # Nota: A telemetria de 2018 e 2024 terão origens X/Y diferentes por padrão do FastF1. 
    # Para o mapa ficar legível, vamos focar no carro atual (Ciano).
    fig_map.add_trace(go.Scatter(x=tel_cur['X'], y=tel_cur['Y'], mode='lines', line=dict(color='cyan', width=2), name=f"Atual ({tel_cur['Driver'].iloc[0]})"))

    # Marcador Dinâmico
    fig_map.add_trace(go.Scatter(
        x=[tel_cur['X'].iloc[idx_cur]],
        y=[tel_cur['Y'].iloc[idx_cur]],
        mode='markers',
        marker=dict(size=14, color='cyan', line=dict(color='white', width=2)),
        name='Posição'
    ))

    fig_map.update_layout(
        plot_bgcolor='#1e1e1e', paper_bgcolor='#121212', font=dict(color='white'),
        xaxis=dict(showgrid=False, zeroline=False, scaleanchor="y", scaleratio=1, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0.5)")
    )

    # GRÁFICOS DE TELEMETRIA (Mantém os dois carros comparados aqui)
    fig_graphs = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04, 
                               subplot_titles=("Velocidade (km/h)", "Acelerador (%)", "Freio", "RPM"))

    for i, metric in enumerate(['Speed', 'Throttle', 'Brake', 'RPM']):
        fig_graphs.add_trace(go.Scatter(x=tel_ref['Distance'], y=tel_ref[metric], mode='lines', line=dict(color='red', width=1.5), name=f"Ref" if i==0 else "", showlegend=(i==0)), row=i+1, col=1)
        fig_graphs.add_trace(go.Scatter(x=tel_cur['Distance'], y=tel_cur[metric], mode='lines', line=dict(color='cyan', width=1.5), name=f"Atual" if i==0 else "", showlegend=(i==0)), row=i+1, col=1)
        fig_graphs.add_vline(x=current_distance, line_width=2, line_dash="dash", line_color="yellow", row=i+1, col=1)

    fig_graphs.update_layout(height=800, plot_bgcolor='#1e1e1e', paper_bgcolor='#121212', font=dict(color='white'), margin=dict(l=40, r=20, t=40, b=20), hovermode="x unified")
    fig_graphs.update_xaxes(showgrid=True, gridcolor='#333')
    fig_graphs.update_yaxes(showgrid=True, gridcolor='#333')

    return fig_map, fig_graphs

if __name__ == '__main__':
    app.run(debug=True)
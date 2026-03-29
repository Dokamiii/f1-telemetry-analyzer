import pandas as pd
import matplotlib.pyplot as plt

# 1. Carregar os dados do CSV
# Certifique-se de que o arquivo 'telemetry_session.csv' está na mesma pasta do script
df = pd.read_csv('telemetry_session.csv')

# 2. Configurar o tamanho da figura
fig = plt.figure(figsize=(12, 10))

# --- GRÁFICO 1: MAPA DA PISTA ---
ax1 = plt.subplot(2, 1, 1)
# Usando pos_x e pos_z (geralmente formam a visão superior no espaço 3D)
ax1.plot(df['pos_x'], df['pos_z'], color='black', linewidth=1.5)
ax1.set_title('Mapa do Trajeto (Posição X vs Z)', fontsize=14, fontweight='bold')
ax1.set_xlabel('Posição X')
ax1.set_ylabel('Posição Z')
ax1.axis('equal') # Mantém a proporção real da pista para não distorcer as curvas
ax1.grid(True, linestyle='--', alpha=0.6)

# --- GRÁFICO 2: TELEMETRIA (VELOCIDADE E PEDAIS) ---
ax2 = plt.subplot(2, 1, 2)

# Plotando a Velocidade no eixo Y principal (esquerdo)
color_speed = '#1f77b4' # Azul
ax2.plot(df['session_time'], df['speed'], color=color_speed, label='Velocidade', linewidth=2)
ax2.set_xlabel('Tempo de Sessão (s)', fontsize=12)
ax2.set_ylabel('Velocidade', color=color_speed, fontsize=12)
ax2.tick_params(axis='y', labelcolor=color_speed)
ax2.grid(True, linestyle='--', alpha=0.6)

# Criando um eixo Y secundário (direito) para Acelerador e Freio
ax3 = ax2.twinx()
color_throttle = '#2ca02c' # Verde
color_brake = '#d62728'    # Vermelho

ax3.plot(df['session_time'], df['throttle'], color=color_throttle, label='Acelerador', alpha=0.8)
ax3.plot(df['session_time'], df['brake'], color=color_brake, label='Freio', alpha=0.8)
ax3.set_ylabel('Pedais (Input)', fontsize=12)

# Juntando as legendas dos dois eixos
lines_1, labels_1 = ax2.get_legend_handles_labels()
lines_2, labels_2 = ax3.get_legend_handles_labels()
ax3.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper right')
ax3.set_title('Velocidade e Inputs de Pedal ao longo do tempo', fontsize=14, fontweight='bold')

# 3. Ajustar o layout e exibir
plt.tight_layout()
plt.show()
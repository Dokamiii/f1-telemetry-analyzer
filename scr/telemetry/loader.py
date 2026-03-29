import pandas as pd
import matplotlib.pyplot as plt

# 1. Carregar os dados
df = pd.read_csv('telemetry_session.csv')

# 2. Calcular a Quantidade de Voltas e Tempos
voltas = df['lap'].unique()
quantidade_voltas = len(voltas)

# Montar o texto que será exibido no gráfico
texto_resumo = f"RESUMO DA SESSÃO\n\nTotal de Voltas: {quantidade_voltas}\n\nTempos por Volta:\n"
for volta in voltas:
    df_volta = df[df['lap'] == volta]
    tempo_total = df_volta['session_time'].max() - df_volta['session_time'].min()
    
    # Calcula os minutos e os segundos restantes
    minutos = int(tempo_total // 60)
    segundos = tempo_total % 60
    
    # Formata para mm:ss.000
    texto_resumo += f"Volta {volta}: {minutos:02d}:{segundos:06.3f}\n"

# 3. Configurar a figura com 4 subgráficos
# O gridspec_kw faz com que o mapa da pista (índice 0) seja maior que os gráficos de linha
fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(14, 14), gridspec_kw={'height_ratios': [2, 1, 1, 1]})

# --- GRÁFICO 1: MAPA DA PISTA ---
ax1.plot(df['pos_x'], df['pos_z'], color='black', linewidth=1.5)
ax1.set_title('Mapa da Pista (Posição X vs Z)', fontsize=14, fontweight='bold')
ax1.set_ylabel('Posição Z')
ax1.axis('equal') # Mantém a proporção real da pista
ax1.grid(True, linestyle='--', alpha=0.6)

# Comando adicionado para espelhar o mapa horizontalmente
ax1.invert_xaxis()

# Inserindo o texto com o resumo das voltas no gráfico (ancorado no ax1)
ax1.text(1.05, 0.5, texto_resumo, transform=ax1.transAxes, fontsize=12,
         verticalalignment='center', bbox=dict(boxstyle='round,pad=0.8', facecolor='#f8f9fa', edgecolor='#ced4da', alpha=0.9))

# --- GRÁFICO 2: VELOCIDADE ---
color_speed = '#1f77b4' # Azul
ax2.plot(df['session_time'], df['speed'], color=color_speed, linewidth=2)
ax2.set_ylabel('Velocidade', color=color_speed, fontsize=12, fontweight='bold')
ax2.tick_params(axis='y', labelcolor=color_speed)
ax2.grid(True, linestyle='--', alpha=0.6)

# --- GRÁFICO 3: ACELERADOR ---
color_throttle = '#2ca02c' # Verde
ax3.plot(df['session_time'], df['throttle'], color=color_throttle, linewidth=2)
ax3.set_ylabel('Acelerador', color=color_throttle, fontsize=12, fontweight='bold')
ax3.tick_params(axis='y', labelcolor=color_throttle)
ax3.grid(True, linestyle='--', alpha=0.6)

# --- GRÁFICO 4: FREIO ---
color_brake = '#d62728' # Vermelho
ax4.plot(df['session_time'], df['brake'], color=color_brake, linewidth=2)
ax4.set_xlabel('Tempo de Sessão (s)', fontsize=12, fontweight='bold')
ax4.set_ylabel('Freio', color=color_brake, fontsize=12, fontweight='bold')
ax4.tick_params(axis='y', labelcolor=color_brake)
ax4.grid(True, linestyle='--', alpha=0.6)

# 4. Ajustar layout e exibir
# tight_layout ajusta os espaços internos, e subplots_adjust garante espaço extra na direita para a caixa de texto
plt.tight_layout()
plt.subplots_adjust(right=0.82) 

plt.show()
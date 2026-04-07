import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import os
import glob

# ==========================================================
# 1. CARREGAR OS DADOS (ARQUIVO MAIS RECENTE)
# ==========================================================
# Lista todos os arquivos .csv na pasta atual
arquivos_csv = glob.glob(r'scr\telemetry\f1-25\*.csv')

# Verifica se existe algum arquivo na pasta para evitar erros
if not arquivos_csv:
    raise FileNotFoundError("Nenhum arquivo CSV foi encontrado na pasta atual.")

# Pega o arquivo mais recente baseado na data de modificação
arquivo_mais_recente = max(arquivos_csv, key=os.path.getmtime)

print(f"Lendo os dados do arquivo: {arquivo_mais_recente}")

# Carrega o dataframe com o arquivo encontrado
df = pd.read_csv(arquivo_mais_recente)

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
# ==========================================================
# CÁLCULO DA DISTÂNCIA E FILTRO DA ÚLTIMA VOLTA COMPLETADA
# ==========================================================
# 1. Calcula a diferença de tempo entre cada linha (em segundos)
df['delta_time'] = df['session_time'].diff().fillna(0)

# 2. Converte a velocidade de km/h para metros por segundo (m/s)
df['speed_ms'] = df['speed'] / 3.6

# 3. Calcula quantos metros o carro andou nessa micro-fração de segundo
df['delta_dist'] = df['speed_ms'] * df['delta_time']

# 4. Acumula a distância para cada volta
df['lap_distance'] = df.groupby('lap')['delta_dist'].cumsum()

# 3. Configurar a figura com 4 subgráficos
# O gridspec_kw faz com que o mapa da pista (índice 0) seja maior que os gráficos de linha
fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(14, 14), gridspec_kw={'height_ratios': [2, 1, 1, 1]})

# --- GRÁFICO 1: MAPA DA PISTA ---
# Usando o df_mapa, que não tem os "rabiscos" de entrada/saída de box
ax1.plot(df['pos_x'], df['pos_z'], color='black', linewidth=1.5)
ax1.set_title('Mapa da Pista (Apenas Voltas Válidas)', fontsize=14, fontweight='bold')
ax1.set_ylabel('Posição Z')
ax1.axis('equal') # Mantém a proporção real da pista
ax1.grid(True, linestyle='--', alpha=0.6)

# Comando adicionado para espelhar o mapa horizontalmente
ax1.invert_xaxis()

# Inserindo o texto com o resumo das voltas no gráfico (ancorado no ax1)
ax1.text(1.05, 0.5, texto_resumo, transform=ax1.transAxes, fontsize=12,
         verticalalignment='center', bbox=dict(boxstyle='round,pad=0.8', facecolor='#f8f9fa', edgecolor='#ced4da', alpha=0.9))

# 5. Descobre quais voltas foram completadas
distancias_por_volta = df.groupby('lap')['lap_distance'].max()
distancia_pista = distancias_por_volta.max() # Considera a maior volta como referência do tamanho da pista

# Considera como completada a volta que tem pelo menos 95% da distância máxima
voltas_completadas = distancias_por_volta[distancias_por_volta >= 0.95 * distancia_pista].index.tolist()
   
# Filtra o dataframe para conter APENAS a última volta completada
if voltas_completadas:
    ultima_volta = voltas_completadas[-1]
    df = df[df['lap'] == ultima_volta]
else:
    # Se por acaso nenhuma volta atingiu a métrica, pega a última disponível
    ultima_volta = df['lap'].max()
    df = df[df['lap'] == ultima_volta]
# ==========================================================
# FILTRO DO MAPA: Apenas voltas completadas (limpa o traçado)
# ==========================================================
# Verifica se a lista de voltas completadas existe e tem dados. 
# Se sim, filtra. Se não, usa o df padrão para não quebrar o código.
if 'voltas_completadas' in locals() and voltas_completadas:
    df_mapa = df[df['lap'].isin(voltas_completadas)]
else:
    df_mapa = df

# ==========================================================
# SUBSTITUIR OS GRÁFICOS 2, 3 E 4 POR ESTE BLOCO:
# ==========================================================
color_speed = '#1f77b4'    # Azul
color_throttle = '#2ca02c' # Verde
color_brake = '#d62728'    # Vermelho

# Loop para desenhar cada volta separadamente e sobrepor as linhas
for volta in df['lap'].unique():
    df_v = df[df['lap'] == volta]
    
    # --- GRÁFICO 2: VELOCIDADE ---
    # Usando alpha=0.7 para as linhas ficarem levemente transparentes ao se sobreporem
    ax2.plot(df_v['lap_distance'], df_v['speed'], color=color_speed, linewidth=1.5, alpha=0.7)
    
    # --- GRÁFICO 3: ACELERADOR ---
    ax3.plot(df_v['lap_distance'], df_v['throttle'] * 100, color=color_throttle, linewidth=1.5, alpha=0.7)
    
    # --- GRÁFICO 4: FREIO ---
    ax4.plot(df_v['lap_distance'], df_v['brake'] * 100, color=color_brake, linewidth=1.5, alpha=0.7)

# --- CONFIGURAÇÕES VISUAIS (Textos, Eixos e Grids) ---

# --- GRÁFICO 2: VELOCIDADE ---
ax2.set_ylabel('Velocidade', color=color_speed, fontsize=12, fontweight='bold')
ax2.tick_params(axis='y', labelcolor=color_speed)
ax2.grid(True, linestyle='--', alpha=0.6)

# --- GRÁFICO 3: ACELERADOR ---
ax3.set_ylabel('Acelerador', color=color_throttle, fontsize=12, fontweight='bold')
ax3.set_ylim(-5, 105) 
ax3.yaxis.set_major_formatter(mtick.PercentFormatter()) 
ax3.tick_params(axis='y', labelcolor=color_throttle)
ax3.grid(True, linestyle='--', alpha=0.6)

# --- GRÁFICO 4: FREIO ---
ax4.set_xlabel('Distância da Volta (metros)', fontsize=12, fontweight='bold')
ax4.set_ylabel('Freio', color=color_brake, fontsize=12, fontweight='bold')
ax4.set_ylim(-5, 105) 
ax4.yaxis.set_major_formatter(mtick.PercentFormatter()) 
ax4.tick_params(axis='y', labelcolor=color_brake)
ax4.grid(True, linestyle='--', alpha=0.6)

# 4. Ajustar layout e exibir
# tight_layout ajusta os espaços internos, e subplots_adjust garante espaço extra na direita para a caixa de texto
plt.tight_layout()
plt.subplots_adjust(right=0.82) 

plt.show()
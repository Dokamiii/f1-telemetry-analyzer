import fastf1
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import matplotlib.animation as animation
import matplotlib.colors as colors
from matplotlib.patches import Rectangle
from scipy.interpolate import interp1d

# 1. Carregar Dados FastF1
fastf1.Cache.enable_cache("cache")
print("Carregando telemetria...")
session = fastf1.get_session(2023, "Brazil", "Q")
session.load()

lap_opt = session.laps.pick_driver('NOR').pick_fastest()
lap_ref = session.laps.pick_driver('RUS').pick_fastest()

tel_opt = lap_opt.get_telemetry().add_distance()
tel_ref = lap_ref.get_telemetry().add_distance()

X_orig = tel_opt['X'].values
Y_orig = tel_opt['Y'].values
SPEED_orig = tel_opt['Speed'].values
TIME_orig = tel_opt['Time'].dt.total_seconds().values

X_ref_orig = tel_ref['X'].values
Y_ref_orig = tel_ref['Y'].values
DIST_ref_orig = tel_ref['Distance'].values

# 2. Interpolação para Alta Fluidez (60 FPS)
print("Suavizando traçados...")
_, idx_opt = np.unique(TIME_orig, return_index=True)
_, idx_ref = np.unique(DIST_ref_orig, return_index=True)

TIME_smooth = np.linspace(TIME_orig[idx_opt][0], TIME_orig[idx_opt][-1], len(TIME_orig[idx_opt]) * 5)
DIST_ref_smooth = np.linspace(DIST_ref_orig[idx_ref][0], DIST_ref_orig[idx_ref][-1], len(DIST_ref_orig[idx_ref]) * 5)

X = interp1d(TIME_orig[idx_opt], X_orig[idx_opt], kind='cubic')(TIME_smooth)
Y = interp1d(TIME_orig[idx_opt], Y_orig[idx_opt], kind='cubic')(TIME_smooth)
SPEED = interp1d(TIME_orig[idx_opt], SPEED_orig[idx_opt], kind='linear')(TIME_smooth)
TIME = TIME_smooth

X_ref = interp1d(DIST_ref_orig[idx_ref], X_ref_orig[idx_ref], kind='cubic')(DIST_ref_smooth)
Y_ref = interp1d(DIST_ref_orig[idx_ref], Y_ref_orig[idx_ref], kind='cubic')(DIST_ref_smooth)
DIST_ref = DIST_ref_smooth

# Calcular a "frente" do carro (Heading angle) para rotacionar o retângulo
dx = np.gradient(X)
dy = np.gradient(Y)
HEADING = np.degrees(np.arctan2(dy, dx)) # Ângulo em graus para cada frame

# 3. CSV Real da Pista (Escala 1:1)
print("Processando CSV da pista...")
track_df = pd.read_csv('SaoPaulo.csv', comment='#', names=['x', 'y', 'w_right', 'w_left'])

csv_x = track_df['x'].values
csv_y = track_df['y'].values
csv_dist = np.zeros(len(csv_x))
for i in range(1, len(csv_x)):
    csv_dist[i] = csv_dist[i-1] + np.hypot(csv_x[i] - csv_x[i-1], csv_y[i] - csv_y[i-1])

csv_dist_norm = csv_dist / csv_dist[-1]
f1_dist_norm = DIST_ref / DIST_ref[-1]

# Multiplicador 1.0 (Pista exata de 12 a 15 metros de largura)
VISUAL_MULTIPLIER = 1.0 
real_w_right = np.interp(f1_dist_norm, csv_dist_norm, track_df['w_right'].values) * VISUAL_MULTIPLIER
real_w_left = np.interp(f1_dist_norm, csv_dist_norm, track_df['w_left'].values) * VISUAL_MULTIPLIER

def create_real_boundaries(x, y, w_right, w_left):
    grad_x = np.gradient(x)
    grad_y = np.gradient(y)
    norm = np.sqrt(grad_x**2 + grad_y**2)
    norm[norm == 0] = 1e-6 
    nx = -grad_y / norm
    ny = grad_x / norm
    
    out_x = x + nx * w_right
    out_y = y + ny * w_right
    in_x = x - nx * w_left
    in_y = y - ny * w_left
    return out_x, out_y, in_x, in_y

out_x, out_y, in_x, in_y = create_real_boundaries(X_ref, Y_ref, real_w_right, real_w_left)

# 4. Configuração do Plot Lado a Lado
fig, (ax_full, ax_zoom) = plt.subplots(1, 2, figsize=(16, 8), facecolor='white')
fig.canvas.manager.set_window_title('F1 Telemetry - Real Scale 1:1 View')

# Tela 1: Zoom Out
ax_full.set_facecolor('white')
ax_full.axis('off')
ax_full.set_aspect('equal')
ax_full.set_title("Full Track View", fontsize=16, fontweight='bold')
ax_full.plot(out_x, out_y, color='black', linewidth=1) 
ax_full.plot(in_x, in_y, color='black', linewidth=1)   
ax_full.plot(X_ref, Y_ref, color='gray', linestyle='--', linewidth=0.8) 

# Tela 2: Zoom In
ax_zoom.set_facecolor('white')
ax_zoom.axis('off')
ax_zoom.set_aspect('equal')
ax_zoom.set_title("Sector Camera (100m View)", fontsize=16, fontweight='bold')
ax_zoom.plot(out_x, out_y, color='black', linewidth=2) 
ax_zoom.plot(in_x, in_y, color='black', linewidth=2)   
ax_zoom.plot(X_ref, Y_ref, color='gray', linestyle='--', linewidth=1.5) 

# Textos
time_text = fig.text(0.5, 0.92, '', fontsize=24, fontweight='bold', ha='center')
fig.text(0.5, 0.97, "F1 2023 Optimized Racing Line - True Scale", fontsize=22, ha='center', va='top')

# Rastro Colorido
cmap = plt.cm.RdYlGn
norm = colors.Normalize(vmin=SPEED.min(), vmax=SPEED.max())

lc_full = LineCollection([], cmap=cmap, norm=norm, linewidths=2, zorder=4)
ax_full.add_collection(lc_full)

lc_zoom = LineCollection([], cmap=cmap, norm=norm, linewidths=5, alpha=0.8, zorder=4) # Rastro mais largo e levemente transparente para visibilidade
ax_zoom.add_collection(lc_zoom)

# --- CRIAÇÃO DO CARRO EM ESCALA REAL (5.5m x 2.0m) ---
CAR_LENGTH = 5.5
CAR_WIDTH = 2.0

def get_rect_bottom_left(cx, cy, length, width, angle_deg):
    angle_rad = np.radians(angle_deg)
    dx = -length / 2
    dy = -width / 2
    rot_dx = dx * np.cos(angle_rad) - dy * np.sin(angle_rad)
    rot_dy = dx * np.sin(angle_rad) + dy * np.cos(angle_rad)
    return cx + rot_dx, cy + rot_dy

# Inicializa os retângulos escondidos
rect_full = Rectangle((0,0), CAR_LENGTH, CAR_WIDTH, color='black', zorder=5)
rect_zoom = Rectangle((0,0), CAR_LENGTH, CAR_WIDTH, color='black', zorder=5)
ax_full.add_patch(rect_full)
ax_zoom.add_patch(rect_zoom)

# Barra de Cores
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=[ax_full, ax_zoom], orientation='horizontal', fraction=0.04, pad=0.05, aspect=60)
cbar.set_label('Speed [km/h]   red=low   green=high', fontsize=12)
cbar_indicator = cbar.ax.axvline(SPEED[0], color='black', linewidth=2)
cbar_text = cbar.ax.text(1.01, 0.5, '', transform=cbar.ax.transAxes, va='center', ha='left', fontsize=12)

# 5. Sistema de Animação
camera_center = [X[0], Y[0]]
zoom_radius = 100 # Câmera muito mais próxima para vermos as proporções
threshold = 60    # Troca de câmera mais frequente

def update(frame):
    current_x = X[:frame+1]
    current_y = Y[:frame+1]
    current_speed_array = SPEED[:frame+1]
    current_speed_val = SPEED[frame]
    
    car_x = X[frame]
    car_y = Y[frame]
    car_angle = HEADING[frame]
    
    # Atualiza a posição e rotação do CARRO ESCALA 1:1
    rx, ry = get_rect_bottom_left(car_x, car_y, CAR_LENGTH, CAR_WIDTH, car_angle)
    rect_full.set_xy((rx, ry))
    rect_full.angle = car_angle
    
    rect_zoom.set_xy((rx, ry))
    rect_zoom.angle = car_angle
    
    # Atualiza o rastro
    if frame > 0:
        points = np.array([current_x, current_y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        lc_full.set_segments(segments)
        lc_full.set_array(current_speed_array)
        lc_zoom.set_segments(segments)
        lc_zoom.set_array(current_speed_array)
    
    # Lógica de Câmera da tela Zoom
    dist_x = abs(car_x - camera_center[0])
    dist_y = abs(car_y - camera_center[1])
    
    if dist_x > threshold or dist_y > threshold:
        camera_center[0] = car_x
        camera_center[1] = car_y
        
    ax_zoom.set_xlim(camera_center[0] - zoom_radius, camera_center[0] + zoom_radius)
    ax_zoom.set_ylim(camera_center[1] - zoom_radius, camera_center[1] + zoom_radius)
    
    total_sec = TIME[frame]
    mins = int(total_sec // 60)
    secs = total_sec % 60
    time_text.set_text(f'{mins}:{secs:05.2f}')
    
    cbar_indicator.set_xdata([current_speed_val, current_speed_val])
    cbar_text.set_text(f'{current_speed_val:.0f}')

    return rect_full, rect_zoom, lc_full, lc_zoom, time_text, cbar_indicator, cbar_text

mean_dt = np.mean(np.diff(TIME)) 
real_time_interval = max(1, int(mean_dt * 1000))

ani = animation.FuncAnimation(fig, update, frames=range(0, len(TIME), 1), interval=real_time_interval, blit=False)

plt.show()
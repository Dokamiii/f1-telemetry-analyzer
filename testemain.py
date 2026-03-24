import arcade
import fastf1
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
import matplotlib.cm as cm
import matplotlib.colors as colors
from scipy.signal import savgol_filter

# 1. Carregar dados FastF1

fastf1.Cache.enable_cache("cache")

print("Carregando telemetria...")
session = fastf1.get_session(2023, "Brazil", "Q")
session.load()

fastest_lap = session.laps.pick_fastest()
telemetry = fastest_lap.get_telemetry().add_distance()
X = telemetry["X"].values
Y = telemetry["Y"].values
SPEED = telemetry["Speed"].values
TIME = telemetry["Time"].dt.total_seconds().values
DISTANCE = telemetry["Distance"].values
DRIVER = fastest_lap["Driver"]

def interpolate_track(x, y, speed, time, distance, factor=3):

    t = np.arange(len(x))
    t_new = np.linspace(0, len(x)-1, len(x)*factor)

    x_i = np.interp(t_new, t, x)
    y_i = np.interp(t_new, t, y)
    s_i = np.interp(t_new, t, speed)
    time_i = np.interp(t_new, t, time)
    dist_i = np.interp(t_new, t, distance)

    return x_i, y_i, s_i, time_i, dist_i

X, Y, SPEED, TIME, DISTANCE = interpolate_track(
    X, Y, SPEED, TIME, DISTANCE
    )

s1_end = DISTANCE.max() * 0.33
s2_end = DISTANCE.max() * 0.66
s3_end = DISTANCE.max()


# normalizar distância
dist_norm = DISTANCE / DISTANCE.max()


X, Y, SPEED, TIME, DISTANCE = interpolate_track(X, Y, SPEED, TIME, DISTANCE)
dt = np.gradient(TIME)
dt[dt == 0] = 1e-6
ACC = np.gradient(SPEED) / dt

ACC_MIN, ACC_MAX = ACC.min(), ACC.max()
# 2. Configuração visual

WIDTH = 1100
HEIGHT = 900
SCALE = 0.07

# Colormap igual matplotlib
cmap = matplotlib.colormaps["RdYlGn"]
norm = colors.Normalize(vmin=SPEED.min(), vmax=SPEED.max())

laps = session.laps

best_s1 = laps["Sector1Time"].min()
best_s2 = laps["Sector2Time"].min()
best_s3 = laps["Sector3Time"].min()

ideal_total = best_s1 + best_s2 + best_s3
ideal_total_sec = ideal_total.total_seconds()

dist_norm = DISTANCE / DISTANCE.max()

# tempo ideal ao longo da pista
IDEAL_TIME = dist_norm * ideal_total_sec

Z = SPEED * 0.3

opt_x = savgol_filter(X, 51, 3)
opt_y = savgol_filter(Y, 51, 3)

def format_lap(time):
    total = time.total_seconds()
    minutes = int(total // 60)
    seconds = total % 60
    return f"{minutes}:{seconds:06.3f}"

def get_sector(dist):
    if dist <= s1_end:
        return 1
    elif dist <= s2_end:
        return 2
    else:
        return 3

def speed_to_color(speed):

    rgba = cmap(norm(speed))

    r = int(rgba[0] * 255)
    g = int(rgba[1] * 255)
    b = int(rgba[2] * 255)

    return (r, g, b, 255)
# 3. Classe Arcade
class F1Telemetry(arcade.Window):

    def __init__(self):

        super().__init__(WIDTH, HEIGHT, f"F1 Telemetry Replay - {DRIVER}")

        arcade.set_background_color((30, 30, 30))

        self.current_frame = 0
        self.replay_time = 0
        self.points = []

        # Barra de aceleração
        self.bar_w = 900
        self.bar_h = 20
        self.bar_x_start = WIDTH // 2 - self.bar_w // 2
        self.bar_y = 60

        
        # Centralização da pista
        cx, cy = (X.max() + X.min()) / 2, (Y.max() + Y.min()) / 2
        for i in range(len(X)):
            nx = ((X[i] - cx) * SCALE) + WIDTH / 2
            ny = ((Y[i] - cy) * SCALE) + HEIGHT / 2
            self.points.append((nx, ny))

        # criar pontos da linha ideal
        self.opt_points = []

        for i in range(len(opt_x)):
            nx = ((opt_x[i] - cx) * SCALE) + WIDTH / 2
            ny = ((opt_y[i] - cy) * SCALE) + HEIGHT / 2
            self.opt_points.append((nx, ny))

        self.opt_line = arcade.shape_list.ShapeElementList()

        for i in range(1, len(self.opt_points)):
            p1 = self.opt_points[i-1]
            p2 = self.opt_points[i]

            color = speed_to_color(SPEED[i])

            self.opt_line.append(
                arcade.shape_list.create_line(*p1, *p2, color, 4)
            )

        self.track = arcade.shape_list.ShapeElementList()

        self.track.append(arcade.shape_list.create_line_strip(self.points, (0,0,0), 22))
        self.track.append(arcade.shape_list.create_line_strip(self.points, (230,230,230), 16))
        self.track.append(arcade.shape_list.create_line_strip(self.points, (100,100,100), 2))

        # --- AS CAMADAS QUE ESTAVAM FALTANDO ---
        self.glow_layer = arcade.shape_list.ShapeElementList()
        self.main_layer = arcade.shape_list.ShapeElementList()
        self.high_layer = arcade.shape_list.ShapeElementList()

        # Criar uma lista para a telemetria colorida
        self.telemetry_lines = arcade.shape_list.ShapeElementList()
        for i in range(1, len(self.points)-5, 8):
            p1 = self.points[i]
            p2 = self.points[i+4]
            color = speed_to_color(SPEED[i])
            self.track.append(
                arcade.shape_list.create_line(*p1, *p2, (150,150,150), 2)
            )
            # Camada de Brilho (Glow)
            self.glow_layer.append(
                arcade.shape_list.create_line(*p1, *p2, (*color[:3], 60), 12)
            )
            
            # Camada Principal
            self.main_layer.append(
                arcade.shape_list.create_line(*p1, *p2, color, 6)
            )
            
            # Camada de Highlight
            self.high_layer.append(
                arcade.shape_list.create_line(*p1, *p2, (255, 255, 255, 40), 2)
            )

            line = arcade.shape_list.create_line(*p1, *p2, color, 6)
            self.telemetry_lines.append(line)
        # 3. Barra de aceleração
        self.acc_bar_list = arcade.shape_list.ShapeElementList()
        steps = 300
        for i in range(steps):
            t = i / steps
            rgba = cmap(t)
            color = (int(rgba[0]*255), int(rgba[1]*255), int(rgba[2]*255))
            rect = arcade.shape_list.create_rectangle_filled(
                self.bar_x_start + (i * self.bar_w / steps),
                self.bar_y,
                self.bar_w / steps + 1,
                self.bar_h,
                color,
            )
            self.acc_bar_list.append(rect)
    # ----------------------------

    def on_draw(self):

        self.clear()

        # pista
        self.track.draw()

        self.opt_line.draw()

        frame = min(self.current_frame, len(TIME)-1)

        real_time = TIME[self.current_frame]

        # índice do ghost baseado no tempo ideal
        ghost_idx = np.searchsorted(IDEAL_TIME, real_time)

        ghost_idx = min(ghost_idx, len(self.points) - 1)

        # Desenha telemetria acumulada
        if self.current_frame > 1:
            for shape in self.glow_layer[:self.current_frame]:
                shape.draw()
            for shape in self.main_layer[:self.current_frame]:
                shape.draw()
            for shape in self.high_layer[:self.current_frame]:
                shape.draw()

        # Ghost Car
        if self.current_frame < len(self.points):
            x, y = self.points[self.current_frame]
            arcade.draw_circle_filled(x, y, 7, (255, 255, 255))
            arcade.draw_circle_outline(x, y, 8, (0, 0, 0), 2)
            
        idx = self.current_frame
        current_time = TIME[self.current_frame]

        delta = real_time - IDEAL_TIME[self.current_frame]

        # Ghost car (piloto ideal)
        gx, gy = self.points[ghost_idx]

        arcade.draw_circle_filled(
            gx,
            gy,
            6,
            (0, 255, 255)  # azul/ciano
        )

        arcade.draw_circle_outline(
            gx,
            gy,
            7,
            (255, 255, 255),
            2
        )

        arcade.draw_text(
            f"DELTA: {delta:+.3f}s",
            WIDTH - 300,
            HEIGHT - 100,
            arcade.color.YELLOW,
            14,
        )

        # HUD
        elapsed = TIME[frame]
        arcade.draw_text(
            f"{DRIVER} | VEL: {SPEED[idx]:.0f} KM/H",
            20,
            HEIGHT - 40,
            arcade.color.WHITE,
            16,
            bold=True,
        )

        arcade.draw_text(
            f"TEMPO: {TIME[idx]:.3f}s | SETOR: {get_sector(DISTANCE[idx])}",
            20,
            HEIGHT - 70,
            arcade.color.LIGHT_GRAY,
            12,
        )

        arcade.draw_text(
            f"VEL: {SPEED[self.current_frame]:.0f} km/h",
            20,
            HEIGHT - 100,
            arcade.color.WHITE,
            14,
        )
        sector = get_sector(DISTANCE[self.current_frame])
        arcade.draw_text(
            f"SETOR: S{sector}",
            20,
            HEIGHT - 120,
            arcade.color.YELLOW,
            14
        )
        arcade.draw_text(
            f"BEST S1: {best_s1}",
            20, HEIGHT-160,
            arcade.color.PURPLE, 14
        )

        arcade.draw_text(
            f"BEST S2: {best_s2}",
            20, HEIGHT-180,
            arcade.color.PURPLE, 14
        )

        arcade.draw_text(
            f"BEST S3: {best_s3}",
            20, HEIGHT-200,
            arcade.color.PURPLE, 14
        )

        arcade.draw_text(
            f"PILO IMP: {format_lap(ideal_total)}",
            WIDTH - 300,
            HEIGHT - 40,
            arcade.color.RED,
            16,
            bold=True
        )

        arcade.draw_text(
            "Speed [km/h] (Vermelho=Baixa | Verde=Alta)",
            WIDTH/2,
            self.bar_y - 55,
            arcade.color.WHITE,
            14,
            anchor_x="center"
        )
        ticks = np.linspace(SPEED.min(), SPEED.max(), 6)

        for i, v in enumerate(ticks):
            x = self.bar_x_start + (i/(len(ticks)-1)) * self.bar_w
            
            arcade.draw_text(
                f"{int(v)}",
                x-10,
                self.bar_y - 30,
                arcade.color.WHITE,
                12,
                anchor_x="center"
        )

        # Barra de aceleração
        self.acc_bar_list.draw()

        # Evita divisão por zero
        if ACC_MAX != ACC_MIN:
            acc_norm = (ACC[idx] - ACC_MIN) / (ACC_MAX - ACC_MIN)
        else:
            acc_norm = 0.5

        indicator_x = self.bar_x_start + (acc_norm * self.bar_w)

    def on_update(self, delta_time):
        self.replay_time += delta_time
        # Busca o índice, mas limita ao tamanho máximo do array
        self.current_frame = min(np.searchsorted(TIME, self.replay_time), len(self.points) - 1)

        if self.replay_time >= TIME[-1]:
            self.replay_time = 0
            self.current_frame = 0
# ----------------------------
# 4. Executar
# ----------------------------
if __name__ == "__main__":

    app = F1Telemetry()
    arcade.run()

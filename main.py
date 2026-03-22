import arcade
import fastf1
import numpy as np
import matplotlib.cm as cm
import matplotlib.colors as colors

# 1. Carregar dados FastF1

fastf1.Cache.enable_cache("cache")

print("Carregando telemetria...")
session = fastf1.get_session(2023, "Brazil", "Q")
session.load()

fastest_lap = session.laps.pick_fastest()
telemetry = fastest_lap.get_telemetry().add_distance()

distance = telemetry["Distance"].values

total_distance = distance.max()

s1_end = total_distance * 0.33
s2_end = total_distance * 0.66
s3_end = total_distance

X = telemetry["X"].values
Y = telemetry["Y"].values
SPEED = telemetry["Speed"].values
TIME = telemetry["Time"].dt.total_seconds().values
DRIVER = fastest_lap["Driver"]

# 2. Configuração visual

WIDTH = 1100
HEIGHT = 900
SCALE = 0.07

# Colormap igual matplotlib
cmap = cm.get_cmap("RdYlGn")
norm = colors.Normalize(vmin=SPEED.min(), vmax=SPEED.max())

laps = session.laps

best_s1 = laps["Sector1Time"].min()
best_s2 = laps["Sector2Time"].min()
best_s3 = laps["Sector3Time"].min()

perfect_lap = best_s1 + best_s2 + best_s3

Z = SPEED * 0.3

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

        center_x = (X.max() + X.min()) / 2
        center_y = (Y.max() + Y.min()) / 2

        for i in range(len(X)):

            nx = ((X[i] - center_x) * SCALE) + WIDTH / 2
            ny = ((Y[i] - center_y) * SCALE) + HEIGHT / 2

            self.points.append((nx, ny))

    # ----------------------------

    def on_draw(self):

        self.clear()
        # Pista (bordas)
        # borda externa
        arcade.draw_line_strip(self.points, (15,15,15), 18)

        # asfalto
        arcade.draw_line_strip(self.points, (60,60,60), 12)

        # linha interna clara
        arcade.draw_line_strip(self.points, (120,120,120), 2)
        # Linha colorida velocidade
        if self.current_frame > 1:
            for i in range(1, self.current_frame):
                p1 = self.points[i - 1]
                p2 = self.points[i]
                color = speed_to_color(SPEED[i])
                # glow externo
                arcade.draw_line(
                    p1[0], p1[1],
                    p2[0], p2[1],
                    (*color[:3], 60),
                    12
                )

                # linha principal
                arcade.draw_line(
                    p1[0], p1[1],
                    p2[0], p2[1],
                    color,
                    6
                )

                # highlight central
                arcade.draw_line(
                    p1[0], p1[1],
                    p2[0], p2[1],
                    (255,255,255,40),
                    2
                )
        # Ghost car
        if self.current_frame < len(self.points):
            cur = self.points[self.current_frame]
            # sombra
            arcade.draw_circle_filled(cur[0],cur[1],12,(0,0,0,80))

            # carro
            arcade.draw_circle_filled(cur[0],cur[1],8,(240,240,240))

            # outline
            arcade.draw_circle_outline(cur[0],cur[1],8,(30,30,30),2)
        # HUD
        elapsed = TIME[self.current_frame]
        arcade.draw_text(
            f"PILOTO: {DRIVER}",
            20,
            HEIGHT - 40,
            arcade.color.WHITE,
            16,
            bold=True,
        )

        arcade.draw_text(
            f"TEMPO: {elapsed:.3f}s",
            20,
            HEIGHT - 70,
            arcade.color.WHITE,
            14,
        )
        arcade.draw_text(
            f"VEL: {SPEED[self.current_frame]:.0f} km/h",
            20,
            HEIGHT - 100,
            arcade.color.WHITE,
            14,
        )
        sector = get_sector(distance[self.current_frame])
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
            f"PILO IMP: {format_lap(perfect_lap)}",
            WIDTH - 300,
            HEIGHT - 40,
            arcade.color.RED,
            16,
            bold=True
        )
    # ----------------------------
    def on_update(self, delta_time):

        self.replay_time += delta_time

        self.current_frame = np.searchsorted(TIME, self.replay_time)

        if self.current_frame >= len(self.points):
            self.replay_time = 0
            self.current_frame = 0
# ----------------------------
# 4. Executar
# ----------------------------
if __name__ == "__main__":

    app = F1Telemetry()
    arcade.run()
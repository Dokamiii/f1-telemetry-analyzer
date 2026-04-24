import numpy as np
from typing import Dict, List
from scipy.interpolate import splprep, splev


class RacelineAI:
    def __init__(self, track_data: Dict):
        self.track_data = track_data
        self.corners = track_data["corners"]
        self.centerline_x = np.array(track_data["centerline"]["x"])
        self.centerline_y = np.array(track_data["centerline"]["y"])
        self.left_edge_x = np.array(track_data["left_edge"]["x"])
        self.left_edge_y = np.array(track_data["left_edge"]["y"])
        self.right_edge_x = np.array(track_data["right_edge"]["x"])
        self.right_edge_y = np.array(track_data["right_edge"]["y"])
        self.curvatures = np.array(track_data["curvatures"])

    # ==========================
    # 🔥 FUNÇÃO PRINCIPAL
    # ==========================
    def generate_optimal_raceline(self, player_data: Dict) -> Dict:
        ideal_apexes = self._calculate_ideal_apexes()

        if len(ideal_apexes) < 2:
            ideal_trajectory = np.column_stack([self.centerline_x, self.centerline_y])
        else:
            ideal_trajectory = self._generate_racing_line(ideal_apexes)

        ideal_trajectory = self._enforce_track_limits(ideal_trajectory, margin=1.0)
        ideal_speeds = self._calculate_ideal_speeds(ideal_trajectory)
        ideal_inputs = self._calculate_ideal_inputs(ideal_speeds)
        estimated_time = self._estimate_lap_time(ideal_trajectory, ideal_speeds)
        distances = self._calculate_distances(ideal_trajectory)

        result = {
            "trajectory": {
                "x": ideal_trajectory[:, 0],
                "z": ideal_trajectory[:, 1],
                "distance": distances
            },
            "speed": ideal_speeds,
            "throttle": ideal_inputs["throttle"],
            "brake": ideal_inputs["brake"],
            "estimated_time": estimated_time,
            "apexes": ideal_apexes,
            "insights": self._generate_insights(player_data, ideal_speeds),
            "improvements": self._identify_improvements(player_data, ideal_speeds)
        }

        # 🔥 SANITIZAÇÃO GLOBAL (ANTI-FASTAPI BUG)
        return self._sanitize(result)

    # ==========================
    # 🧹 SANITIZAÇÃO (CHAVE DO FIX)
    # ==========================
    def _sanitize(self, obj):
        import numpy as np

        if isinstance(obj, dict):
            return {k: self._sanitize(v) for k, v in obj.items()}

        elif isinstance(obj, list):
            return [self._sanitize(v) for v in obj]

        elif isinstance(obj, np.ndarray):
            return obj.tolist()

        elif isinstance(obj, np.integer):
            return int(obj)

        elif isinstance(obj, np.floating):
            return float(obj)

        return obj

    # ==========================
    # 📍 APEXES
    # ==========================
    def _calculate_ideal_apexes(self) -> List[Dict]:
        apexes = []

        for corner in self.corners:
            start = int(corner["start_idx"])
            end = int(corner["end_idx"])

            segment = self.curvatures[start:end]
            apex_local = int(np.argmax(segment))
            apex_global = int(start + apex_local)

            apexes.append({
                "corner_id": int(corner["corner_id"]),
                "apex_idx": int(apex_global),
                "apex_x": float(self.centerline_x[apex_global]),
                "apex_y": float(self.centerline_y[apex_global]),
                "curvature": float(segment[apex_local])
            })

        return apexes

    # ==========================
    # 🛣 RACELINE
    # ==========================
    def _generate_racing_line(self, apexes: List[Dict]) -> np.ndarray:
        control_points = []

        for apex in apexes:
            control_points.append([apex["apex_x"], apex["apex_y"]])

        control_points = np.array(control_points)

        tck, _ = splprep([control_points[:, 0], control_points[:, 1]], s=0, per=True)
        u_new = np.linspace(0, 1, len(self.centerline_x))
        x, y = splev(u_new, tck)

        return np.column_stack([x, y])

    # ==========================
    # 🚀 SPEED
    # ==========================
    def _calculate_ideal_speeds(self, trajectory: np.ndarray) -> np.ndarray:
        """
        Calcula velocidades ideais com física real:
        - Limite de grip lateral (curvas)
        - Forward pass (aceleração)
        - Backward pass (frenagem)
        """

        # ==========================
        # ⚙️ PARÂMETROS FÍSICOS
        # ==========================
        mu = 1.6          # coeficiente de atrito (slicks)
        g = 9.81
        max_speed = 320 / 3.6  # m/s
        accel = 8.0       # m/s² (aceleração)
        brake = 12.0      # m/s² (frenagem)

        # ==========================
        # 📐 CURVATURA
        # ==========================
        curvatures = self._calculate_curvature(trajectory)
        n = len(curvatures)

        speeds = np.zeros(n)

        # ==========================
        # 🧠 LIMITE LATERAL (CURVAS)
        # ==========================
        for i, c in enumerate(curvatures):
            if c < 1e-6:
                speeds[i] = max_speed
            else:
                r = 1 / c
                v = np.sqrt(mu * g * r)  # m/s
                speeds[i] = min(v, max_speed)

        # ==========================
        # 📏 DISTÂNCIA ENTRE PONTOS
        # ==========================
        ds = np.linalg.norm(np.diff(trajectory, axis=0), axis=1)
        ds = np.append(ds, ds[-1])  # manter tamanho consistente

        # ==========================
        # 🚀 FORWARD PASS (ACELERAÇÃO)
        # ==========================
        for i in range(1, n):
            v_prev = speeds[i - 1]
            v_max = np.sqrt(v_prev**2 + 2 * accel * ds[i - 1])
            speeds[i] = min(speeds[i], v_max)

        # ==========================
        # 🛑 BACKWARD PASS (FRENAGEM)
        # ==========================
        for i in range(n - 2, -1, -1):
            v_next = speeds[i + 1]
            v_max = np.sqrt(v_next**2 + 2 * brake * ds[i])
            speeds[i] = min(speeds[i], v_max)

        # Converter para km/h
        return speeds * 3.6
    def _calculate_trajectory_curvature(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """
        Calcula a curvatura de um array de coordenadas x, y.
        (Você já tem uma função parecida, mas precisamos garantir que ela rode na raceline, não na centerline)
        """
        dx = np.gradient(x)
        dy = np.gradient(y)
        ddx = np.gradient(dx)
        ddy = np.gradient(dy)
        
        num = np.abs(dx * ddy - dy * ddx)
        den = (dx**2 + dy**2) ** (3/2)
        den[den == 0] = 1e-10  # Prevenir divisão por zero
        
        return num / den

    def _calculate_curvature(self, traj):
        dx = np.gradient(traj[:, 0])
        dy = np.gradient(traj[:, 1])
        ddx = np.gradient(dx)
        ddy = np.gradient(dy)

        num = np.abs(dx * ddy - dy * ddx)
        den = (dx**2 + dy**2) ** (3/2)
        den[den == 0] = 1e-10

        return num / den

    # ==========================
    # 🎮 INPUTS
    # ==========================
    def _calculate_ideal_inputs(self, speeds):
        throttle = np.zeros(len(speeds))
        brake = np.zeros(len(speeds))

        for i in range(1, len(speeds)):
            diff = speeds[i] - speeds[i - 1]

            if diff > 0:
                throttle[i] = min(100, diff * 5)
            elif diff < -1:
                brake[i] = min(100, abs(diff) * 5)
            else:
                throttle[i] = 50

        return {"throttle": throttle, "brake": brake}

    # ==========================
    # ⏱ TEMPO
    # ==========================
    def _estimate_lap_time(self, traj, speeds):
        dist = np.linalg.norm(np.diff(traj, axis=0), axis=1)
        speeds = speeds[:-1] / 3.6
        speeds[speeds == 0] = 1
        return float(np.sum(dist / speeds))

    def _calculate_distances(self, traj):
        dist = np.linalg.norm(np.diff(traj, axis=0), axis=1)
        return np.concatenate([[0], np.cumsum(dist)])

    # ==========================
    # 📊 INSIGHTS (simplificado)
    # ==========================
    def _generate_insights(self, player_data, ideal_speeds):
        return ["Raceline gerada com sucesso"]

    def _identify_improvements(self, player_data, ideal_speeds):
        return []
    
    def _enforce_track_limits(self, trajectory: np.ndarray, margin: float = 1.0) -> np.ndarray:
        # ==========================\n    # 🚧 LIMITES DE PISTA\n    # ==========================\n    def _enforce_track_limits(self, trajectory: np.ndarray, margin: float = 1.0) -> np.ndarray:
        """
        Garante que a linha gerada pela IA nunca ultrapasse as bordas da pista.
        margin: Margem de segurança em metros (1.0 = metade do carro)
        """
        clamped_trajectory = np.zeros_like(trajectory)

        for i, point in enumerate(trajectory):
            # 1. Encontrar o ponto mais próximo na centerline
            px, py = point[0], point[1]
            distances = np.sqrt((self.centerline_x - px)**2 + (self.centerline_y - py)**2)
            idx = np.argmin(distances)
            
            # Coordenadas da pista neste ponto exato
            lx, ly = self.left_edge_x[idx], self.left_edge_y[idx]
            rx, ry = self.right_edge_x[idx], self.right_edge_y[idx]
            
            # 2. Criar um vetor que vai da borda esquerda até a borda direita
            track_vec = np.array([rx - lx, ry - ly])
            track_width = np.linalg.norm(track_vec)
            
            # Proteção: se a pista não tiver largura, mantém o ponto original
            if track_width < 0.1:
                clamped_trajectory[i] = point
                continue
                
            track_dir = track_vec / track_width
            
            # 3. Projetar o ponto da IA neste vetor transversal
            point_vec = np.array([px - lx, py - ly])
            projection = np.dot(point_vec, track_dir)
            
            # 4. O SEGREDO: Limitar o ponto para ficar dentro das bordas!
            # A projeção não pode ser menor que a margem, nem maior que a largura da pista - margem
            clamped_projection = np.clip(projection, margin, track_width - margin)
            
            # 5. Reconstruir a coordenada X, Y com base no limite corrigido
            new_x = lx + track_dir[0] * clamped_projection
            new_y = ly + track_dir[1] * clamped_projection
            
            clamped_trajectory[i] = [new_x, new_y]
            
        return clamped_trajectory

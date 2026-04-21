"""
IA de Raceline Ideal
Baseada em princípios REAIS de corrida, não em valores mágicos ou scaling arbitrário

Princípios:
1. Racing line: Outside → Apex → Outside
2. Maximizar raio de curva = maior velocidade
3. Minimizar frenagem total
4. Conservar momentum
5. Otimizar entrada/saída de curvas
"""
import numpy as np
from typing import Dict, List, Tuple
from scipy.interpolate import splprep, splev
from scipy.optimize import minimize


class RacelineAI:
    """
    Gerador de raceline ideal baseado em física e análise da pista
    """
    
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
        
    def generate_optimal_raceline(self, player_data: Dict) -> Dict:
        """
        Gera raceline ideal analisando:
        1. Geometria da pista
        2. Performance do jogador
        3. Princípios de física
        
        Args:
            player_data: Telemetria do jogador
        
        Returns:
            Dict com raceline ideal + insights
        """
        # 1. Calcular apex ideal para cada curva
        ideal_apexes = self._calculate_ideal_apexes()
        
        # 2. Gerar trajetória ideal (outside → apex → outside)
        ideal_trajectory = self._generate_racing_line(ideal_apexes)
        
        # 3. Calcular velocidade ideal em cada ponto
        ideal_speeds = self._calculate_ideal_speeds(ideal_trajectory)
        
        # 4. Calcular throttle/brake ideais
        ideal_inputs = self._calculate_ideal_inputs(ideal_speeds)
        
        # 5. Estimar tempo de volta
        estimated_time = self._estimate_lap_time(ideal_trajectory, ideal_speeds)
        
        # 6. Comparar com jogador e gerar insights
        insights = self._generate_insights(player_data, ideal_trajectory, ideal_speeds)
        
        # 7. Calcular distância ao longo da raceline
        distances = self._calculate_distances(ideal_trajectory)
        
        return {
            "trajectory": {
                "x": ideal_trajectory[:, 0].tolist(),
                "z": ideal_trajectory[:, 1].tolist(),
                "distance": distances.tolist()
            },
            "speed": ideal_speeds.tolist(),
            "throttle": ideal_inputs["throttle"].tolist(),
            "brake": ideal_inputs["brake"].tolist(),
            "estimated_time": estimated_time,
            "apexes": ideal_apexes,
            "insights": insights,
            "improvements": self._identify_improvements(player_data, ideal_speeds, insights)
        }
    
    def _calculate_ideal_apexes(self) -> List[Dict]:
        """
        Calcula apex geométrico ideal para cada curva
        
        Apex ideal = ponto que maximiza raio de curva
        """
        ideal_apexes = []
        
        for corner in self.corners:
            start_idx = corner["start_idx"]
            end_idx = corner["end_idx"]
            
            # Segmento da curva
            curve_x = self.centerline_x[start_idx:end_idx]
            curve_y = self.centerline_y[start_idx:end_idx]
            curvatures_segment = self.curvatures[start_idx:end_idx]
            
            # Apex = ponto de máxima curvatura
            apex_local_idx = np.argmax(curvatures_segment)
            apex_global_idx = start_idx + apex_local_idx
            
            # Calcular posição ideal do apex (mais próximo da borda interna)
            # Determinar se curva é para esquerda ou direita
            direction = self._determine_corner_direction(start_idx, end_idx)
            
            # Posição ideal: 20-40% da largura da pista a partir da borda interna
            # (carros de F1 geralmente cortam apex)
            apex_offset = self._calculate_apex_offset(corner, direction)
            
            apex_x = curve_x[apex_local_idx] + apex_offset[0]
            apex_y = curve_y[apex_local_idx] + apex_offset[1]
            
            ideal_apexes.append({
                "corner_id": corner["corner_id"],
                "apex_idx": apex_global_idx,
                "apex_x": float(apex_x),
                "apex_y": float(apex_y),
                "direction": direction,
                "curvature": float(curvatures_segment[apex_local_idx]),
                "recommended_speed": self._calculate_corner_speed(curvatures_segment[apex_local_idx])
            })
        
        return ideal_apexes
    
    def _determine_corner_direction(self, start_idx: int, end_idx: int) -> str:
        """Determina se curva é para esquerda ou direita"""
        # Calcular cross product do vetor tangente
        mid_idx = (start_idx + end_idx) // 2
        
        v1 = np.array([
            self.centerline_x[mid_idx] - self.centerline_x[start_idx],
            self.centerline_y[mid_idx] - self.centerline_y[start_idx]
        ])
        
        v2 = np.array([
            self.centerline_x[end_idx] - self.centerline_x[mid_idx],
            self.centerline_y[end_idx] - self.centerline_y[mid_idx]
        ])
        
        cross = np.cross(v1, v2)
        return "left" if cross > 0 else "right"
    
    def _calculate_apex_offset(self, corner: Dict, direction: str) -> np.ndarray:
        """
        Calcula offset do apex em relação à centerline
        
        Apex ideal: 20-40% da largura a partir da borda interna
        """
        apex_idx = corner["apex_idx"]
        
        # Vetor normal à pista
        dx = np.gradient(self.centerline_x)[apex_idx]
        dy = np.gradient(self.centerline_y)[apex_idx]
        norm = np.hypot(dx, dy)
        nx = -dy / norm
        ny = dx / norm
        
        # Largura da pista no apex
        width_left = self.track_data["width_left"][apex_idx]
        width_right = self.track_data["width_right"][apex_idx]
        
        # Offset: 30% da largura em direção à borda interna
        offset_factor = 0.3
        
        if direction == "left":
            # Curva à esquerda -> apex próximo da borda direita
            offset = np.array([nx, ny]) * (-width_right * offset_factor)
        else:
            # Curva à direita -> apex próximo da borda esquerda
            offset = np.array([nx, ny]) * (width_left * offset_factor)
        
        return offset
    
    def _generate_racing_line(self, apexes: List[Dict]) -> np.ndarray:
        """
        Gera trajetória ideal: Outside → Apex → Outside
        
        Usa spline suave passando pelos apexes
        """
        n_points = len(self.centerline_x)
        
        # Pontos de controle da raceline
        control_points = []
        
        # Adicionar pontos entre curvas (retas)
        for i in range(len(apexes)):
            current_apex = apexes[i]
            next_apex = apexes[(i + 1) % len(apexes)]
            
            # Apex atual
            control_points.append([current_apex["apex_x"], current_apex["apex_y"]])
            
            # Ponto de saída (outside após apex)
            exit_idx = (current_apex["apex_idx"] + (next_apex["apex_idx"] - current_apex["apex_idx"]) // 3) % n_points
            
            # Outside = usar borda oposta
            if current_apex["direction"] == "left":
                exit_x = self.left_edge_x[exit_idx]
                exit_y = self.left_edge_y[exit_idx]
            else:
                exit_x = self.right_edge_x[exit_idx]
                exit_y = self.right_edge_y[exit_idx]
            
            control_points.append([exit_x, exit_y])
            
            # Ponto de entrada (outside antes do próximo apex)
            entry_idx = (next_apex["apex_idx"] - (next_apex["apex_idx"] - current_apex["apex_idx"]) // 3) % n_points
            
            if next_apex["direction"] == "left":
                entry_x = self.left_edge_x[entry_idx]
                entry_y = self.left_edge_y[entry_idx]
            else:
                entry_x = self.right_edge_x[entry_idx]
                entry_y = self.right_edge_y[entry_idx]
            
            control_points.append([entry_x, entry_y])
        
        # Converter para array
        control_points = np.array(control_points)
        
        # Criar spline suave
        tck, u = splprep([control_points[:, 0], control_points[:, 1]], s=0, per=True)
        
        # Interpolar para n_points
        u_new = np.linspace(0, 1, n_points)
        x_smooth, y_smooth = splev(u_new, tck)
        
        return np.column_stack([x_smooth, y_smooth])
    
    def _calculate_ideal_speeds(self, trajectory: np.ndarray) -> np.ndarray:
        """
        Calcula velocidade ideal em cada ponto da trajetória
        
        Baseado em:
        1. Curvatura local (v² = μ * g * r)
        2. Reta vs curva
        3. Conservação de energia
        """
        n_points = len(trajectory)
        speeds = np.zeros(n_points)
        
        # Calcular curvatura da raceline ideal
        raceline_curvatures = self._calculate_trajectory_curvature(trajectory)
        
        # Parâmetros físicos (ajustáveis)
        MAX_SPEED = 340  # km/h (velocidade máxima em reta)
        MIN_SPEED = 60   # km/h (velocidade mínima em curva fechada)
        GRIP_FACTOR = 1.8  # Coeficiente de grip (F1 ~1.5-2.0)
        G = 9.81  # m/s²
        
        for i in range(n_points):
            curvature = raceline_curvatures[i]
            
            if curvature < 0.001:  # Reta
                speeds[i] = MAX_SPEED
            else:
                # Velocidade máxima em curva: v = sqrt(μ * g * r)
                # r = 1/curvature
                radius = 1.0 / curvature
                
                # Converter para km/h
                v_max_ms = np.sqrt(GRIP_FACTOR * G * radius)
                v_max_kmh = v_max_ms * 3.6
                
                speeds[i] = max(MIN_SPEED, min(MAX_SPEED, v_max_kmh))
        
        # Suavizar velocidades (simular aceleração/frenagem realistas)
        speeds = self._smooth_speeds(speeds)
        
        return speeds
    
    def _calculate_trajectory_curvature(self, trajectory: np.ndarray) -> np.ndarray:
        """Calcula curvatura da trajetória ideal"""
        x = trajectory[:, 0]
        y = trajectory[:, 1]
        
        dx = np.gradient(x)
        dy = np.gradient(y)
        ddx = np.gradient(dx)
        ddy = np.gradient(dy)
        
        numerator = np.abs(dx * ddy - dy * ddx)
        denominator = (dx**2 + dy**2)**(3/2)
        denominator[denominator == 0] = 1e-10
        
        return numerator / denominator
    
    def _smooth_speeds(self, speeds: np.ndarray) -> np.ndarray:
        """
        Suaviza perfil de velocidade considerando aceleração/frenagem realistas
        
        Limites:
        - Aceleração máxima: ~1.5 g
        - Frenagem máxima: ~4.5 g
        """
        smoothed = speeds.copy()
        MAX_ACCEL = 14.715  # m/s² (1.5g)
        MAX_BRAKE = 44.145  # m/s² (4.5g)
        
        # Forward pass (limitar aceleração)
        for i in range(1, len(smoothed)):
            dt = 0.05  # ~50ms entre pontos (ajustar conforme telemetria)
            max_speed_gain = (MAX_ACCEL * dt) * 3.6  # converter m/s para km/h
            smoothed[i] = min(smoothed[i], smoothed[i-1] + max_speed_gain)
        
        # Backward pass (limitar frenagem)
        for i in range(len(smoothed)-2, -1, -1):
            dt = 0.05
            max_speed_loss = (MAX_BRAKE * dt) * 3.6
            smoothed[i] = min(smoothed[i], smoothed[i+1] + max_speed_loss)
        
        return smoothed
    
    def _calculate_corner_speed(self, curvature: float) -> float:
        """Calcula velocidade recomendada para uma curva baseada na curvatura"""
        if curvature < 0.001:
            return 340.0
        
        radius = 1.0 / curvature
        GRIP = 1.8
        G = 9.81
        v_ms = np.sqrt(GRIP * G * radius)
        return min(340.0, max(60.0, v_ms * 3.6))
    
    def _calculate_ideal_inputs(self, speeds: np.ndarray) -> Dict:
        """
        Calcula throttle e brake ideais baseados no perfil de velocidade
        """
        throttle = np.zeros(len(speeds))
        brake = np.zeros(len(speeds))
        
        for i in range(1, len(speeds)):
            speed_diff = speeds[i] - speeds[i-1]
            
            if speed_diff > 0:  # Acelerando
                # Throttle proporcional à aceleração desejada
                throttle[i] = min(100.0, (speed_diff / 10.0) * 100)
                brake[i] = 0.0
            elif speed_diff < -1:  # Freando
                # Brake proporcional à desaceleração desejada
                brake[i] = min(100.0, abs(speed_diff / 15.0) * 100)
                throttle[i] = 0.0
            else:  # Manter velocidade
                throttle[i] = 50.0
                brake[i] = 0.0
        
        return {"throttle": throttle, "brake": brake}
    
    def _estimate_lap_time(self, trajectory: np.ndarray, speeds: np.ndarray) -> float:
        """Estima tempo de volta baseado na trajetória e velocidades"""
        distances = np.diff(trajectory, axis=0)
        segment_lengths = np.linalg.norm(distances, axis=1)
        
        # Velocidade média de cada segmento
        avg_speeds = (speeds[:-1] + speeds[1:]) / 2
        
        # Tempo = distância / velocidade
        # Converter km/h para m/s
        avg_speeds_ms = avg_speeds / 3.6
        avg_speeds_ms[avg_speeds_ms == 0] = 1  # Evitar divisão por zero
        
        segment_times = segment_lengths / avg_speeds_ms
        total_time = np.sum(segment_times)
        
        return float(total_time)
    
    def _calculate_distances(self, trajectory: np.ndarray) -> np.ndarray:
        """Calcula distância acumulada ao longo da trajetória"""
        distances = np.diff(trajectory, axis=0)
        segment_lengths = np.linalg.norm(distances, axis=1)
        cumulative = np.concatenate([[0], np.cumsum(segment_lengths)])
        return cumulative
    
    def _generate_insights(
        self, 
        player_data: Dict, 
        ideal_trajectory: np.ndarray, 
        ideal_speeds: np.ndarray
    ) -> List[str]:
        """
        Gera insights comparando jogador vs IA
        """
        insights = []
        
        player_speeds = np.array(player_data["best_lap_data"]["speed"])
        player_avg_speed = np.mean(player_speeds)
        ai_avg_speed = np.mean(ideal_speeds)
        
        # Análise de velocidade
        if player_avg_speed < ai_avg_speed * 0.92:
            insights.append(f"Velocidade média {(ai_avg_speed - player_avg_speed):.1f} km/h abaixo do ideal. Trabalhe aceleração nas saídas de curva.")
        
        # Análise de frenagem
        player_brake = np.array(player_data["best_lap_data"]["brake"])
        total_brake_time = (player_brake > 10).sum()
        
        if total_brake_time > len(player_speeds) * 0.25:
            insights.append("Frenando em excesso. Tente levar mais velocidade nas curvas e frenar mais tarde.")
        
        # Análise de throttle
        player_throttle = np.array(player_data["best_lap_data"]["throttle"])
        full_throttle_pct = (player_throttle > 95).sum() / len(player_throttle) * 100
        
        if full_throttle_pct < 40:
            insights.append(f"Apenas {full_throttle_pct:.1f}% do tempo em full throttle. Ataque mais nas retas.")
        
        # Análise de estilo
        driving_style = player_data["driving_style"]["classification"]
        if driving_style == "agressivo":
            insights.append("Estilo agressivo detectado. Transições mais suaves podem ganhar tempo.")
        elif driving_style == "conservador":
            insights.append("Estilo conservador. Pode arriscar mais nas curvas.")
        
        return insights
    
    def _identify_improvements(
        self, 
        player_data: Dict, 
        ideal_speeds: np.ndarray, 
        insights: List[str]
    ) -> List[Dict]:
        """
        Identifica áreas específicas onde o jogador pode melhorar
        """
        improvements = []
        
        # Comparar velocidade em cada curva
        for corner in self.corners:
            start = corner["start_idx"]
            end = corner["end_idx"]
            
            # Velocidade do jogador nesta curva (aproximação)
            # Seria mais preciso mapear pontos player → track
            player_speeds = np.array(player_data["best_lap_data"]["speed"])
            
            # Se temos menos pontos que a pista, interpolar
            if len(player_speeds) < len(ideal_speeds):
                player_idx = int(start * len(player_speeds) / len(ideal_speeds))
                player_corner_speed = player_speeds[player_idx] if player_idx < len(player_speeds) else 0
            else:
                player_corner_speed = player_speeds[start]
            
            ai_corner_speed = ideal_speeds[start]
            
            if player_corner_speed < ai_corner_speed * 0.85:
                improvements.append({
                    "corner": corner["corner_id"],
                    "type": "speed",
                    "current": float(player_corner_speed),
                    "target": float(ai_corner_speed),
                    "gain": float(ai_corner_speed - player_corner_speed),
                    "suggestion": f"Curva {corner['corner_id']}: Carregue {ai_corner_speed - player_corner_speed:.0f} km/h a mais"
                })
        
        return improvements
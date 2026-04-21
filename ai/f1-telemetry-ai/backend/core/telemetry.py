"""
Módulo de processamento de telemetria
Valida, limpa e processa dados de telemetria do jogador
"""
import pandas as pd
import numpy as np
from typing import Dict, List


class TelemetryProcessor:
    """Processa telemetria do jogador"""
    
    def process_telemetry(self, df: pd.DataFrame, track_data: Dict) -> Dict:
        """
        Processa CSV de telemetria do jogador
        
        Args:
            df: DataFrame com telemetria
            track_data: Dados do trackmap
        
        Returns:
            Dict com telemetria processada e melhor volta
        """
        # Validar e normalizar colunas
        df = self._normalize_columns(df)
        
        # Validar campos obrigatórios
        required = ['session_time', 'lap', 'pos_x', 'pos_z', 'speed', 'throttle', 'brake']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Colunas faltando no CSV: {missing}")
        
        # Limpar dados
        df = df.dropna(subset=required)
        
        # Identificar melhor volta
        best_lap_data = self._find_best_lap(df)
        
        # Calcular distância percorrida
        best_lap_data = self._calculate_distance(best_lap_data)
        
        # Validar se raceline está dentro da pista
        violations = self._check_track_limits(best_lap_data, track_data)
        
        # Calcular métricas
        metrics = self._calculate_metrics(best_lap_data)
        
        # Analisar driving style
        driving_style = self._analyze_driving_style(best_lap_data)
        
        return {
            "total_laps": len(df['lap'].unique()),
            "best_lap_number": int(best_lap_data['lap'].iloc[0]),
            "best_lap_time": float(best_lap_data['session_time'].iloc[-1] - best_lap_data['session_time'].iloc[0]),
            "best_lap_data": {
                "x": best_lap_data['pos_x'].tolist(),
                "z": best_lap_data['pos_z'].tolist(),
                "speed": best_lap_data['speed'].tolist(),
                "throttle": (best_lap_data['throttle'] * 100).tolist(),  # Converter para %
                "brake": (best_lap_data['brake'] * 100).tolist(),
                "distance": best_lap_data['distance'].tolist()
            },
            "track_limit_violations": violations,
            "metrics": metrics,
            "driving_style": driving_style
        }
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza nomes de colunas (case insensitive, aliases)"""
        # Mapeamento de aliases
        col_map = {
            'time': 'session_time',
            't': 'session_time',
            'x': 'pos_x',
            'z': 'pos_z',
            'y': 'pos_z',  # Alguns jogos usam Y em vez de Z
            'pos_y': 'pos_z'
        }
        
        # Renomear colunas
        df.columns = df.columns.str.strip().str.lower()
        df = df.rename(columns=col_map)
        
        return df
    
    def _find_best_lap(self, df: pd.DataFrame) -> pd.DataFrame:
        """Identifica e retorna dados da melhor volta"""
        laps = {}
        
        for lap_num in df['lap'].unique():
            lap_data = df[df['lap'] == lap_num].copy()
            
            # Calcular tempo da volta
            if len(lap_data) < 10:  # Volta muito curta, ignorar
                continue
            
            lap_time = lap_data['session_time'].max() - lap_data['session_time'].min()
            laps[lap_num] = (lap_time, lap_data)
        
        if not laps:
            raise ValueError("Nenhuma volta válida encontrada")
        
        # Melhor volta = menor tempo
        best_lap_num = min(laps.keys(), key=lambda k: laps[k][0])
        best_lap_df = laps[best_lap_num][1].copy()
        
        # Normalizar tempo para começar em 0
        t0 = best_lap_df['session_time'].min()
        best_lap_df['session_time'] = best_lap_df['session_time'] - t0
        
        return best_lap_df.reset_index(drop=True)
    
    def _calculate_distance(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula distância percorrida ao longo da volta"""
        dx = df['pos_x'].diff().fillna(0)
        dz = df['pos_z'].diff().fillna(0)
        delta_dist = np.sqrt(dx**2 + dz**2)
        df['distance'] = delta_dist.cumsum()
        return df
    
    def _check_track_limits(self, df: pd.DataFrame, track_data: Dict) -> Dict:
        """
        Verifica se o jogador saiu dos limites da pista
        
        Método:
        1. Para cada ponto da telemetria, encontrar ponto mais próximo na centerline
        2. Verificar se está dentro das bordas
        """
        violations = {
            "total": 0,
            "positions": []
        }
        
        # Converter track data para arrays
        track_x = np.array(track_data["centerline"]["x"])
        track_y = np.array(track_data["centerline"]["y"])
        left_x = np.array(track_data["left_edge"]["x"])
        left_y = np.array(track_data["left_edge"]["y"])
        right_x = np.array(track_data["right_edge"]["x"])
        right_y = np.array(track_data["right_edge"]["y"])
        
        for idx, row in df.iterrows():
            player_x = row['pos_x']
            player_z = row['pos_z']
            
            # Encontrar ponto mais próximo na centerline
            distances = np.sqrt((track_x - player_x)**2 + (track_y - player_z)**2)
            closest_idx = np.argmin(distances)
            
            # Verificar se está fora das bordas
            # (simplificado - em produção, usar geometria mais precisa)
            left_pt = np.array([left_x[closest_idx], left_y[closest_idx]])
            right_pt = np.array([right_x[closest_idx], right_y[closest_idx]])
            player_pt = np.array([player_x, player_z])
            
            # Distância do player às bordas
            dist_to_left = np.linalg.norm(player_pt - left_pt)
            dist_to_right = np.linalg.norm(player_pt - right_pt)
            track_width = np.linalg.norm(left_pt - right_pt)
            
            # Se player está mais longe das bordas que a largura da pista, violação
            if min(dist_to_left, dist_to_right) > track_width * 0.6:
                violations["total"] += 1
                violations["positions"].append({
                    "distance": float(row['distance']),
                    "time": float(row['session_time'])
                })
        
        return violations
    
    def _calculate_metrics(self, df: pd.DataFrame) -> Dict:
        """Calcula métricas de performance"""
        return {
            "avg_speed": float(df['speed'].mean()),
            "max_speed": float(df['speed'].max()),
            "min_speed": float(df['speed'].min()),
            "avg_throttle": float(df['throttle'].mean() * 100),
            "avg_brake": float(df['brake'].mean() * 100),
            "brake_points": int((df['brake'] > 0.1).sum()),
            "full_throttle_pct": float((df['throttle'] > 0.95).sum() / len(df) * 100),
            "coasting_pct": float(((df['throttle'] < 0.1) & (df['brake'] < 0.1)).sum() / len(df) * 100)
        }
    
    def _analyze_driving_style(self, df: pd.DataFrame) -> Dict:
        """
        Analisa estilo de pilotagem
        - Agressivo: muito freio, throttle on/off
        - Suave: transições graduais
        - Conservador: velocidade média baixa
        """
        # Variação de throttle (transições bruscas vs suaves)
        throttle_changes = df['throttle'].diff().abs().mean()
        brake_changes = df['brake'].diff().abs().mean()
        
        # Classificação
        if throttle_changes > 0.15 or brake_changes > 0.15:
            style = "agressivo"
            desc = "Muitas transições bruscas de throttle/brake"
        elif df['speed'].mean() < df['speed'].max() * 0.65:
            style = "conservador"
            desc = "Velocidade média baixa, pode atacar mais"
        else:
            style = "suave"
            desc = "Transições graduais, bom controle"
        
        return {
            "classification": style,
            "description": desc,
            "throttle_smoothness": float(1 - throttle_changes),
            "brake_smoothness": float(1 - brake_changes)
        }
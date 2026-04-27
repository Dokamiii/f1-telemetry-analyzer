# backend/core/trajectory_ai.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd
from scipy.interpolate import splprep, splev


@dataclass
class TrajectoryResult:
    trajectory_x: List[float]
    trajectory_z: List[float]
    target_speed: List[float]
    segment_loss: List[float]
    estimated_gain_seconds: float
    notes: List[str]


class TrajectoryAI:
    """
    IA leve para TCC:
    - aprende um score por segmento da pista
    - identifica onde o piloto perde tempo
    - gera uma raceline recomendada em cima da geometria da pista

    Requer:
    - track_data no formato já usado no projeto
    - telemetry_data["best_lap_data"] do seu pipeline atual
    """

    def __init__(self, track_data: Dict[str, Any], n_segments: int = 40):
        self.track_data = track_data
        self.n_segments = n_segments

        self.cx = np.asarray(track_data["centerline"]["x"], dtype=float)
        self.cz = np.asarray(track_data["centerline"]["y"], dtype=float)
        self.lx = np.asarray(track_data["left_edge"]["x"], dtype=float)
        self.lz = np.asarray(track_data["left_edge"]["y"], dtype=float)
        self.rx = np.asarray(track_data["right_edge"]["x"], dtype=float)
        self.rz = np.asarray(track_data["right_edge"]["y"], dtype=float)

        self.curv = np.asarray(track_data["curvatures"], dtype=float)
        self.wl = np.asarray(track_data["width_left"], dtype=float)
        self.wr = np.asarray(track_data["width_right"], dtype=float)

        self.coef_: np.ndarray | None = None

    def fit(self, telemetry_data: Dict[str, Any]) -> "TrajectoryAI":
        """
        Treina uma regressão linear simples por segmento.
        O objetivo não é ser "o melhor modelo do mundo", e sim ter
        uma IA clara, defensável e viável para TCC.
        """
        lap = telemetry_data["best_lap_data"]

        lap_x = np.asarray(lap["x"], dtype=float)
        lap_z = np.asarray(lap["z"], dtype=float)
        lap_speed = np.asarray(lap["speed"], dtype=float)
        lap_throttle = np.asarray(lap["throttle"], dtype=float) / 100.0
        lap_brake = np.asarray(lap["brake"], dtype=float) / 100.0

        track_idx = self._map_points_to_track_indices(lap_x, lap_z)
        seg_ids = self._indices_to_segments(track_idx)

        X = []
        y = []

        for seg in range(self.n_segments):
            mask = seg_ids == seg
            if mask.sum() < 3:
                continue

            speed_mean = float(np.mean(lap_speed[mask]))
            throttle_mean = float(np.mean(lap_throttle[mask]))
            brake_mean = float(np.mean(lap_brake[mask]))

            track_points = track_idx[mask]
            curvature_mean = float(np.mean(self.curv[track_points]))
            width_mean = float(np.mean(self.wl[track_points] + self.wr[track_points]))

            # proxy simples de "perda de tempo":
            # mais frenagem + mais curvatura + menos velocidade = mais perda
            loss_proxy = (
                1.8 * curvature_mean
                + 1.2 * brake_mean
                - 0.8 * speed_mean / max(np.max(lap_speed), 1.0)
                + 0.2 * (1.0 - throttle_mean)
            )

            X.append([
                1.0,
                curvature_mean,
                curvature_mean ** 2,
                speed_mean,
                brake_mean,
                throttle_mean,
                width_mean,
            ])
            y.append(loss_proxy)

        if len(X) < 4:
            raise ValueError("Dados insuficientes para treinar a IA de trajetória.")

        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)

        # Ridge simples via equação normal
        lam = 1e-3
        I = np.eye(X.shape[1])
        self.coef_ = np.linalg.solve(X.T @ X + lam * I, X.T @ y)
        return self

    def recommend(self) -> Dict[str, Any]:
        if self.coef_ is None:
            raise RuntimeError("Chame fit() antes de recommend().")

        # score por ponto da pista
        scores = self._segment_scores_from_track()

        # raceline baseada em deslocamento lateral para o lado interno da curva
        x_out, z_out = self._build_raceline_from_scores(scores)

        # velocidade alvo por ponto, limitada por curvatura
        target_speed = self._build_target_speed(scores)

        # estimativa simples de ganho
        estimated_gain = float(np.clip(np.mean(scores) * 12.0, 0.5, 8.0))

        notes = self._build_notes(scores)

        return {
            "trajectory": {
                "x": x_out.tolist(),
                "z": z_out.tolist(),
            },
            "target_speed": target_speed.tolist(),
            "segment_loss": scores.tolist(),
            "estimated_gain_seconds": estimated_gain,
            "notes": notes,
        }

    def _map_points_to_track_indices(self, px: np.ndarray, pz: np.ndarray) -> np.ndarray:
        track = np.column_stack([self.cx, self.cz])
        points = np.column_stack([px, pz])

        idxs = []
        for p in points:
            d = np.sum((track - p) ** 2, axis=1)
            idxs.append(int(np.argmin(d)))
        return np.asarray(idxs, dtype=int)

    def _indices_to_segments(self, track_idx: np.ndarray) -> np.ndarray:
        n = len(self.cx)
        seg_size = max(1, n // self.n_segments)
        return np.clip(track_idx // seg_size, 0, self.n_segments - 1)

    def _segment_scores_from_track(self) -> np.ndarray:
        n = len(self.cx)
        seg_size = max(1, n // self.n_segments)
        scores = np.zeros(self.n_segments, dtype=float)

        for seg in range(self.n_segments):
            start = seg * seg_size
            end = n if seg == self.n_segments - 1 else (seg + 1) * seg_size

            curv_mean = float(np.mean(self.curv[start:end]))
            width_mean = float(np.mean(self.wl[start:end] + self.wr[start:end]))

            # score maior = mais espaço para melhorar
            scores[seg] = 1.5 * curv_mean + 0.15 / max(width_mean, 1.0)

        # normaliza 0..1
        scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-9)
        return scores

    def _build_raceline_from_scores(self, scores: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        n = len(self.cx)
        offsets = np.zeros(n, dtype=float)

        # normal da centerline
        dx = np.gradient(self.cx)
        dz = np.gradient(self.cz)
        norm = np.hypot(dx, dz) + 1e-9
        nx = -dz / norm
        nz = dx / norm

        seg_size = max(1, n // self.n_segments)

        for seg in range(self.n_segments):
            start = seg * seg_size
            end = n if seg == self.n_segments - 1 else (seg + 1) * seg_size

            curv_mean = float(np.mean(self.curv[start:end]))
            width_mean = float(np.mean(self.wl[start:end] + self.wr[start:end]))
            score = float(scores[seg])

            # deslocamento maior onde há mais curvatura e mais perda prevista
            base = 0.10 * width_mean
            extra = 0.22 * width_mean * score
            offset = np.clip(base + extra, 0.0, 0.42 * width_mean)

            # decide o lado interno da curva
            sign = np.sign(np.mean(self.curv[start:end]))
            # curva à esquerda -> desloca para a direita; curva à direita -> esquerda
            offsets[start:end] = -sign * offset

        x_new = self.cx + nx * offsets
        z_new = self.cz + nz * offsets

        # suavização por spline fechada
        pts = np.column_stack([x_new, z_new])
        tck, _ = splprep([pts[:, 0], pts[:, 1]], s=4.0, per=True)
        u_new = np.linspace(0.0, 1.0, n)
        xs, zs = splev(u_new, tck)

        return np.asarray(xs, dtype=float), np.asarray(zs, dtype=float)

    def _build_target_speed(self, scores: np.ndarray) -> np.ndarray:
        n = len(self.cx)
        seg_size = max(1, n // self.n_segments)
        speeds = np.zeros(n, dtype=float)

        for seg in range(self.n_segments):
            start = seg * seg_size
            end = n if seg == self.n_segments - 1 else (seg + 1) * seg_size

            curv_mean = float(np.mean(self.curv[start:end]))
            score = float(scores[seg])

            # física simples: quanto maior a curvatura, menor a velocidade
            if abs(curv_mean) < 1e-6:
                v = 80.0
            else:
                radius = 1.0 / abs(curv_mean)
                v = np.sqrt(max(0.0, 10.5 * radius))

            # penaliza trechos mais críticos
            v *= (1.0 - 0.18 * score)
            speeds[start:end] = np.clip(v, 40.0, 330.0)

        return speeds

    def _build_notes(self, scores: np.ndarray) -> List[str]:
        top = np.argsort(scores)[-5:][::-1]
        notes = []
        for i, seg in enumerate(top, start=1):
            notes.append(f"Trecho {int(seg)+1}: alta chance de ganho de tempo.")
        return notes
"""
F1 Telemetry Analyzer - Backend FastAPI
Sistema completo de análise de telemetria com IA de raceline baseada em princípios reais de corrida
"""
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
from typing import Dict, Any
import io

from core.trackmap import TrackMapGenerator
from core.telemetry import TelemetryProcessor
from core.raceline_ai import RacelineAI

app = FastAPI(
    title="F1 Telemetry Analyzer API",
    description="API para análise de telemetria e geração de raceline ideal com IA",
    version="1.0.0"
)

# CORS - permitir frontend local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# State global (em produção, usar Redis/DB)
app_state = {
    "track_data": None,
    "telemetry_data": None,
    "ai_raceline": None
}


@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "online",
        "message": "F1 Telemetry Analyzer API",
        "version": "1.0.0"
    }


@app.post("/api/upload/track")
async def upload_track(file: UploadFile = File(...)):
    """
    Upload do CSV da pista (track data)
    
    Formato esperado:
    # x_m, y_m, w_tr_right_m, w_tr_left_m
    """
    try:
        # Ler CSV
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        # Validar colunas
        required_cols = ['# x_m', 'y_m', 'w_tr_right_m', 'w_tr_left_m']
        df.columns = df.columns.str.strip()
        
        if not all(col in df.columns for col in required_cols):
            raise HTTPException(
                status_code=400,
                detail=f"CSV inválido. Colunas necessárias: {required_cols}"
            )
        
        # Gerar trackmap
        trackmap_gen = TrackMapGenerator()
        track_data = trackmap_gen.generate_from_csv(df)
        
        # Salvar no state
        app_state["track_data"] = track_data
        
        return {
            "status": "success",
            "message": "Track carregado com sucesso",
            "data": {
                "track_name": track_data["name"],
                "total_points": len(track_data["centerline"]["x"]),
                "track_length": track_data["length_meters"],
                "bounds": track_data["bounds"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload/telemetry")
async def upload_telemetry(file: UploadFile = File(...)):
    """
    Upload do CSV de telemetria do jogador
    
    Formato esperado:
    session_time, lap, pos_x, pos_z, speed, throttle, brake
    """
    try:
        # Verificar se track foi carregado
        if app_state["track_data"] is None:
            raise HTTPException(
                status_code=400,
                detail="Carregue primeiro o CSV da pista (track)"
            )
        
        # Ler CSV
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        # Processar telemetria
        processor = TelemetryProcessor()
        telemetry_data = processor.process_telemetry(df, app_state["track_data"])
        
        # Gerar raceline IA
        ai_engine = RacelineAI(app_state["track_data"])
        ai_raceline = ai_engine.generate_optimal_raceline(telemetry_data)
        
        # Salvar no state
        app_state["telemetry_data"] = telemetry_data
        app_state["ai_raceline"] = ai_raceline
        
        return {
            "status": "success",
            "message": "Telemetria processada com sucesso",
            "data": {
                "total_laps": telemetry_data["total_laps"],
                "best_lap": telemetry_data["best_lap_number"],
                "player_time": telemetry_data["best_lap_time"],
                "ai_time": ai_raceline["estimated_time"],
                "time_gain": telemetry_data["best_lap_time"] - ai_raceline["estimated_time"],
                "insights": ai_raceline["insights"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/track")
async def get_track_data():
    """Retorna dados do trackmap"""
    if app_state["track_data"] is None:
        raise HTTPException(status_code=404, detail="Track não carregado")
    
    return app_state["track_data"]


@app.get("/api/data/telemetry")
async def get_telemetry_data():
    """Retorna dados da telemetria do jogador"""
    if app_state["telemetry_data"] is None:
        raise HTTPException(status_code=404, detail="Telemetria não carregada")
    
    return app_state["telemetry_data"]


@app.get("/api/data/ai-raceline")
async def get_ai_raceline():
    """Retorna raceline ideal gerada pela IA"""
    if app_state["ai_raceline"] is None:
        raise HTTPException(status_code=404, detail="IA raceline não gerada")
    
    return app_state["ai_raceline"]


@app.get("/api/data/comparison")
async def get_comparison():
    """Retorna comparação completa: track + player + IA"""
    if app_state["track_data"] is None:
        raise HTTPException(status_code=404, detail="Track não carregado")
    if app_state["telemetry_data"] is None:
        raise HTTPException(status_code=404, detail="Telemetria não carregada")
    if app_state["ai_raceline"] is None:
        raise HTTPException(status_code=404, detail="IA raceline não gerada")
    
    return {
        "track": app_state["track_data"],
        "player": app_state["telemetry_data"],
        "ai": app_state["ai_raceline"]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
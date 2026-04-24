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
import logging

from core.trackmap import TrackMapGenerator
from core.telemetry import TelemetryProcessor
from core.raceline_ai import RacelineAI
from core.udp_capture import UDPTelemetryCapture
# NOVO: Importando o módulo de track limits
from core.tracklimits import TrackLimitsValidator, validate_lap_track_limits

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="F1 Telemetry Analyzer API",
    description="API para análise de telemetria e geração de raceline ideal com IA",
    version="1.0.0"
)

# CORS - permitir frontend local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# State global (em produção, usar Redis/DB)
app_state = {
    "track_data": None,
    "telemetry_data": None,
    "ai_raceline": None,
    "track_limits": None,  # NOVO: Estado para armazenar validação da volta
    "udp_capture": None  # Instância de captura UDP
}


def load_example_data():
    """
    Carrega automaticamente dados de exemplo ao iniciar o servidor
    Para facilitar testes sem necessidade de upload manual
    """
    from pathlib import Path
    
    try:
        # Caminhos dos arquivos de exemplo
        base_dir = Path(__file__).parent.parent
        track_csv = base_dir / "data" / "SaoPaulo.csv"
        telemetry_csv = base_dir / "data" / "example_telemetry.csv"
        
        logger.info("=" * 60)
        logger.info("CARREGANDO DADOS DE EXEMPLO AUTOMATICAMENTE")
        logger.info("=" * 60)
        
        # 1. Carregar pista
        if track_csv.exists():
            logger.info(f"Carregando pista: {track_csv}")
            df_track = pd.read_csv(track_csv)
            
            trackmap_gen = TrackMapGenerator()
            track_data = trackmap_gen.generate_from_csv(df_track)
            app_state["track_data"] = track_data
            
            logger.info(f"✅ Pista carregada: {track_data['name']}")
            logger.info(f"   - Pontos: {track_data['total_points']}")
            logger.info(f"   - Comprimento: {track_data['length_meters']:.0f}m")
            logger.info(f"   - Curvas detectadas: {len(track_data['corners'])}")
        else:
            logger.warning(f"❌ Arquivo de pista não encontrado: {track_csv}")
            return
        
        # 2. Carregar telemetria
        if telemetry_csv.exists():
            logger.info(f"Carregando telemetria: {telemetry_csv}")
            df_telemetry = pd.read_csv(telemetry_csv)
            
            processor = TelemetryProcessor()
            telemetry_data = processor.process_telemetry(df_telemetry, app_state["track_data"])
            app_state["telemetry_data"] = telemetry_data
            
            logger.info(f"✅ Telemetria processada")
            logger.info(f"   - Voltas: {telemetry_data['total_laps']}")
            logger.info(f"   - Melhor volta: {telemetry_data['best_lap_number']}")
            logger.info(f"   - Tempo: {telemetry_data['best_lap_time']:.3f}s")
            
            # NOVO: 3. Validar Track Limits na telemetria carregada
            logger.info("Validando Track Limits...")
            lap_data_for_validation = {
                'pos_x': df_telemetry['pos_x'].values if 'pos_x' in df_telemetry else [],
                'pos_z': df_telemetry['pos_z'].values if 'pos_z' in df_telemetry else []
            }
            track_limits_result = validate_lap_track_limits(lap_data_for_validation, app_state["track_data"])
            app_state["track_limits"] = track_limits_result
            
            if track_limits_result["valid"]:
                logger.info(f"✅ Track Limits: {track_limits_result['reason']}")
            else:
                logger.warning(f"❌ Track Limits: {track_limits_result['reason']}")
            
            # 4. Gerar raceline IA
            logger.info("Gerando raceline IA...")
            ai_engine = RacelineAI(app_state["track_data"])
            ai_raceline = ai_engine.generate_optimal_raceline(telemetry_data)
            app_state["ai_raceline"] = ai_raceline
            
            logger.info(f"✅ Raceline IA gerada")
            logger.info(f"   - Tempo IA: {ai_raceline['estimated_time']:.3f}s")
            logger.info(f"   - Ganho potencial: {telemetry_data['best_lap_time'] - ai_raceline['estimated_time']:.3f}s")
            
            logger.info("=" * 60)
            logger.info("DADOS DE EXEMPLO PRONTOS PARA USO!")
            logger.info("Acesse http://localhost:5173 para visualizar")
            logger.info("=" * 60)
            
        else:
            logger.warning(f"❌ Arquivo de telemetria não encontrado: {telemetry_csv}")
    
    except Exception as e:
        logger.error(f"❌ Erro ao carregar dados de exemplo: {str(e)}", exc_info=True)


@app.on_event("startup")
async def startup_event():
    """Executado ao iniciar o servidor"""
    logger.info("🚀 Iniciando F1 Telemetry Analyzer API...")
    load_example_data()


@app.get("/")
async def root():
    """Health check"""
    has_data = all([
        app_state["track_data"] is not None,
        app_state["telemetry_data"] is not None,
        app_state["ai_raceline"] is not None
    ])
    
    return {
        "status": "online",
        "message": "F1 Telemetry Analyzer API",
        "version": "1.1.0",
        "example_data_loaded": has_data,
        "endpoints": {
            "track": "/api/data/track",
            "telemetry": "/api/data/telemetry",
            "ai_raceline": "/api/data/ai-raceline",
            "track_limits": "/api/data/track-limits", # NOVO
            "comparison": "/api/data/comparison"
        }
    }


@app.post("/api/upload/track")
async def upload_track(file: UploadFile = File(...)):
    """
    Upload do CSV da pista (track data)
    """
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        required_cols = ['# x_m', 'y_m', 'w_tr_right_m', 'w_tr_left_m']
        df.columns = df.columns.str.strip()
        
        if not all(col in df.columns for col in required_cols):
            raise HTTPException(
                status_code=400,
                detail=f"CSV inválido. Colunas necessárias: {required_cols}"
            )
        
        trackmap_gen = TrackMapGenerator()
        track_data = trackmap_gen.generate_from_csv(df)
        
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
    """
    try:
        if app_state["track_data"] is None:
            raise HTTPException(
                status_code=400,
                detail="Carregue primeiro o CSV da pista (track)"
            )
        
        logger.info(f"Recebendo upload de telemetria: {file.filename}")
        
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="CSV de telemetria está vazio"
            )
        
        # Processar telemetria
        processor = TelemetryProcessor()
        telemetry_data = processor.process_telemetry(df, app_state["track_data"])
        logger.info("Telemetria processada com sucesso")

        # NOVO: Validar Track Limits
        lap_data_for_validation = {
            'pos_x': df['pos_x'].values if 'pos_x' in df else [],
            'pos_z': df['pos_z'].values if 'pos_z' in df else []
        }
        track_limits_result = validate_lap_track_limits(lap_data_for_validation, app_state["track_data"])
        logger.info(f"Track limits validado: Válido={track_limits_result['valid']}")
        
        # Gerar raceline IA
        logger.info("Gerando raceline IA...")
        ai_engine = RacelineAI(app_state["track_data"])
        ai_raceline = ai_engine.generate_optimal_raceline(telemetry_data)
        logger.info("Raceline IA gerada com sucesso")
        
        # Salvar no state
        app_state["telemetry_data"] = telemetry_data
        app_state["ai_raceline"] = ai_raceline
        app_state["track_limits"] = track_limits_result # Salvar validação
        
        return {
            "status": "success",
            "message": "Telemetria processada com sucesso",
            "data": {
                "total_laps": telemetry_data["total_laps"],
                "best_lap": telemetry_data["best_lap_number"],
                "player_time": telemetry_data["best_lap_time"],
                "ai_time": ai_raceline["estimated_time"],
                "time_gain": telemetry_data["best_lap_time"] - ai_raceline["estimated_time"],
                "track_limits_valid": track_limits_result["valid"], # NOVO
                "track_limits_reason": track_limits_result["reason"], # NOVO
                "insights": ai_raceline["insights"]
            }
        }
        
    except ValueError as ve:
        logger.error(f"Erro de validação: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Erro ao processar telemetria: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao processar telemetria: {str(e)}")


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


# NOVO ENDPOINT EXCLUSIVO PARA TRACK LIMITS
@app.get("/api/data/track-limits")
async def get_track_limits():
    """Retorna o resultado da validação dos limites de pista"""
    if app_state["track_limits"] is None:
        raise HTTPException(status_code=404, detail="Validação de track limits não processada")
    
    return app_state["track_limits"]


@app.get("/api/data/comparison")
async def get_comparison():
    """Retorna comparação completa: track + player + IA + Track Limits"""
    if app_state["track_data"] is None:
        raise HTTPException(status_code=404, detail="Track não carregado")
    if app_state["telemetry_data"] is None:
        raise HTTPException(status_code=404, detail="Telemetria não carregada")
    if app_state["ai_raceline"] is None:
        raise HTTPException(status_code=404, detail="IA raceline não gerada")
    
    return {
        "track": app_state["track_data"],
        "player": app_state["telemetry_data"],
        "ai": app_state["ai_raceline"],
        "track_limits": app_state.get("track_limits") # NOVO
    }


# ============================================================================
# ENDPOINTS DE CAPTURA UDP EM TEMPO REAL
# ============================================================================

@app.post("/api/capture/start")
async def start_udp_capture(game: str = "F1-25"):
    """Inicia captura UDP de telemetria em tempo real"""
    try:
        if app_state["udp_capture"] and app_state["udp_capture"].running:
            raise HTTPException(status_code=400, detail="Captura já está rodando")
        
        logger.info(f"Iniciando captura UDP para {game}")
        
        capture = UDPTelemetryCapture(game=game)
        capture.start_capture()
        
        app_state["udp_capture"] = capture
        
        return {
            "status": "success",
            "message": f"Captura UDP iniciada para {game}",
            "data": capture.get_status()
        }
    
    except Exception as e:
        logger.error(f"Erro ao iniciar captura: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/capture/stop")
async def stop_udp_capture():
    """Para captura UDP e salva CSV"""
    try:
        if not app_state["udp_capture"] or not app_state["udp_capture"].running:
            raise HTTPException(status_code=400, detail="Nenhuma captura rodando")
        
        logger.info("Parando captura UDP...")
        
        csv_path = app_state["udp_capture"].stop_capture()
        
        return {
            "status": "success",
            "message": "Captura finalizada e CSV salvo",
            "data": {
                "csv_path": str(csv_path),
                "points_captured": len(app_state["udp_capture"].rows)
            }
        }
    
    except Exception as e:
        logger.error(f"Erro ao parar captura: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/capture/status")
async def get_capture_status():
    """Retorna status da captura UDP"""
    if not app_state["udp_capture"]:
        return {
            "running": False,
            "message": "Nenhuma captura iniciada"
        }
    
    return app_state["udp_capture"].get_status()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
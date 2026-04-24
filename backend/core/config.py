"""
Configurações do F1 Telemetry Analyzer
"""

# =============================================================================
# MODO DE DESENVOLVIMENTO / TESTE
# =============================================================================

# Carregamento automático de dados de exemplo ao iniciar o servidor
# True = Carrega automaticamente SaoPaulo.csv + example_telemetry.csv
# False = Requer upload manual via interface
AUTO_LOAD_EXAMPLE_DATA = True

# =============================================================================
# ARQUIVOS DE EXEMPLO
# =============================================================================

# Caminho relativo ao diretório raiz do projeto
EXAMPLE_TRACK_CSV = "data/SaoPaulo.csv"
EXAMPLE_TELEMETRY_CSV = "data/example_telemetry.csv"

# =============================================================================
# CAPTURA UDP
# =============================================================================

# Diretório onde salvar telemetrias capturadas via UDP
UDP_CAPTURE_DIR = "data/telemetry_sessions"

# =============================================================================
# API SETTINGS
# =============================================================================

# CORS - origens permitidas
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "*"  # Para desenvolvimento. Em produção, especificar domínios exatos
]

# Logging level
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# =============================================================================
# IA SETTINGS
# =============================================================================

# Parâmetros físicos da IA de raceline
GRIP_FACTOR = 1.8  # Grip factor (F1 típico: 1.5-2.0)
MAX_SPEED_KMH = 340  # Velocidade máxima em retas
MIN_SPEED_KMH = 60   # Velocidade mínima em curvas fechadas
MAX_ACCEL_G = 1.5    # Aceleração máxima (g)
MAX_BRAKE_G = 4.5    # Frenagem máxima (g)

# Posicionamento do apex (% da largura interna)
APEX_OFFSET_FACTOR = 0.3  # 30% da largura em direção à borda interna

# =============================================================================
# VALIDAÇÃO
# =============================================================================

# Número mínimo de pontos por volta
MIN_POINTS_PER_LAP = 10

# Tempo de volta válido (segundos)
MIN_LAP_TIME = 30   # Voltas mais rápidas que isso são ignoradas
MAX_LAP_TIME = 300  # Voltas mais lentas que isso são ignoradas

# =============================================================================
# PRODUÇÃO
# =============================================================================

# Para produção, alterar para:
# AUTO_LOAD_EXAMPLE_DATA = False
# CORS_ORIGINS = ["https://seu-dominio.com"]
# LOG_LEVEL = "WARNING"
import arcade
from data_engine import obter_dados_telemetria

# Configurações da Janela e Animação
LARGURA_TELA = 1200 # Aumentei um pouco para caber a legenda lateral
ALTURA_TELA = 900
TITULO = "Agente de IA - Traçado Ideal Animado (TCC)"

# Velocidade da Animação (Quantos pontos de telemetria pular por frame)
# 1 = Velocidade Real (se gravado a 60Hz), 5 = 5x mais rápido
VELOCIDADE_ANIMACAO = 3 

class F1Dashboard(arcade.Window):
    def __init__(self):
        super().__init__(LARGURA_TELA, ALTURA_TELA, TITULO)
        arcade.set_background_color(arcade.color.EERIE_BLACK)
        
        # Obter dados do Backend
        self.dados = obter_dados_telemetria()
        
        # Listas de armazenamento (Pixels da tela)
        self.pontos_borda_esq = []
        self.pontos_borda_dir = []
        
        # ESTRUTURA NOVA PARA O GRADIENTE:
        # Lista de dicionários: [{'p1': (x,y), 'p2': (x,y), 'cor': (r,g,b)}, ...]
        self.segmentos_coloridos = []
        self.telemetria_pontos = [] # Guardar velocidade para o carro
        
        # Variáveis de Controle da Animação
        self.indice_frame_atual = 0
        self.total_pontos = 0
        self.carro_ligado = True
        
        self.preparar_dados()

    def preparar_dados(self):
        if not self.dados: return

        # 1. Obter limites da pista para Escala e Centro
        xs_pista = self.dados["pista"]["centro_x"]
        ys_pista = self.dados["pista"]["centro_y"]
        escala = min(LARGURA_TELA / (max(xs_pista) - min(xs_pista)), 
                    ALTURA_TELA / (max(ys_pista) - min(ys_pista))) * 0.85
        centro_x_tela, centro_y_tela = (max(xs_pista) + min(xs_pista))/2, (max(ys_pista) + min(ys_pista))/2

        # =========================================================
        # AQUI ESTÁ A FUNÇÃO CORRIGIDA COM O ESPELHAMENTO (-1 *)
        # =========================================================
        def to_tex(x, y):
            tx = -1 * (x - centro_x_tela) * escala + (LARGURA_TELA / 2)
            ty = -1 * (y - centro_y_tela) * escala + (ALTURA_TELA / 2) # Y Invertido da pista
            return (tx, ty)
        # =========================================================

        # 2. Converter Bordas da Pista (Asfalto)
        for i in range(len(self.dados["pista"]["esquerda_x"])):
            self.pontos_borda_esq.append(to_tex(self.dados["pista"]["esquerda_x"][i], self.dados["pista"]["esquerda_y"][i]))
            self.pontos_borda_dir.append(to_tex(self.dados["pista"]["direita_x"][i], self.dados["pista"]["direita_y"][i]))

        # ---------------------------------------------------------
        # 3. LÓGICA DO ALINHAMENTO E GRADIENTE (A "Magia")
        # ---------------------------------------------------------
        xs_tel, zs_tel = self.dados["melhor"]["x"], self.dados["melhor"]["z"]
        freio, acel = self.dados["melhor"]["freio"], self.dados["melhor"]["acelerador"]
        
        # Centralização (Matemática do loader.py)
        media_x_pista, media_y_pista = sum(xs_pista)/len(xs_pista), sum(ys_pista)/len(ys_pista)
        media_x_tel, media_z_tel = sum(xs_tel)/len(xs_tel), sum(-z for z in zs_tel)/len(zs_tel)
        
        # Ajuste Total (Diferença centros + Offset manual do GPS)
        aj_x, aj_z = (media_x_pista - media_x_tel) - 13, (media_y_pista - media_z_tel) + 30

        self.total_pontos = len(xs_tel)
        ponto_anterior = None

        for i in range(self.total_pontos):
            # Converte o ponto atual para pixels
            x_real, y_real = xs_tel[i] + aj_x, -zs_tel[i] + aj_z
            ponto_atual = to_tex(x_real, y_real)
            
            # Guarda para a bolinha do carro
            self.telemetria_pontos.append({
                'pos': ponto_atual,
                'vel': self.dados["melhor"]["velocidade"][i]
            })

            # Se temos um ponto anterior, criamos um segmento colorido entre eles
            if ponto_anterior:
                # CÁLCULO DA COR DO GRADIENTE (RGB)
                # Padrão: Azul (Neutro), Freio: Vermelho, Acel: Verde
                
                pct_freio = freio[i] # Já vem em % do data_engine corrigido
                pct_acel = acel[i]
                
                # Interpolação simples de cor
                if pct_freio > 5: # Prioridade para o freio
                    red = int(100 + (pct_freio * 1.55)) # De 100 a 255
                    green, blue = 50, 50
                elif pct_acel > 10:
                    green = int(100 + (pct_acel * 1.55)) # De 100 a 255
                    red, blue = 50, 50
                else:
                    # Neutro (Azul Neon)
                    red, green, blue = 50, 200, 255
                
                cor_segmento = (red, green, blue)
                
                # Adiciona o segmento à lista de desenho
                self.segmentos_coloridos.append({
                    'p1': ponto_anterior,
                    'p2': ponto_atual,
                    'cor': cor_segmento
                })

            ponto_anterior = ponto_atual

    def on_update(self, delta_time):
        """Lógica da Animação: Executado 60 vezes por segundo"""
        if self.carro_ligado and self.dados:
            # Avança o índice da animação
            self.indice_frame_atual += VELOCIDADE_ANIMACAO
            
            # Se chegar no final da volta, reinicia (Loop)
            if self.indice_frame_atual >= self.total_pontos:
                self.indice_frame_atual = 0

    def on_draw(self):
        """Renderização Física: Desenha as imagens na tela"""
        self.clear()
        
        if not self.dados:
            arcade.draw_text("Nenhum dado encontrado", LARGURA_TELA/2, ALTURA_TELA/2, arcade.color.WHITE, 20, anchor_x="center")
            return

        # 1. DESENHAR AS BORDAS DA PISTA (Asfalto cinza)
        if self.pontos_borda_esq and self.pontos_borda_dir:
            arcade.draw_line_strip(self.pontos_borda_esq, arcade.color.GRAY, 2)
            arcade.draw_line_strip(self.pontos_borda_dir, arcade.color.GRAY, 2)

        # ---------------------------------------------------------
        # 2. DESENHAR O GRADIENTE (Até o ponto atual da animação)
        # ---------------------------------------------------------
        # Desenha apenas os segmentos que o carro já percorreu
        fim_desenho = min(self.indice_frame_atual, len(self.segmentos_coloridos))
        
        for i in range(fim_desenho):
            seg = self.segmentos_coloridos[i]
            # Desenha uma linha individual com a sua cor específica
            arcade.draw_line(seg['p1'][0], seg['p1'][1], seg['p2'][0], seg['p2'][1], seg['cor'], 4)

        # ---------------------------------------------------------
        # 3. DESENHAR "O CARRO" (A Bolinha)
        # ---------------------------------------------------------
        if self.telemetria_pontos and self.indice_frame_atual < self.total_pontos:
            dados_carro = self.telemetria_pontos[self.indice_frame_atual]
            pos = dados_carro['pos']
            vel = dados_carro['vel']
            
            # Sombra/Brilho do carro
            arcade.draw_circle_filled(pos[0], pos[1], 10, (255, 255, 255, 100))
            # O carro (Bolinha Branca)
            arcade.draw_circle_filled(pos[0], pos[1], 6, arcade.color.WHITE)
            
            # Texto da Velocidade flutuando sobre o carro
            arcade.draw_text(f"{int(vel)} km/h", pos[0] + 15, pos[1] + 15, arcade.color.WHITE, 12, bold=True)

        # 4. Textos e Legenda Fixa
        self.desenhar_ui_e_legenda()

    def desenhar_ui_e_legenda(self):
        """Desenha as informações de texto e a legenda de cores"""
        arcade.draw_text("SISTEMA DE ANÁLISE DE TRAÇADO", 20, ALTURA_TELA - 40, arcade.color.WHITE, 16, bold=True)
        arcade.draw_text(f"Volta Exibida: {self.dados['resumo']['melhor_volta']}", 20, ALTURA_TELA - 70, arcade.color.CYAN, 12)
        arcade.draw_text(f"Tempo: {self.dados['resumo']['tempo_formatado']}", 20, ALTURA_TELA - 90, arcade.color.WHITE, 12)

        # Caixa da Legenda (Canto inferior direito)
        x_leg, y_leg = LARGURA_TELA - 200, 150
        arcade.draw_lbwh_rectangle_filled(x_leg - 10, y_leg - 100, 190, 110, (50, 50, 50, 200))
        arcade.draw_text("LEGENDA TELEMETRIA", x_leg, y_leg - 20, arcade.color.WHITE, 11, bold=True)
        
        # Linhas de exemplo da legenda
        arcade.draw_line(x_leg, y_leg - 45, x_leg + 40, y_leg - 45, (255, 50, 50), 4) # Freio
        arcade.draw_text("Frenagem Agressiva", x_leg + 50, y_leg - 50, arcade.color.WHITE, 10)
        
        arcade.draw_line(x_leg, y_leg - 65, x_leg + 40, y_leg - 65, (50, 255, 50), 4) # Acel
        arcade.draw_text("Aceleração Total", x_leg + 50, y_leg - 70, arcade.color.WHITE, 10)
        
        arcade.draw_line(x_leg, y_leg - 85, x_leg + 40, y_leg - 85, (50, 200, 255), 4) # Neutro
        arcade.draw_text("Neutro / Cooldown", x_leg + 50, y_leg - 90, arcade.color.WHITE, 10)

    def on_key_press(self, key, modifiers):
        """Controles de teclado (Pausar animação)"""
        if key == arcade.key.SPACE:
            self.carro_ligado = not self.carro_ligado

if __name__ == "__main__":
    app = F1Dashboard()
    arcade.run()
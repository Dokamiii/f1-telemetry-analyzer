import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def desenhar_pista(pista_interlagos):
    # 1. Carregar os dados
    pista_interlagos = pd.read_csv(r'/raw/SaoPaulo.csv')
    pista_interlagos.columns = pista_interlagos.columns.str.strip()  # Limpar possíveis espaços nos nomes das colunas

    # Extraindo os dados
    x = pista_interlagos['# x_m'].values
    y = pista_interlagos['y_m'].values
    w_right = pista_interlagos['w_tr_right_m'].values
    w_left = pista_interlagos['w_tr_left_m'].values

    # 2. Calcular a geometria para desenhar as bordas da pista
    # Primeiro, pegamos a direção da linha central (dx, dy)
    dx = np.gradient(x)
    dy = np.gradient(y)

    # Em seguida, calculamos o vetor perpendicular (normal) apontando para os lados
    norm = np.hypot(dx, dy)
    norm[norm == 0] = 1  # Evitar divisão por zero

    nx = -dy / norm  # Componente X do vetor perpendicular (aponta para a esquerda)
    ny = dx / norm   # Componente Y do vetor perpendicular

    # 3. Calcular as coordenadas exatas dos limites da pista (Bordas)
    # Borda Esquerda = Linha Central + (Vetor Perpendicular * Largura Esquerda)
    x_left = x + nx * w_left
    y_left = y + ny * w_left

    # Borda Direita = Linha Central - (Vetor Perpendicular * Largura Direita)
    x_right = x - nx * w_right
    y_right = y - ny * w_right
    
    plt.figure(figsize=(20, 10))

    # Preenche o espaço entre a borda direita e esquerda simulando o asfalto
    plt.fill(np.concatenate([x_left, x_right[::-1]]), 
            np.concatenate([y_left, y_right[::-1]]), 
            color='gray', alpha=0.4, label='Asfalto (Proporção da Pista)')
    # Desenha as linhas principais
    plt.plot(x, y, linestyle='--', color='yellow', linewidth=1, label='Linha de Referência (Centro)')
    plt.plot(x_left, y_left, color='black', linewidth=1.5, label='Limite Esquerdo')
    plt.plot(x_right, y_right, color='black', linewidth=1.5, label='Limite Direito')
    # Configurações do gráfico
    plt.title('Circuito de Interlagos - Limites e Proporção Real')
    plt.xlabel('Eixo X (m)')
    plt.ylabel('Eixo Y (m)')
    plt.axis('equal')  # Mantém a proporção real em x e y
    plt.legend()


desenhar_pista(r'/raw/SaoPaulo.csv')
# 4. Plotando o resultado!
# Exibe a pista
plt.show()
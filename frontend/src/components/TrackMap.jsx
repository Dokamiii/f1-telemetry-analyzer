import React, { useEffect, useRef, useState } from 'react'
import Plot from 'react-plotly.js'
import './TrackMap.css'

function TrackMap({ trackData, playerData, aiData }) {
  const [selectedPoint, setSelectedPoint] = useState(0)
  const [animating, setAnimating] = useState(false)
  const animationRef = useRef(null)

  const playerX = playerData?.best_lap_data?.x || []
  const playerZ = playerData?.best_lap_data?.z || []
  const playerSpeed = playerData?.best_lap_data?.speed || []
  
  const aiX = aiData?.trajectory?.x || []
  const aiZ = aiData?.trajectory?.z || []
  const aiSpeed = aiData?.speed || []

  // Calcular bounds do mapa
  const allX = [
    ...trackData.centerline.x,
    ...trackData.left_edge.x,
    ...trackData.right_edge.x
  ]
  const allZ = [
    ...trackData.centerline.y,
    ...trackData.left_edge.y,
    ...trackData.right_edge.y
  ]

  const minX = Math.min(...allX)
  const maxX = Math.max(...allX)
  const minZ = Math.min(...allZ)
  const maxZ = Math.max(...allZ)

  const margin = 50
  const xRange = [minX - margin, maxX + margin]
  const zRange = [minZ - margin, maxZ + margin]

  // Criar polígono do asfalto
  const asphaltX = [
    ...trackData.left_edge.x,
    ...trackData.right_edge.x.slice().reverse(),
    trackData.left_edge.x[0]
  ]
  
  const asphaltZ = [
    ...trackData.left_edge.y,
    ...trackData.right_edge.y.slice().reverse(),
    trackData.left_edge.y[0]
  ]

  // Colorir raceline do player por velocidade
  const getSpeedColor = (speed) => {
    if (speed < 100) return 'rgb(41, 121, 255)' // Azul
    if (speed < 180) return 'rgb(0, 230, 118)' // Verde
    if (speed < 250) return 'rgb(255, 208, 0)' // Amarelo
    if (speed < 300) return 'rgb(255, 121, 0)' // Laranja
    return 'rgb(232, 25, 44)' // Vermelho
  }

  const currentAiIndex = Math.min(selectedPoint, Math.max(0, aiX.length - 1));

  // Dados do gráfico
  const traces = [
    // Asfalto
    {
      x: asphaltX,
      y: asphaltZ,
      fill: 'toself',
      fillcolor: 'rgba(100, 100, 100, 0.3)',
      line: { color: 'rgba(255, 255, 255, 0)', width: 0 },
      mode: 'lines',
      name: 'Pista',
      hoverinfo: 'skip',
      showlegend: false
    },
    // Centerline
    {
      x: trackData.centerline.x,
      y: trackData.centerline.y,
      mode: 'lines',
      line: { color: 'rgba(255, 208, 0, 0.4)', width: 1, dash: 'dot' },
      name: 'Centro',
      hoverinfo: 'skip',
      showlegend: false
    },
    // Bordas
    {
      x: trackData.left_edge.x,
      y: trackData.left_edge.y,
      mode: 'lines',
      line: { color: 'rgba(255, 255, 255, 0.6)', width: 2 },
      name: 'Limite Esq.',
      hoverinfo: 'skip',
      showlegend: false
    },
    {
      x: trackData.right_edge.x,
      y: trackData.right_edge.y,
      mode: 'lines',
      line: { color: 'rgba(255, 255, 255, 0.6)', width: 2 },
      name: 'Limite Dir.',
      hoverinfo: 'skip',
      showlegend: false
    },
    // Raceline do Jogador
    {
      x: playerX,
      y: playerZ,
      mode: 'lines',
      line: { 
        color: 'rgba(255, 208, 0, 0.8)',
        width: 3
      },
      name: 'Player',
      hovertemplate: 'Velocidade: %{text} km/h<extra></extra>',
      // CORREÇÃO AQUI: fallback para 0 se s for undefined
      text: playerSpeed.map(s => (s || 0).toFixed(0)), 
      showlegend: true
    },
    // Raceline da IA (linha ~125)
    {
      x: aiX,
      y: aiZ,
      mode: 'lines',
      line: { 
        color: 'rgba(157, 78, 221, 0.9)',
        width: 3
      },
      name: 'IA Ideal',
      hovertemplate: 'Velocidade: %{text} km/h<extra></extra>',
      // CORREÇÃO AQUI: fallback para 0 se s for undefined
      text: aiSpeed.map(s => (s || 0).toFixed(0)),
      showlegend: true
    },
    // Ponto atual do player
    selectedPoint < playerX.length ? {
      x: [playerX[selectedPoint]],
      y: [playerZ[selectedPoint]],
      mode: 'markers',
      marker: { 
        size: 12, 
        color: 'rgb(255, 208, 0)',
        symbol: 'circle',
        line: { color: 'white', width: 2 }
      },
      name: 'Posição Player',
      hoverinfo: 'skip',
      showlegend: false
    } : {},
    // Ponto atual da IA
    {
      x: [aiX[currentAiIndex]], // <-- Usa o índice seguro para não desaparecer!
      y: [aiZ[currentAiIndex]], // <-- Usa o índice seguro para não desaparecer!
      mode: 'markers',
      marker: {
        color: '#9d4edd',
        size: 10,
        line: { color: '#ffffff', width: 2 }
      },
      name: 'IA Ideal',
      showlegend: false, // <-- ISSO REMOVE A LEGENDA DUPLICADA
      hoverinfo: 'skip'
    }
  ]

  // Layout do gráfico
  const layout = {
    width: undefined,
    height: undefined,
    autosize: true,
    paper_bgcolor: '#0b0c1a',
    plot_bgcolor: '#0b0c1a',
    xaxis: {
      range: xRange,
      showgrid: false,
      zeroline: false,
      showticklabels: false,
      scaleanchor: 'y',
      scaleratio: 1
    },
    yaxis: {
      range: zRange,
      showgrid: false,
      zeroline: false,
      showticklabels: false
    },
    margin: { l: 10, r: 10, t: 10, b: 10 },
    showlegend: true,
    legend: {
      x: 0.02,
      y: 0.98,
      bgcolor: 'rgba(11, 12, 26, 0.8)',
      bordercolor: 'rgba(255, 255, 255, 0.2)',
      borderwidth: 1,
      font: { color: '#eceef8', size: 11 }
    },
    hovermode: 'closest'
  }

  const config = {
    responsive: true,
    displayModeBar: false
  }

  // Animação
  const toggleAnimation = () => {
    if (animating) {
      setAnimating(false)
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    } else {
      setAnimating(true)
      animate()
    }
  }

  const animate = () => {
    setSelectedPoint(prev => {
      if (prev >= playerX.length - 1) {
        setAnimating(false)
        return 0
      }
      return prev + 1
    })
    animationRef.current = requestAnimationFrame(animate)
  }

  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [])

  return (
    <div className="track-map">
      <div className="map-header">
        <div className="map-title">
          <h2>{trackData.name}</h2>
          <span className="map-subtitle">{trackData.total_points} pontos de referência</span>
        </div>
        
        <div className="map-controls">
          <button 
            className={`btn-animate ${animating ? 'active' : ''}`}
            onClick={toggleAnimation}
          >
            {animating ? '⏸ Pausar' : '▶ Animar'}
          </button>
          
          <button 
            className="btn-reset-view"
            onClick={() => setSelectedPoint(0)}
          >
            ↺ Reset
          </button>
        </div>
      </div>

      <div className="map-container">
        <Plot
          data={traces}
          layout={layout}
          config={config}
          style={{ width: '100%', height: '100%' }}
          useResizeHandler={true}
        />
      </div>

      <div className="map-info">
        <div className="info-item">
          <span className="info-label">Progresso:</span>
          <span className="info-value">
            {playerX && playerX.length > 0 
              ? Number((selectedPoint / playerX.length) * 100).toFixed(1) 
              : "0.0"}%
          </span>
        </div>
        
        <div className="info-item">
          <span className="info-label">Velocidade Player:</span>
          <span className="info-value player-color">
            {Number(playerSpeed[selectedPoint] ?? playerSpeed[playerSpeed.length - 1] ?? 0).toFixed(0)} km/h
          </span>
        </div>
        
        <div className="info-item">
          <span className="info-label">Velocidade IA:</span>
          <span className="info-value ai-color">
            {Number(aiSpeed[selectedPoint] ?? aiSpeed[aiSpeed.length - 1] ?? 0).toFixed(0)} km/h
          </span>
        </div>
      </div>
    </div>
  )
}

export default TrackMap

import React, { useState } from 'react'
import Plot from 'react-plotly.js'
import './TelemetryCharts.css'

function TelemetryCharts({ playerData, aiData }) {
  const [activeChart, setActiveChart] = useState('speed')

  const playerDistance = playerData.best_lap_data.distance
  const playerSpeed = playerData.best_lap_data.speed
  const playerThrottle = playerData.best_lap_data.throttle
  const playerBrake = playerData.best_lap_data.brake

  const aiDistance = aiData.trajectory.distance
  const aiSpeed = aiData.speed
  const aiThrottle = aiData.throttle
  const aiBrake = aiData.brake

  // Configurações comuns dos gráficos
  const commonLayout = {
    autosize: true,
    paper_bgcolor: '#0b0c1a',
    plot_bgcolor: '#101225',
    margin: { l: 50, r: 20, t: 20, b: 40 },
    font: { color: '#eceef8', family: 'Inter, sans-serif', size: 11 },
    xaxis: {
      title: 'Distância (m)',
      gridcolor: 'rgba(255, 255, 255, 0.05)',
      color: '#7a7d9a'
    },
    yaxis: {
      gridcolor: 'rgba(255, 255, 255, 0.05)',
      color: '#7a7d9a'
    },
    hovermode: 'x unified',
    showlegend: true,
    legend: {
      x: 0.02,
      y: 0.98,
      bgcolor: 'rgba(11, 12, 26, 0.8)',
      bordercolor: 'rgba(255, 255, 255, 0.2)',
      borderwidth: 1
    }
  }

  const config = {
    responsive: true,
    displayModeBar: false
  }

  // Gráfico de Velocidade
  const speedChart = {
    data: [
      {
        x: playerDistance,
        y: playerSpeed,
        name: 'Player',
        type: 'scatter',
        mode: 'lines',
        line: { color: '#ffd000', width: 2 },
        hovertemplate: '%{y:.0f} km/h<extra></extra>'
      },
      {
        x: aiDistance,
        y: aiSpeed,
        name: 'IA Ideal',
        type: 'scatter',
        mode: 'lines',
        line: { color: '#9d4edd', width: 2 },
        hovertemplate: '%{y:.0f} km/h<extra></extra>'
      }
    ],
    layout: {
      ...commonLayout,
      yaxis: {
        ...commonLayout.yaxis,
        title: 'Velocidade (km/h)'
      }
    }
  }

  // Gráfico de Throttle
  const throttleChart = {
    data: [
      {
        x: playerDistance,
        y: playerThrottle,
        name: 'Player',
        type: 'scatter',
        mode: 'lines',
        fill: 'tozeroy',
        fillcolor: 'rgba(0, 230, 118, 0.2)',
        line: { color: '#00e676', width: 2 },
        hovertemplate: '%{y:.1f}%<extra></extra>'
      },
      {
        x: aiDistance,
        y: aiThrottle,
        name: 'IA Ideal',
        type: 'scatter',
        mode: 'lines',
        line: { color: '#9d4edd', width: 2, dash: 'dot' },
        hovertemplate: '%{y:.1f}%<extra></extra>'
      }
    ],
    layout: {
      ...commonLayout,
      yaxis: {
        ...commonLayout.yaxis,
        title: 'Acelerador (%)',
        range: [0, 105]
      }
    }
  }

  // Gráfico de Freio
  const brakeChart = {
    data: [
      {
        x: playerDistance,
        y: playerBrake,
        name: 'Player',
        type: 'scatter',
        mode: 'lines',
        fill: 'tozeroy',
        fillcolor: 'rgba(232, 25, 44, 0.2)',
        line: { color: '#e8192c', width: 2 },
        hovertemplate: '%{y:.1f}%<extra></extra>'
      },
      {
        x: aiDistance,
        y: aiBrake,
        name: 'IA Ideal',
        type: 'scatter',
        mode: 'lines',
        line: { color: '#9d4edd', width: 2, dash: 'dot' },
        hovertemplate: '%{y:.1f}%<extra></extra>'
      }
    ],
    layout: {
      ...commonLayout,
      yaxis: {
        ...commonLayout.yaxis,
        title: 'Freio (%)',
        range: [0, 105]
      }
    }
  }

  // Gráfico de Delta (diferença de tempo acumulada)
  const calculateDelta = () => {
    // Simplificado: calcular delta baseado em velocidade média
    const delta = []
    const minLength = Math.min(playerDistance.length, aiDistance.length)
    
    let cumulativeDelta = 0
    
    for (let i = 0; i < minLength; i++) {
      if (i > 0) {
        const distSegment = playerDistance[i] - playerDistance[i - 1]
        
        // Tempo do player neste segmento
        const playerSpeedMs = playerSpeed[i] / 3.6
        const playerTime = playerSpeedMs > 0 ? distSegment / playerSpeedMs : 0
        
        // Tempo da IA neste segmento
        const aiSpeedMs = aiSpeed[i] / 3.6
        const aiTime = aiSpeedMs > 0 ? distSegment / aiSpeedMs : 0
        
        // Delta acumulado (positivo = player mais lento)
        cumulativeDelta += (playerTime - aiTime)
      }
      
      delta.push(cumulativeDelta)
    }
    
    return delta
  }

  const deltaData = calculateDelta()

  const deltaChart = {
    data: [
      {
        x: playerDistance.slice(0, deltaData.length),
        y: deltaData,
        name: 'Delta Tempo',
        type: 'scatter',
        mode: 'lines',
        fill: 'tozeroy',
        fillcolor: deltaData[deltaData.length - 1] > 0 ? 'rgba(232, 25, 44, 0.15)' : 'rgba(0, 230, 118, 0.15)',
        line: { 
          color: deltaData[deltaData.length - 1] > 0 ? '#e8192c' : '#00e676', 
          width: 2 
        },
        hovertemplate: '%{y:.3f}s<extra></extra>'
      }
    ],
    layout: {
      ...commonLayout,
      yaxis: {
        ...commonLayout.yaxis,
        title: 'Delta (s)',
        zeroline: true,
        zerolinecolor: 'rgba(255, 255, 255, 0.3)',
        zerolinewidth: 1
      }
    }
  }

  const charts = {
    speed: speedChart,
    throttle: throttleChart,
    brake: brakeChart,
    delta: deltaChart
  }

  const currentChart = charts[activeChart]

  return (
    <div className="telemetry-charts">
      <div className="charts-header">
        <h3>Análise Detalhada</h3>
        
        <div className="chart-tabs">
          <button
            className={`chart-tab ${activeChart === 'speed' ? 'active' : ''}`}
            onClick={() => setActiveChart('speed')}
          >
            Velocidade
          </button>
          <button
            className={`chart-tab ${activeChart === 'throttle' ? 'active' : ''}`}
            onClick={() => setActiveChart('throttle')}
          >
            Throttle
          </button>
          <button
            className={`chart-tab ${activeChart === 'brake' ? 'active' : ''}`}
            onClick={() => setActiveChart('brake')}
          >
            Freio
          </button>
          <button
            className={`chart-tab ${activeChart === 'delta' ? 'active' : ''}`}
            onClick={() => setActiveChart('delta')}
          >
            Delta
          </button>
        </div>
      </div>

      <div className="chart-container">
        <Plot
          data={currentChart.data}
          layout={currentChart.layout}
          config={config}
          style={{ width: '100%', height: '100%' }}
          useResizeHandler={true}
        />
      </div>
    </div>
  )
}

export default TelemetryCharts

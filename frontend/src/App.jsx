import React, { useState, useEffect } from 'react'
import TrackMap from './components/TrackMap'
import TelemetryCharts from './components/TelemetryCharts'
import UploadPanel from './components/UploadPanel'
import ComparisonPanel from './components/ComparisonPanel'
import { api } from './api/client'
import './App.css'

function App() {
  const [trackData, setTrackData] = useState(null)
  const [telemetryData, setTelemetryData] = useState(null)
  const [aiData, setAiData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [step, setStep] = useState(1) // 1: upload track, 2: upload telemetry, 3: results

  // Carregar dados automaticamente ao iniciar
  useEffect(() => {
    loadExampleData()
  }, [])

  const loadExampleData = async () => {
    setLoading(true)
    setError(null)
    
    try {
      console.log('Verificando se dados de exemplo já estão carregados...')
      
      // Tentar carregar dados que já podem estar no backend
      const [track, telemetry, ai] = await Promise.all([
        api.getTrackData().catch(() => null),
        api.getTelemetryData().catch(() => null),
        api.getAiRaceline().catch(() => null)
      ])
      
      if (track && telemetry && ai) {
        console.log('✅ Dados de exemplo carregados automaticamente!')
        setTrackData(track)
        setTelemetryData(telemetry)
        setAiData(ai)
        setStep(3) // Ir direto para visualização
      } else {
        console.log('⚠️ Dados de exemplo não encontrados. Aguardando upload.')
        setStep(1) // Mostrar tela de upload
      }
    } catch (err) {
      console.error('Erro ao carregar dados de exemplo:', err)
      setStep(1) // Em caso de erro, mostrar tela de upload
    } finally {
      setLoading(false)
    }
  }

  const handleTrackUpload = async (file) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await api.uploadTrack(file)
      setTrackData(await api.getTrackData())
      setStep(2)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao carregar pista')
    } finally {
      setLoading(false)
    }
  }

  const handleTelemetryUpload = async (file) => {
    setLoading(true)
    setError(null)
    
    try {
      await api.uploadTelemetry(file)
      const [telemetry, ai] = await Promise.all([
        api.getTelemetryData(),
        api.getAiRaceline()
      ])
      
      setTelemetryData(telemetry)
      setAiData(ai)
      setStep(3)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao processar telemetria')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setTrackData(null)
    setTelemetryData(null)
    setAiData(null)
    setStep(1)
    setError(null)
  }

  // Loading inicial
  if (loading && step === 1) {
    return (
      <div className="app">
        <div className="loading-screen">
          <div className="loading-spinner"></div>
          <p>Carregando dados de exemplo...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="logo">
          <span className="logo-text">RACELINE</span>
          <span className="logo-ai">AI</span>
        </div>
        
        <div className="header-center">
          {trackData && (
            <div className="track-badge">
              <span className="track-name">{trackData.name}</span>
              <span className="track-length">{(trackData.length_meters / 1000).toFixed(2)} km</span>
            </div>
          )}
        </div>
        
        <div className="header-buttons">
          {step === 3 && (
            <button onClick={loadExampleData} className="btn-reload" title="Recarregar dados de exemplo">
              ↻ Recarregar
            </button>
          )}
          <button onClick={handleReset} className="btn-reset">
            Reset
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {error && (
          <div className="error-banner">
            ⚠️ {error}
          </div>
        )}

        {step === 1 && (
          <UploadPanel
            title="1. Carregar Pista"
            description="Upload do CSV da pista (track data)"
            acceptedFormat=".csv"
            onUpload={handleTrackUpload}
            loading={loading}
            example="# x_m, y_m, w_tr_right_m, w_tr_left_m"
          />
        )}

        {step === 2 && (
          <UploadPanel
            title="2. Carregar Telemetria"
            description="Upload do CSV de telemetria do jogador"
            acceptedFormat=".csv"
            onUpload={handleTelemetryUpload}
            loading={loading}
            example="session_time, lap, pos_x, pos_z, speed, throttle, brake"
          />
        )}

        {step === 3 && trackData && telemetryData && aiData && (
          <div className="results-layout">
            <div className="map-section">
              <TrackMap 
                trackData={trackData}
                playerData={telemetryData}
                aiData={aiData}
              />
            </div>
            
            <div className="sidebar-section">
              <ComparisonPanel
                telemetryData={telemetryData}
                aiData={aiData}
              />
              
              <TelemetryCharts
                playerData={telemetryData}
                aiData={aiData}
              />
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="footer">
        <span>F1 Telemetry Analyzer v1.0</span>
        <span>•</span>
        <span>IA de Raceline baseada em princípios reais de corrida</span>
      </footer>
    </div>
  )
}

export default App
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
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [step, setStep] = useState(1) // 1: upload track, 2: upload telemetry, 3: results

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
        
        <button onClick={handleReset} className="btn-reset">
          Reset
        </button>
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
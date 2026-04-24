import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const client = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const api = {
  // Upload de pista
  uploadTrack: async (file) => {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await client.post('/api/upload/track', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    
    return response.data
  },

  // Upload de telemetria
  uploadTelemetry: async (file) => {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await client.post('/api/upload/telemetry', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    
    return response.data
  },

  // Obter dados da pista
  getTrackData: async () => {
    const response = await client.get('/api/data/track')
    return response.data
  },

  // Obter dados de telemetria
  getTelemetryData: async () => {
    const response = await client.get('/api/data/telemetry')
    return response.data
  },

  // Obter raceline da IA
  getAiRaceline: async () => {
    const response = await client.get('/api/data/ai-raceline')
    return response.data
  },

  // Obter comparação completa
  getComparison: async () => {
    const response = await client.get('/api/data/comparison')
    return response.data
  },
}

export default client

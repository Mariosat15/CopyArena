import axios from 'axios'

// Configure API base URL based on environment
const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
const isNetworkAccess = window.location.hostname.startsWith('192.168.') || window.location.hostname.startsWith('10.') || window.location.hostname.startsWith('172.')
const isProduction = !isLocalhost && !isNetworkAccess

const API_BASE_URL = isProduction 
  ? `${window.location.protocol}//${window.location.host}`
  : `http://${window.location.hostname}:8002`

// Create axios instance with base configuration
export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request interceptor for auth token and debugging
api.interceptors.request.use(
  (config) => {
    // Add session ID if available
    const sessionId = localStorage.getItem('copyarena_session_id')
    if (sessionId) {
      config.headers['X-Session-ID'] = sessionId
    }
    
    // Add auth token if available
    const authStore = JSON.parse(localStorage.getItem('auth-storage') || '{}')
    const token = authStore.state?.token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    if (!isProduction) {
      console.log(`API Request: ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`)
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Add response interceptor for error handling and auth
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear auth state on 401 errors
      localStorage.removeItem('auth-storage')
      window.location.href = '/login'
    }
    
    if (!isProduction) {
      console.error('API Error:', error.response?.data || error.message)
    }
    return Promise.reject(error)
  }
)

export default api 
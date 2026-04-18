import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor: attach JWT
api.interceptors.request.use((config) => {
  const stored = localStorage.getItem('auth')
  if (stored) {
    try {
      const { state } = JSON.parse(stored)
      if (state?.user?.access_token) {
        config.headers.Authorization = `Bearer ${state.user.access_token}`
      }
    } catch {
      // malformed storage — ignore
    }
  }
  return config
})

// Response interceptor: auto-logout on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('auth')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)

export default api

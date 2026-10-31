import axios from 'axios'

export const api = axios.create({ baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1' })
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = sessionStorage.getItem('recurflow_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export function collection<T = any>(data: any): T[] {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.items)) return data.items
  if (Array.isArray(data?.results)) return data.results
  if (Array.isArray(data?.data)) return data.data
  return []
}

export const resource = (path: string) => ({
  list: (params?: Record<string, unknown>) => api.get(path, { params }).then(r => r.data),
  get: (id: number | string) => api.get(`${path}/${id}`).then(r => r.data),
  create: (data: unknown) => api.post(path, data).then(r => r.data),
  update: (id: number | string, data: unknown) => api.patch(`${path}/${id}`, data).then(r => r.data),
})

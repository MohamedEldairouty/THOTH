import axios from 'axios'
import type {
  ExhibitLocalized,
  CategoryLocalized,
  HallLocalized,
  ChatRequest,
  ChatResponse,
  RobotStatus,
  NavigationRequest,
  MapOverview,
  MapExhibitMarker,
  Language,
} from '../types'

const api = axios.create({ baseURL: '/api' })

// Exhibits
export const getExhibits = (
  lang: Language,
  params?: { category_id?: number; hall_id?: number; era?: string; search?: string }
) => api.get<ExhibitLocalized[]>('/exhibits', { params: { lang, ...params } }).then(r => r.data)

export const getExhibit = (id: number, lang: Language) =>
  api.get<ExhibitLocalized>(`/exhibits/${id}`, { params: { lang } }).then(r => r.data)

// Categories & Halls
export const getCategories = (lang: Language) =>
  api.get<CategoryLocalized[]>('/categories', { params: { lang } }).then(r => r.data)

export const getHalls = (lang: Language) =>
  api.get<HallLocalized[]>('/halls', { params: { lang } }).then(r => r.data)

// Chat
export const sendChatMessage = (payload: ChatRequest) =>
  api.post<ChatResponse>('/chat', payload).then(r => r.data)

// Map
export const getMapOverview = () => api.get<MapOverview>('/map').then(r => r.data)

export const getMapExhibits = (lang: Language) =>
  api.get<MapExhibitMarker[]>('/map/exhibits', { params: { lang } }).then(r => r.data)

export const getRoute = (to_exhibit: number, from_exhibit?: number) =>
  api.get('/map/route', { params: { to_exhibit, from_exhibit } }).then(r => r.data)

// Robot / Navigation
export const getRobotStatus = () => api.get<RobotStatus>('/robot/status').then(r => r.data)

export const startNavigation = (exhibit_id: number) =>
  api.post<NavigationRequest>('/navigation/start', { exhibit_id }).then(r => r.data)

export const stopNavigation = () => api.post('/navigation/stop').then(r => r.data)

export const getNavigationStatus = () =>
  api.get<NavigationRequest | null>('/navigation/status').then(r => r.data)

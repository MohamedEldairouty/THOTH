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

const api = axios.create({
  baseURL: '/api',
  // Bypass ngrok free-tier interstitial that otherwise replies with HTML
  // and breaks JSON parsing on /api/* calls when tunneling over ngrok.
  headers: { 'ngrok-skip-browser-warning': 'true' },
})

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

export const sendVoiceMessage = (
  audioBlob: Blob,
  session_id?: number,
  exhibit_id?: number,
) => {
  const form = new FormData()
  form.append('audio', audioBlob, 'recording.webm')
  if (session_id != null) form.append('session_id', String(session_id))
  if (exhibit_id != null) form.append('exhibit_id', String(exhibit_id))
  return api.post<ChatResponse>('/chat/voice', form).then(r => r.data)
}

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

// ── Tours ──────────────────────────────────────────────────────────────

export interface TourSummary {
  id: number
  name: string
  description: string | null
  estimated_minutes: number | null
  is_preset: boolean
  stop_count: number
  language: string
}

export interface TourStop {
  sequence_order: number
  exhibit_id: number
  exhibit_title: string
  exhibit_image: string | null
  x_position: number | null
  y_position: number | null
}

export interface TourDetail extends TourSummary {
  stops: TourStop[]
}

export interface TourRun {
  id: number
  tour_id: number
  tour_name: string
  current_stop_index: number
  total_stops: number
  status: 'pending' | 'moving' | 'arrived' | 'completed' | 'cancelled'
  language: string

  current_exhibit_id: number | null
  current_exhibit_title: string | null
  current_exhibit_image: string | null
  target_x: number | null
  target_y: number | null

  next_exhibit_id: number | null
  next_exhibit_title: string | null

  started_at: string
  ended_at: string | null
}

export const listTours = (lang: Language) =>
  api.get<TourSummary[]>('/tours/presets', { params: { lang } }).then(r => r.data)

export const getTour = (tour_id: number, lang: Language) =>
  api.get<TourDetail>(`/tours/${tour_id}`, { params: { lang } }).then(r => r.data)

export const startTour = (payload: {
  tour_id?: number
  exhibit_ids?: number[]
  language: Language
}) => api.post<TourRun>('/tours/start', payload).then(r => r.data)

export const getCurrentTourRun = () =>
  api.get<TourRun | null>('/tours/runs/current').then(r => r.data)

export const advanceTour = (run_id: number) =>
  api.post<TourRun>(`/tours/runs/${run_id}/next`).then(r => r.data)

export const cancelTour = (run_id: number) =>
  api.post(`/tours/runs/${run_id}/cancel`).then(r => r.data)

export interface Narration {
  exhibit_id: number
  exhibit_title: string
  narration: string
  has_more_stops: boolean
  language: string
  audio_base64: string | null
}

export const getNarration = (run_id: number, with_audio = true) =>
  api.get<Narration | null>(`/tours/runs/${run_id}/narration`, {
    params: { with_audio },
  }).then(r => r.data)

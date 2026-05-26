export type Language = 'en' | 'ar' | 'fr'

export interface ExhibitLocalized {
  id: number
  title: string
  short_description: string | null
  full_description: string | null
  era: string | null
  category_id: number | null
  hall_id: number | null
  image_url: string | null
  video_url: string | null
  audio_url: string | null
  x_position: number | null
  y_position: number | null
  language: string
  created_at: string
  updated_at: string
}

export interface CategoryLocalized {
  id: number
  name: string
  language: string
}

export interface HallLocalized {
  id: number
  name: string
  floor_number: number
  description: string | null
  map_image_url: string | null
  language: string
}

export interface ChatRequest {
  message: string
  session_id?: number
  language: Language
  exhibit_id?: number
}

export interface ChatResponse {
  reply: string
  session_id: number
  language: string
}

export interface RobotStatus {
  /** Live snapshot from the ROS bridge — not persisted. */
  status: string
  current_x: number
  current_y: number
}

export interface NavigationRequest {
  id: number
  target_exhibit_id: number
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled'
  estimated_time: number | null
  created_at: string
}

export interface MapConfig {
  resolution: number   // meters per pixel
  origin_x: number     // world x of map's bottom-left pixel
  origin_y: number     // world y of map's bottom-left pixel
  width_px: number
  height_px: number
  width_m: number
  height_m: number
}

export interface MapOverview {
  map_image_url: string
  map_config: MapConfig
  robot: {
    x: number     // world meters
    y: number     // world meters
    status: string
  }
}

export interface MapExhibitMarker {
  id: number
  title: string
  x: number
  y: number
  hall_id: number | null
}

// ── Tour types ─────────────────────────────────────────────────────────
export interface TourStop {
  sequence_order: number
  exhibit_id: number
  exhibit_title: string
  exhibit_image: string | null
  x_position: number | null
  y_position: number | null
}

export interface TourSummary {
  id: number
  name: string
  description: string | null
  estimated_minutes: number | null
  is_preset: boolean
  stop_count: number
  language: string
}

export interface TourDetail extends TourSummary {
  stops: TourStop[]
}

export type TourRunStatus = 'pending' | 'moving' | 'arrived' | 'completed' | 'cancelled'

export interface TourRun {
  id: number
  tour_id: number
  tour_name: string
  current_stop_index: number
  total_stops: number
  status: TourRunStatus
  language: string

  current_exhibit_id: number | null
  current_exhibit_title: string | null
  current_exhibit_image: string | null
  target_x: number | null
  target_y: number | null

  next_exhibit_id: number | null
  next_exhibit_title: string | null

  all_stops: TourStop[]

  started_at: string
  ended_at: string | null
}

export interface TourNarration {
  exhibit_id: number
  exhibit_title: string
  narration: string
  has_more_stops: boolean
  language: string
  audio_base64: string | null
}

// ── Single-exhibit navigation (non-tour) ───────────────────────────────
export type NavState =
  | { active: false; blocked_by_tour: boolean }
  | {
      active: true
      blocked_by_tour: false
      request_id: number
      exhibit_id: number
      exhibit_title: string
      exhibit_image: string | null
      target_x: number | null
      target_y: number | null
      status: 'in_progress' | 'arrived' | 'cancelled'
      language: string
    }

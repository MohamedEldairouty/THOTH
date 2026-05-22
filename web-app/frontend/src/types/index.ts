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
  id: number
  status: 'idle' | 'navigating' | 'charging'
  battery: number
  current_hall_id: number | null
  current_x: number
  current_y: number
  updated_at: string
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

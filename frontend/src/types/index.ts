export type UserRole = 'teacher' | 'student'

export interface AuthUser {
  access_token: string
  user_id: string
  name: string
  email: string
  role: UserRole
  roll_number?: string
  face_enrolled: boolean
}

export type SessionStatus = 'active' | 'closed'

export interface AttendanceSession {
  id: string
  teacher_id: string
  course_name: string
  status: SessionStatus
  classroom_lat: number
  classroom_lon: number
  room_radius_meters: number
  created_at: string
  expires_at: string | null
}

export interface CreateSessionRequest {
  course_name: string
  classroom_lat: number
  classroom_lon: number
  room_radius_meters: number
  duration_minutes: number
}

export type AttendanceStatus =
  | 'present'
  | 'rejected_location'
  | 'rejected_face'
  | 'rejected_liveness'
  | 'rejected_no_face'

export interface AttendanceRecord {
  id: number
  student_id: string
  student_name: string
  student_email: string
  roll_number: string | null
  status: AttendanceStatus
  face_similarity_score: number | null
  liveness_score: number | null
  distance_from_class_meters: number | null
  marked_at: string
}

export interface AttendanceResult {
  success: boolean
  status: AttendanceStatus
  message: string
  face_similarity_score?: number
  liveness_score?: number
  liveness_challenge_passed?: boolean
  distance_meters?: number
  debug_image_b64?: string
}

export interface Student {
  id: string
  name: string
  email: string
  roll_number: string | null
  face_enrolled: boolean
}

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus, X, Clock, MapPin, Users, CheckCircle, XCircle,
  ChevronDown, ChevronUp, RefreshCw, BookOpen, Trash2, Crosshair, Mail
} from 'lucide-react'
import toast from 'react-hot-toast'
import Navbar from '../../components/Navbar'
import PageTransition from '../../components/PageTransition'
import Card3D from '../../components/Card3D'
import { GridPattern } from '../../components/BauhausShapes'
import api from '../../api/axios'
import type { AttendanceSession, AttendanceRecord, Student } from '../../types'

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } },
}

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
}

export default function TeacherDashboard() {
  const [sessions, setSessions] = useState<AttendanceSession[]>([])
  const [students, setStudents] = useState<Student[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [expandedSession, setExpandedSession] = useState<string | null>(null)
  const [attendanceMap, setAttendanceMap] = useState<Record<string, AttendanceRecord[]>>({})
  const [activeTab, setActiveTab] = useState<'sessions' | 'students'>('sessions')
  const [loading, setLoading] = useState(true)

  // GPS state for teacher's current location
  const [gps, setGps] = useState<{ lat: number; lon: number; accuracy: number } | null>(null)
  const [gpsLoading, setGpsLoading] = useState(false)
  const [gpsError, setGpsError] = useState<string | null>(null)

  // Create session form
  const [courseName, setCourseName] = useState('')
  const [radius, setRadius] = useState(30)
  const [duration, setDuration] = useState(30)

  const fetchSessions = useCallback(async () => {
    try {
      const { data } = await api.get('/sessions/active')
      setSessions(data)
    } catch {
      toast.error('Failed to load sessions')
    }
  }, [])

  const fetchStudents = useCallback(async () => {
    try {
      const { data } = await api.get('/students/')
      setStudents(data)
    } catch {
      toast.error('Failed to load students')
    }
  }, [])

  useEffect(() => {
    Promise.all([fetchSessions(), fetchStudents()]).finally(() => setLoading(false))
  }, [fetchSessions, fetchStudents])

  const detectLocation = () => {
    if (!navigator.geolocation) {
      setGpsError('Geolocation not supported by your browser')
      return
    }
    setGpsLoading(true)
    setGpsError(null)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGps({ lat: pos.coords.latitude, lon: pos.coords.longitude, accuracy: pos.coords.accuracy })
        setGpsLoading(false)
        toast.success(`Location detected! (accuracy: ${Math.round(pos.coords.accuracy)}m)`)
      },
      (err) => {
        setGpsError(err.message)
        setGpsLoading(false)
        toast.error('Failed to get location: ' + err.message)
      },
      { enableHighAccuracy: true, timeout: 15000 },
    )
  }

  const createSession = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!gps) {
      toast.error('Detect your location first!')
      return
    }
    try {
      await api.post('/sessions/create', {
        course_name: courseName,
        classroom_lat: gps.lat,
        classroom_lon: gps.lon,
        classroom_gps_accuracy: gps.accuracy,
        room_radius_meters: radius,
        duration_minutes: duration,
      })
      toast.success('Session created at your current location!')
      setShowCreate(false)
      setCourseName('')
      fetchSessions()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create session')
    }
  }

  const closeSession = async (id: string) => {
    try {
      await api.post(`/sessions/${id}/close`)
      toast.success('Session closed')
      fetchSessions()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to close session')
    }
  }

  const fetchAttendance = async (sessionId: string) => {
    if (expandedSession === sessionId) {
      setExpandedSession(null)
      return
    }
    try {
      const { data } = await api.get(`/sessions/${sessionId}/attendance`)
      setAttendanceMap((m) => ({ ...m, [sessionId]: data }))
      setExpandedSession(sessionId)
    } catch {
      toast.error('Failed to load attendance')
    }
  }

  const removeEnrollment = async (studentId: string) => {
    try {
      await api.delete(`/students/${studentId}/enrollment`)
      toast.success('Enrollment removed')
      fetchStudents()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to remove enrollment')
    }
  }

  const getStatusBadge = (status: string) => {
    const map: Record<string, { bg: string; text: string; label: string }> = {
      present: { bg: 'bg-green-100', text: 'text-green-800', label: 'Present' },
      rejected_location: { bg: 'bg-orange-100', text: 'text-orange-800', label: 'Location Fail' },
      rejected_face: { bg: 'bg-red-100', text: 'text-red-800', label: 'Face Fail' },
      rejected_liveness: { bg: 'bg-purple-100', text: 'text-purple-800', label: 'Liveness Fail' },
      rejected_no_face: { bg: 'bg-gray-100', text: 'text-gray-800', label: 'No Face' },
    }
    const s = map[status] || { bg: 'bg-gray-100', text: 'text-gray-800', label: status }
    return (
      <span className={`px-2 py-0.5 text-xs font-mono uppercase ${s.bg} ${s.text}`}>
        {s.label}
      </span>
    )
  }

  const timeLeft = (expiresAt: string | null) => {
    if (!expiresAt) return 'No expiry'
    const diff = new Date(expiresAt).getTime() - Date.now()
    if (diff <= 0) return 'Expired'
    const mins = Math.floor(diff / 60000)
    return `${mins}m left`
  }

  return (
    <div className="min-h-screen bg-cream">
      <Navbar />
      <PageTransition>
        <div className="relative">
          <GridPattern />
          <div className="max-w-7xl mx-auto px-6 py-8 relative z-10">
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
              <div>
                <h1 className="font-display text-4xl text-navy">Teacher Dashboard</h1>
                <div className="flex gap-1.5 mt-2">
                  <div className="w-10 h-1 bg-bauhaus-red" />
                  <div className="w-10 h-1 bg-bauhaus-gold" />
                  <div className="w-10 h-1 bg-navy" />
                </div>
              </div>
              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => setShowCreate(!showCreate)}
                className="px-5 py-3 bg-navy text-cream font-semibold flex items-center gap-2 border-2 border-navy shadow-bauhaus-sm hover:shadow-bauhaus transition-shadow"
              >
                {showCreate ? <X size={18} /> : <Plus size={18} />}
                {showCreate ? 'Cancel' : 'New Session'}
              </motion.button>
            </div>

            {/* Create session form */}
            <AnimatePresence>
              {showCreate && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden mb-8"
                >
                  <Card3D className="p-6">
                    <h2 className="font-display text-xl text-navy mb-4">Create Attendance Session</h2>
                    <form onSubmit={createSession} className="space-y-4">
                      <div>
                        <label className="text-xs font-mono uppercase tracking-wider text-slate mb-1 block">
                          Course Name
                        </label>
                        <input
                          value={courseName}
                          onChange={(e) => setCourseName(e.target.value)}
                          placeholder="e.g. CS301 — Machine Learning"
                          required
                          className="w-full px-4 py-3 bg-cream border-2 border-navy/20 focus:border-navy outline-none text-navy"
                        />
                      </div>

                      {/* GPS location — auto-detected */}
                      <div className="p-4 bg-cream border-2 border-navy/10">
                        <div className="flex items-center justify-between mb-3">
                          <label className="text-xs font-mono uppercase tracking-wider text-slate flex items-center gap-2">
                            <MapPin size={14} /> Classroom Location
                          </label>
                          <motion.button
                            type="button"
                            whileHover={{ scale: 1.03 }}
                            whileTap={{ scale: 0.97 }}
                            onClick={detectLocation}
                            disabled={gpsLoading}
                            className="px-4 py-2 bg-navy text-cream text-xs font-mono uppercase flex items-center gap-2 disabled:opacity-50"
                          >
                            {gpsLoading ? (
                              <motion.div
                                animate={{ rotate: 360 }}
                                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                                className="w-3.5 h-3.5 border-2 border-cream/30 border-t-cream rounded-full"
                              />
                            ) : (
                              <Crosshair size={14} />
                            )}
                            {gpsLoading ? 'Detecting...' : 'Use My Location'}
                          </motion.button>
                        </div>
                        {gps ? (
                          <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2 text-green-700 bg-green-50 px-3 py-2 border border-green-200">
                              <CheckCircle size={16} />
                              <span className="font-mono text-sm">
                                {gps.lat.toFixed(6)}, {gps.lon.toFixed(6)} (±{Math.round(gps.accuracy)}m)
                              </span>
                            </div>
                            <p className="text-xs text-slate">
                              Session will be pinned to your current location. Students must be within the radius below.
                            </p>
                          </div>
                        ) : gpsError ? (
                          <p className="text-sm text-bauhaus-red flex items-center gap-2">
                            <XCircle size={16} /> {gpsError}
                          </p>
                        ) : (
                          <p className="text-sm text-slate">
                            Click "Use My Location" to pin the session to your classroom. You must be physically in the classroom.
                          </p>
                        )}
                      </div>

                      <div className="grid md:grid-cols-2 gap-4">
                        <div>
                          <label className="text-xs font-mono uppercase tracking-wider text-slate mb-1 block">
                            Geofence Radius (meters)
                          </label>
                          <input
                            type="number"
                            min={10}
                            max={200}
                            value={radius}
                            onChange={(e) => setRadius(+e.target.value)}
                            className="w-full px-4 py-3 bg-cream border-2 border-navy/20 focus:border-navy outline-none font-mono text-sm"
                          />
                          <p className="text-xs text-slate mt-1">
                            Students outside this radius cannot mark attendance (10–200m)
                          </p>
                        </div>
                        <div>
                          <label className="text-xs font-mono uppercase tracking-wider text-slate mb-1 block">
                            Duration (minutes)
                          </label>
                          <input
                            type="number"
                            min={5}
                            max={180}
                            value={duration}
                            onChange={(e) => setDuration(+e.target.value)}
                            className="w-full px-4 py-3 bg-cream border-2 border-navy/20 focus:border-navy outline-none font-mono text-sm"
                          />
                          <p className="text-xs text-slate mt-1">
                            Session auto-closes after this duration
                          </p>
                        </div>
                      </div>

                      <motion.button
                        type="submit"
                        disabled={!gps}
                        whileHover={{ scale: gps ? 1.02 : 1 }}
                        whileTap={{ scale: gps ? 0.98 : 1 }}
                        className="w-full py-3.5 bg-bauhaus-red text-cream font-semibold border-2 border-bauhaus-red shadow-bauhaus-sm disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        {gps ? 'Create Session' : 'Detect Location First'}
                      </motion.button>
                    </form>
                  </Card3D>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Tabs */}
            <div className="flex gap-1 mb-6">
              {(['sessions', 'students'] as const).map((tab) => (
                <motion.button
                  key={tab}
                  whileTap={{ scale: 0.97 }}
                  onClick={() => setActiveTab(tab)}
                  className={`px-6 py-2.5 font-mono text-sm uppercase tracking-wider border-2 transition-colors ${
                    activeTab === tab
                      ? 'bg-navy text-cream border-navy'
                      : 'bg-white text-navy border-navy/20 hover:border-navy/40'
                  }`}
                >
                  {tab === 'sessions' ? (
                    <span className="flex items-center gap-2"><BookOpen size={16} /> Sessions</span>
                  ) : (
                    <span className="flex items-center gap-2"><Users size={16} /> Students</span>
                  )}
                </motion.button>
              ))}
              <motion.button
                whileTap={{ scale: 0.95 }}
                whileHover={{ rotate: 180 }}
                transition={{ duration: 0.4 }}
                onClick={() => { fetchSessions(); fetchStudents() }}
                className="ml-auto px-3 py-2.5 border-2 border-navy/20 hover:border-navy/40 transition-colors"
              >
                <RefreshCw size={16} />
              </motion.button>
            </div>

            {loading ? (
              <div className="text-center py-20">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  className="w-10 h-10 border-3 border-navy/20 border-t-navy rounded-full mx-auto"
                />
              </div>
            ) : activeTab === 'sessions' ? (
              /* Sessions list */
              <motion.div initial="hidden" animate="show" variants={stagger} className="space-y-4">
                {sessions.length === 0 ? (
                  <motion.div variants={fadeUp} className="text-center py-16 text-slate">
                    <BookOpen size={48} className="mx-auto mb-4 opacity-30" />
                    <p className="font-display text-xl">No active sessions</p>
                    <p className="text-sm mt-1">Create a new session to start taking attendance.</p>
                  </motion.div>
                ) : (
                  sessions.map((s) => (
                    <motion.div key={s.id} variants={fadeUp}>
                      <Card3D className="overflow-hidden">
                        <div className="p-5">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-3 mb-1">
                                <span className="font-mono text-sm text-bauhaus-gold bg-bauhaus-gold/10 px-2 py-0.5 border border-bauhaus-gold/20">
                                  {s.id}
                                </span>
                                <span className="font-mono text-xs text-green-700 bg-green-100 px-2 py-0.5 uppercase">
                                  Active
                                </span>
                              </div>
                              <h3 className="font-display text-xl text-navy mt-2">{s.course_name}</h3>
                              <div className="flex items-center gap-4 mt-2 text-xs font-mono text-slate">
                                <span className="flex items-center gap-1">
                                  <Clock size={12} /> {timeLeft(s.expires_at)}
                                </span>
                                <span className="flex items-center gap-1">
                                  <MapPin size={12} /> {s.classroom_lat.toFixed(4)}, {s.classroom_lon.toFixed(4)}
                                </span>
                                <span>Radius: {s.room_radius_meters}m</span>
                              </div>
                            </div>
                            <div className="flex gap-2">
                              <motion.button
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={() => fetchAttendance(s.id)}
                                className="px-3 py-2 text-xs font-mono uppercase bg-cream border-2 border-navy/20 hover:border-navy flex items-center gap-1 transition-colors"
                              >
                                {expandedSession === s.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                Records
                              </motion.button>
                              <motion.button
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={() => closeSession(s.id)}
                                className="px-3 py-2 text-xs font-mono uppercase bg-bauhaus-red text-cream border-2 border-bauhaus-red transition-colors"
                              >
                                Close
                              </motion.button>
                            </div>
                          </div>
                        </div>

                        {/* Attendance records expansion */}
                        <AnimatePresence>
                          {expandedSession === s.id && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: 'auto', opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              className="overflow-hidden border-t-2 border-navy/10"
                            >
                              <div className="p-5 bg-cream/50">
                                {!attendanceMap[s.id]?.length ? (
                                  <p className="text-sm text-slate text-center py-4">No attendance records yet.</p>
                                ) : (
                                  <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                      <thead>
                                        <tr className="text-xs font-mono uppercase tracking-wider text-slate border-b-2 border-navy/10">
                                          <th className="text-left py-2 pr-4">Student</th>
                                          <th className="text-left py-2 pr-4">Email</th>
                                          <th className="text-left py-2 pr-4">Roll No</th>
                                          <th className="text-left py-2 pr-4">Status</th>
                                          <th className="text-right py-2 pr-4">Face Score</th>
                                          <th className="text-right py-2 pr-4">Liveness</th>
                                          <th className="text-right py-2 pr-4">Distance</th>
                                          <th className="text-right py-2">Time</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {attendanceMap[s.id].map((rec) => (
                                          <motion.tr
                                            key={rec.id}
                                            initial={{ opacity: 0, x: -10 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            className="border-b border-navy/5"
                                          >
                                            <td className="py-2.5 pr-4 font-medium">{rec.student_name}</td>
                                            <td className="py-2.5 pr-4 font-mono text-xs text-bauhaus-blue">
                                              {rec.student_email}
                                            </td>
                                            <td className="py-2.5 pr-4 font-mono text-xs">{rec.roll_number || '—'}</td>
                                            <td className="py-2.5 pr-4">{getStatusBadge(rec.status)}</td>
                                            <td className="py-2.5 pr-4 text-right font-mono text-xs">
                                              {rec.face_similarity_score != null
                                                ? `${(rec.face_similarity_score * 100).toFixed(1)}%`
                                                : '—'}
                                            </td>
                                            <td className="py-2.5 pr-4 text-right font-mono text-xs">
                                              {rec.liveness_score != null
                                                ? `${(rec.liveness_score * 100).toFixed(1)}%`
                                                : '—'}
                                            </td>
                                            <td className="py-2.5 pr-4 text-right font-mono text-xs">
                                              {rec.distance_from_class_meters != null
                                                ? `${rec.distance_from_class_meters.toFixed(1)}m`
                                                : '—'}
                                            </td>
                                            <td className="py-2.5 text-right font-mono text-xs">
                                              {new Date(rec.marked_at).toLocaleTimeString()}
                                            </td>
                                          </motion.tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                )}
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </Card3D>
                    </motion.div>
                  ))
                )}
              </motion.div>
            ) : (
              /* Students list */
              <motion.div initial="hidden" animate="show" variants={stagger} className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {students.map((st) => (
                  <motion.div key={st.id} variants={fadeUp}>
                    <Card3D className="p-5">
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="font-display text-lg text-navy">{st.name}</h3>
                          <p className="text-xs font-mono text-bauhaus-blue mt-0.5 flex items-center gap-1">
                            <Mail size={10} /> {st.email}
                          </p>
                          {st.roll_number && (
                            <p className="text-xs font-mono text-bauhaus-gold mt-1">
                              Roll: {st.roll_number}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-1.5">
                          {st.face_enrolled ? (
                            <CheckCircle size={18} className="text-green-600" />
                          ) : (
                            <XCircle size={18} className="text-red-400" />
                          )}
                          <span className="text-xs font-mono">
                            {st.face_enrolled ? 'Enrolled' : 'Not enrolled'}
                          </span>
                        </div>
                      </div>
                      {st.face_enrolled && (
                        <motion.button
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={() => removeEnrollment(st.id)}
                          className="mt-4 w-full py-2 text-xs font-mono uppercase bg-red-50 text-bauhaus-red border border-bauhaus-red/30 hover:border-bauhaus-red flex items-center justify-center gap-1.5 transition-colors"
                        >
                          <Trash2 size={12} /> Remove Enrollment
                        </motion.button>
                      )}
                    </Card3D>
                  </motion.div>
                ))}
              </motion.div>
            )}
          </div>
        </div>
      </PageTransition>
    </div>
  )
}

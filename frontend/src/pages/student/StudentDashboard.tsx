import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Camera, CameraOff, ScanFace, MapPin, Clock, CheckCircle,
  XCircle, AlertTriangle, RefreshCw, Wifi, Mail, ShieldCheck, Lock, UserCheck
} from 'lucide-react'
import toast from 'react-hot-toast'
import Navbar from '../../components/Navbar'
import PageTransition from '../../components/PageTransition'
import Card3D from '../../components/Card3D'
import { GridPattern } from '../../components/BauhausShapes'
import { useAuthStore } from '../../store/authStore'
import api from '../../api/axios'
import type { AttendanceSession, AttendanceResult } from '../../types'

const ALLOWED_DOMAIN = '@muj.manipal.edu'

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } },
}

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
}

type EnrollStep = 'enter_email' | 'otp_sent' | 'verified' | 'done'

export default function StudentDashboard() {
  const { user } = useAuthStore()
  const [sessions, setSessions] = useState<AttendanceSession[]>([])
  const [loading, setLoading] = useState(true)
  const [cameraOn, setCameraOn] = useState(false)
  const [enrolling, setEnrolling] = useState(false)
  const [marking, setMarking] = useState<string | null>(null)
  const [result, setResult] = useState<AttendanceResult | null>(null)
  const [location, setLocation] = useState<{ lat: number; lon: number; accuracy: number } | null>(null)
  const [locError, setLocError] = useState<string | null>(null)

  // Enrollment state — fully self-contained with manual email entry
  const [enrollStep, setEnrollStep] = useState<EnrollStep>('enter_email')
  const [enrollEmail, setEnrollEmail] = useState('')
  const [enrollName, setEnrollName] = useState('')
  const [emailError, setEmailError] = useState<string | null>(null)
  const [otpCode, setOtpCode] = useState('')
  const [otpSending, setOtpSending] = useState(false)
  const [otpVerifying, setOtpVerifying] = useState(false)
  const [verificationToken, setVerificationToken] = useState<string | null>(null)
  const [otpCountdown, setOtpCountdown] = useState(0)
  const [enrolledEmail, setEnrolledEmail] = useState<string | null>(null)

  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const fetchSessions = useCallback(async () => {
    try {
      const { data } = await api.get('/sessions/active')
      setSessions(data)
    } catch {
      toast.error('Failed to load sessions')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  useEffect(() => {
    if (!navigator.geolocation) {
      setLocError('Geolocation not supported')
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => setLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude, accuracy: pos.coords.accuracy }),
      (err) => setLocError(err.message),
      { enableHighAccuracy: true },
    )
  }, [])

  useEffect(() => {
    if (otpCountdown <= 0) return
    const t = setTimeout(() => setOtpCountdown((c) => c - 1), 1000)
    return () => clearTimeout(t)
  }, [otpCountdown])

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: 640, height: 480 },
      })
      if (videoRef.current) videoRef.current.srcObject = stream
      streamRef.current = stream
      setCameraOn(true)
    } catch {
      toast.error('Could not access camera')
    }
  }

  const stopCamera = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setCameraOn(false)
  }

  const captureFrame = (): string | null => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas) return null
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return null
    ctx.drawImage(video, 0, 0)
    return canvas.toDataURL('image/jpeg', 0.9).split(',')[1]
  }

  // ─── Email validation ──────────────────────────────────────────────────────

  const validateEnrollEmail = (value: string) => {
    setEnrollEmail(value)
    if (value.includes('@') && !value.toLowerCase().endsWith(ALLOWED_DOMAIN)) {
      setEmailError(`Only ${ALLOWED_DOMAIN} emails allowed`)
    } else {
      setEmailError(null)
    }
  }

  // ─── OTP Flow ──────────────────────────────────────────────────────────────

  const sendOTP = async () => {
    const email = enrollEmail.toLowerCase().trim()
    if (!email.endsWith(ALLOWED_DOMAIN)) {
      toast.error(`Only ${ALLOWED_DOMAIN} emails allowed`)
      return
    }
    setOtpSending(true)
    try {
      const { data } = await api.post('/auth/send-otp', { email })
      setEnrollStep('otp_sent')
      setOtpCountdown(60)
      if (data.email_delivered) {
        toast.success('OTP sent — check your inbox!')
      } else if (data.dev_otp) {
        // SMTP not configured — show OTP directly for testing
        toast(`Your OTP: ${data.dev_otp}`, { duration: 20000, icon: '🔑' })
      } else {
        toast.success(data.message)
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to send OTP')
    } finally {
      setOtpSending(false)
    }
  }

  const verifyOTP = async () => {
    const email = enrollEmail.toLowerCase().trim()
    if (!otpCode) return
    setOtpVerifying(true)
    try {
      const { data } = await api.post('/auth/verify-otp', {
        email,
        otp_code: otpCode,
      })
      toast.success(data.message)
      setVerificationToken(data.verification_token)
      setEnrollStep('verified')
      setOtpCode('')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'OTP verification failed')
    } finally {
      setOtpVerifying(false)
    }
  }

  const enrollFace = async () => {
    const frame = captureFrame()
    if (!frame) {
      toast.error('Could not capture frame — turn on camera first')
      return
    }
    if (!verificationToken) {
      toast.error('Please verify your email first')
      return
    }
    if (!enrollName.trim()) {
      toast.error('Please enter your full name')
      return
    }
    setEnrolling(true)
    try {
      const { data } = await api.post('/students/enroll-face', {
        face_image_b64: frame,
        verification_token: verificationToken,
        student_name: enrollName.trim(),
      })
      toast.success(`Face enrolled for ${data.enrolled_email}`)
      setEnrolledEmail(data.enrolled_email)
      setEnrollName(data.enrolled_name || enrollName)
      setEnrollStep('done')
      setVerificationToken(null)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Enrollment failed')
      if (err.response?.status === 403) {
        setEnrollStep('enter_email')
        setVerificationToken(null)
      }
    } finally {
      setEnrolling(false)
    }
  }

  const resetEnrollment = () => {
    setEnrollStep('enter_email')
    setEnrollEmail('')
    setEnrollName('')
    setOtpCode('')
    setVerificationToken(null)
    setEnrolledEmail(null)
    setEmailError(null)
  }

  // ─── Mark Attendance ───────────────────────────────────────────────────────

  const markAttendance = async (sessionId: string) => {
    if (!location) {
      toast.error('Location not available')
      return
    }
    const frame = captureFrame()
    if (!frame) {
      toast.error('Could not capture frame — turn on camera first')
      return
    }
    setMarking(sessionId)
    setResult(null)
    try {
      const { data } = await api.post('/attendance/mark', {
        session_id: sessionId,
        student_lat: location.lat,
        student_lon: location.lon,
        student_gps_accuracy: location.accuracy,
        face_image_b64: frame,
      })
      setResult(data)
      if (data.success) {
        toast.success(data.message)
      } else {
        toast.error(data.message)
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Attendance marking failed')
    } finally {
      setMarking(null)
    }
  }

  const timeLeft = (expiresAt: string | null) => {
    if (!expiresAt) return 'Open'
    const diff = new Date(expiresAt).getTime() - Date.now()
    if (diff <= 0) return 'Expired'
    return `${Math.floor(diff / 60000)}m left`
  }

  return (
    <div className="min-h-screen bg-cream">
      <Navbar />
      <PageTransition>
        <div className="relative">
          <GridPattern />
          <div className="max-w-6xl mx-auto px-6 py-8 relative z-10">
            {/* Header */}
            <div className="mb-8">
              <h1 className="font-display text-4xl text-navy">Student Portal</h1>
              <div className="flex gap-1.5 mt-2">
                <div className="w-10 h-1 bg-bauhaus-red" />
                <div className="w-10 h-1 bg-bauhaus-gold" />
                <div className="w-10 h-1 bg-navy" />
              </div>
            </div>

            {/* Security notice */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-3 bg-navy/5 border-2 border-navy/10 flex items-start gap-3"
            >
              <ShieldCheck size={18} className="text-bauhaus-blue mt-0.5 flex-shrink-0" />
              <div className="text-xs text-slate leading-relaxed">
                <strong className="text-navy">Identity Verification:</strong> Each student must verify their
                <strong> @muj.manipal.edu</strong> email via OTP before enrolling their face. One enrollment per email.
                Attendance is verified by face recognition + GPS geofencing + liveness detection. Impersonation attempts are logged.
              </div>
            </motion.div>

            <div className="grid lg:grid-cols-3 gap-6">
              {/* Left column: Camera + enrollment */}
              <div className="lg:col-span-1 space-y-6">
                {/* Camera card */}
                <Card3D className="p-5">
                  <h2 className="font-display text-xl text-navy mb-4 flex items-center gap-2">
                    <Camera size={20} /> Camera
                  </h2>
                  <div className="relative bg-navy aspect-[4/3] flex items-center justify-center overflow-hidden">
                    <video
                      ref={videoRef}
                      autoPlay
                      playsInline
                      muted
                      className={`w-full h-full object-cover ${cameraOn ? '' : 'hidden'}`}
                    />
                    {!cameraOn && (
                      <div className="text-center text-cream/40">
                        <CameraOff size={40} className="mx-auto mb-2" />
                        <p className="text-xs font-mono">Camera off</p>
                      </div>
                    )}
                    {cameraOn && (
                      <motion.div
                        className="absolute inset-4 border-2 border-bauhaus-gold/50 pointer-events-none"
                        animate={{ opacity: [0.3, 0.7, 0.3] }}
                        transition={{ duration: 2, repeat: Infinity }}
                      >
                        <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-bauhaus-gold" />
                        <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-bauhaus-gold" />
                        <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-bauhaus-gold" />
                        <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-bauhaus-gold" />
                      </motion.div>
                    )}
                  </div>
                  <canvas ref={canvasRef} className="hidden" />
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={cameraOn ? stopCamera : startCamera}
                    className={`mt-4 w-full py-2.5 font-mono text-sm uppercase tracking-wider border-2 transition-colors ${
                      cameraOn
                        ? 'bg-bauhaus-red text-cream border-bauhaus-red'
                        : 'bg-navy text-cream border-navy'
                    }`}
                  >
                    {cameraOn ? 'Stop Camera' : 'Start Camera'}
                  </motion.button>
                </Card3D>

                {/* ── Face Enrollment (self-service, manual email) ── */}
                <Card3D className="p-5">
                  <h2 className="font-display text-xl text-navy mb-3 flex items-center gap-2">
                    <ScanFace size={20} /> Face Enrollment
                  </h2>

                  {/* Step indicator */}
                  <div className="flex items-center gap-1 mb-4">
                    {['Enter Email', 'Verify OTP', 'Enroll Face'].map((label, i) => {
                      const isDone =
                        i === 0 ? ['otp_sent', 'verified', 'done'].includes(enrollStep) :
                        i === 1 ? ['verified', 'done'].includes(enrollStep) :
                        enrollStep === 'done'
                      const isActive =
                        i === 0 ? enrollStep === 'enter_email' :
                        i === 1 ? enrollStep === 'otp_sent' :
                        enrollStep === 'verified'
                      return (
                        <div key={label} className="flex items-center gap-1 flex-1">
                          <div className={`w-6 h-6 flex items-center justify-center text-xs font-mono border-2 flex-shrink-0 ${
                            isDone ? 'bg-green-600 border-green-600 text-white' :
                            isActive ? 'bg-navy border-navy text-cream' :
                            'bg-white border-navy/20 text-slate'
                          }`}>
                            {isDone ? '✓' : i + 1}
                          </div>
                          <span className="text-[10px] font-mono uppercase text-slate truncate">{label}</span>
                          {i < 2 && <div className="flex-1 h-px bg-navy/10 mx-1 min-w-2" />}
                        </div>
                      )
                    })}
                  </div>

                  <AnimatePresence mode="wait">
                    {/* STEP 1: Enter email */}
                    {enrollStep === 'enter_email' && (
                      <motion.div
                        key="enter_email"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="space-y-3"
                      >
                        <p className="text-xs text-slate">
                          Enter your institutional email to begin face enrollment.
                          A one-time verification code will be sent to confirm your identity.
                        </p>
                        <div>
                          <label className="text-xs font-mono uppercase tracking-wider text-slate mb-1 block">
                            Your Email
                          </label>
                          <div className="relative">
                            <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate/40" />
                            <input
                              type="email"
                              value={enrollEmail}
                              onChange={(e) => validateEnrollEmail(e.target.value)}
                              placeholder="yourname@muj.manipal.edu"
                              className={`w-full pl-9 pr-3 py-2.5 bg-cream border-2 outline-none text-navy text-sm font-mono ${
                                emailError ? 'border-bauhaus-red' : 'border-navy/20 focus:border-navy'
                              }`}
                            />
                          </div>
                          {emailError && (
                            <p className="text-[11px] text-bauhaus-red mt-1 flex items-center gap-1">
                              <AlertTriangle size={10} /> {emailError}
                            </p>
                          )}
                        </div>
                        <motion.button
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={sendOTP}
                          disabled={otpSending || !enrollEmail.toLowerCase().endsWith(ALLOWED_DOMAIN)}
                          className="w-full py-2.5 bg-navy text-cream font-semibold border-2 border-navy flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed text-sm"
                        >
                          {otpSending ? (
                            <motion.div
                              animate={{ rotate: 360 }}
                              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                              className="w-4 h-4 border-2 border-cream/30 border-t-cream rounded-full"
                            />
                          ) : (
                            <Mail size={16} />
                          )}
                          {otpSending ? 'Sending...' : 'Send Verification Code'}
                        </motion.button>
                      </motion.div>
                    )}

                    {/* STEP 2: Enter OTP */}
                    {enrollStep === 'otp_sent' && (
                      <motion.div
                        key="otp_sent"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="space-y-3"
                      >
                        <div className="px-3 py-2 bg-blue-50 border border-blue-200">
                          <p className="text-sm text-blue-800 flex items-center gap-2">
                            <Mail size={14} /> OTP sent to:
                          </p>
                          <p className="font-mono text-sm text-blue-900 font-semibold mt-0.5">
                            {enrollEmail.toLowerCase()}
                          </p>
                          {enrollName && (
                            <p className="text-xs text-blue-600 mt-0.5 flex items-center gap-1">
                              <UserCheck size={12} /> {enrollName}
                            </p>
                          )}
                        </div>
                        <div>
                          <label className="text-xs font-mono uppercase tracking-wider text-slate mb-1 block">
                            Enter 6-digit Code
                          </label>
                          <input
                            type="text"
                            maxLength={6}
                            value={otpCode}
                            onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                            placeholder="000000"
                            className="w-full px-4 py-3 bg-cream border-2 border-navy/20 focus:border-navy outline-none font-mono text-2xl text-center tracking-[0.5em]"
                            autoFocus
                          />
                        </div>
                        <motion.button
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={verifyOTP}
                          disabled={otpVerifying || otpCode.length !== 6}
                          className="w-full py-2.5 bg-bauhaus-blue text-cream font-semibold border-2 border-bauhaus-blue flex items-center justify-center gap-2 disabled:opacity-40 text-sm"
                        >
                          {otpVerifying ? (
                            <motion.div
                              animate={{ rotate: 360 }}
                              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                              className="w-4 h-4 border-2 border-cream/30 border-t-cream rounded-full"
                            />
                          ) : (
                            <Lock size={16} />
                          )}
                          {otpVerifying ? 'Verifying...' : 'Verify Code'}
                        </motion.button>
                        <div className="flex items-center justify-between">
                          <button
                            onClick={() => { setEnrollStep('enter_email'); setOtpCode('') }}
                            className="text-xs text-slate hover:text-navy transition-colors"
                          >
                            ← Change email
                          </button>
                          <button
                            onClick={sendOTP}
                            disabled={otpCountdown > 0 || otpSending}
                            className="text-xs text-bauhaus-blue hover:underline disabled:opacity-40 disabled:no-underline font-mono"
                          >
                            {otpCountdown > 0 ? `Resend in ${otpCountdown}s` : 'Resend code'}
                          </button>
                        </div>
                      </motion.div>
                    )}

                    {/* STEP 3: Email verified — capture face */}
                    {enrollStep === 'verified' && (
                      <motion.div
                        key="verified"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="space-y-3"
                      >
                        <div className="px-3 py-2 bg-green-50 border border-green-200">
                          <p className="text-sm text-green-800 flex items-center gap-2">
                            <CheckCircle size={14} /> Email verified
                          </p>
                          <p className="font-mono text-sm text-green-900 font-semibold mt-0.5">
                            {enrollEmail.toLowerCase()}
                          </p>
                        </div>
                        <div>
                          <label className="text-xs font-mono uppercase tracking-wider text-slate mb-1 block">
                            Your Full Name
                          </label>
                          <div className="relative">
                            <UserCheck size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate/40" />
                            <input
                              type="text"
                              value={enrollName}
                              onChange={(e) => setEnrollName(e.target.value)}
                              placeholder="e.g. Aarav Mehta"
                              className="w-full pl-9 pr-3 py-2.5 bg-cream border-2 border-navy/20 focus:border-navy outline-none text-navy text-sm"
                            />
                          </div>
                        </div>
                        <p className="text-xs text-slate">
                          Look directly at the camera with good lighting.
                          Your face will be permanently linked to <strong className="font-mono">{enrollEmail.toLowerCase()}</strong>.
                        </p>
                        <motion.button
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={enrollFace}
                          disabled={!cameraOn || enrolling || !enrollName.trim()}
                          className="w-full py-2.5 bg-bauhaus-gold text-navy font-bold border-2 border-bauhaus-gold shadow-bauhaus-sm disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm"
                        >
                          {enrolling ? (
                            <motion.div
                              animate={{ rotate: 360 }}
                              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                              className="w-4 h-4 border-2 border-navy/30 border-t-navy rounded-full"
                            />
                          ) : (
                            <ScanFace size={18} />
                          )}
                          {enrolling ? 'Enrolling...' : !cameraOn ? 'Turn on camera first' : 'Capture & Enroll Face'}
                        </motion.button>
                        <p className="text-[10px] font-mono text-slate text-center">
                          Token expires in 10 minutes. One enrollment per email.
                        </p>
                      </motion.div>
                    )}

                    {/* DONE — enrolled successfully */}
                    {enrollStep === 'done' && (
                      <motion.div
                        key="done"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0 }}
                        className="space-y-3"
                      >
                        <div className="px-3 py-3 bg-green-50 border-2 border-green-300">
                          <div className="flex items-center gap-2 mb-1">
                            <CheckCircle size={18} className="text-green-600" />
                            <span className="text-sm text-green-800 font-semibold">Enrollment Complete</span>
                          </div>
                          <p className="font-mono text-sm text-green-900 ml-7">
                            {enrolledEmail}
                          </p>
                          {enrollName && (
                            <p className="text-xs text-green-600 ml-7">{enrollName}</p>
                          )}
                        </div>
                        <motion.button
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={resetEnrollment}
                          className="w-full py-2 text-xs font-mono uppercase bg-cream border-2 border-navy/20 hover:border-navy/40 transition-colors"
                        >
                          Enroll Another Student
                        </motion.button>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </Card3D>

                {/* Location status */}
                <Card3D className="p-5">
                  <h2 className="font-display text-xl text-navy mb-3 flex items-center gap-2">
                    <MapPin size={20} /> Location
                  </h2>
                  {locError ? (
                    <div className="flex items-center gap-2 text-sm text-bauhaus-red">
                      <AlertTriangle size={16} />
                      {locError}
                    </div>
                  ) : location ? (
                    <div className="font-mono text-xs text-slate space-y-1">
                      <p>Lat: {location.lat.toFixed(6)}</p>
                      <p>Lon: {location.lon.toFixed(6)}</p>
                      <p>Accuracy: ±{Math.round(location.accuracy)}m</p>
                      <div className="flex items-center gap-1 text-green-600 mt-2">
                        <Wifi size={12} /> GPS Active
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-slate">Acquiring location...</p>
                  )}
                </Card3D>
              </div>

              {/* Right column: Sessions + results */}
              <div className="lg:col-span-2 space-y-6">
                {/* Result banner */}
                <AnimatePresence>
                  {result && (
                    <motion.div
                      initial={{ opacity: 0, y: -20, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -20, scale: 0.95 }}
                    >
                      <Card3D className={`p-6 !border-2 ${result.success ? '!border-green-500' : '!border-bauhaus-red'}`}>
                        <div className="flex items-start gap-4">
                          {result.success ? (
                            <CheckCircle size={32} className="text-green-500 flex-shrink-0 mt-1" />
                          ) : (
                            <XCircle size={32} className="text-bauhaus-red flex-shrink-0 mt-1" />
                          )}
                          <div className="flex-1">
                            <h3 className="font-display text-xl text-navy">
                              {result.success ? 'Attendance Marked!' : 'Verification Failed'}
                            </h3>
                            <p className="text-sm text-slate mt-1">{result.message}</p>
                            {result.success && (
                              <p className="text-xs font-mono text-green-700 mt-1">
                                Recorded for: {user?.email}
                              </p>
                            )}
                            <div className="grid grid-cols-3 gap-3 mt-4">
                              {result.face_similarity_score != null && (
                                <div className="bg-cream p-3 border border-navy/10">
                                  <p className="text-xs font-mono uppercase text-slate">Face Match</p>
                                  <p className="font-mono text-lg font-bold text-navy">
                                    {(result.face_similarity_score * 100).toFixed(1)}%
                                  </p>
                                </div>
                              )}
                              {result.liveness_score != null && (
                                <div className="bg-cream p-3 border border-navy/10">
                                  <p className="text-xs font-mono uppercase text-slate">Liveness</p>
                                  <p className="font-mono text-lg font-bold text-navy">
                                    {(result.liveness_score * 100).toFixed(1)}%
                                  </p>
                                </div>
                              )}
                              {result.distance_meters != null && (
                                <div className="bg-cream p-3 border border-navy/10">
                                  <p className="text-xs font-mono uppercase text-slate">Distance</p>
                                  <p className="font-mono text-lg font-bold text-navy">
                                    {result.distance_meters.toFixed(1)}m
                                  </p>
                                </div>
                              )}
                            </div>
                          </div>
                          <motion.button
                            whileTap={{ scale: 0.9 }}
                            onClick={() => setResult(null)}
                            className="text-slate hover:text-navy"
                          >
                            <XCircle size={20} />
                          </motion.button>
                        </div>
                      </Card3D>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Active sessions */}
                <div className="flex items-center justify-between mb-2">
                  <h2 className="font-display text-2xl text-navy">Active Sessions</h2>
                  <motion.button
                    whileTap={{ scale: 0.95 }}
                    whileHover={{ rotate: 180 }}
                    transition={{ duration: 0.4 }}
                    onClick={fetchSessions}
                    className="p-2 border-2 border-navy/20 hover:border-navy/40 transition-colors"
                  >
                    <RefreshCw size={16} />
                  </motion.button>
                </div>

                {loading ? (
                  <div className="text-center py-16">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                      className="w-10 h-10 border-3 border-navy/20 border-t-navy rounded-full mx-auto"
                    />
                  </div>
                ) : sessions.length === 0 ? (
                  <Card3D className="p-10 text-center">
                    <Clock size={48} className="mx-auto mb-4 text-slate/30" />
                    <p className="font-display text-xl text-slate">No active sessions</p>
                    <p className="text-sm text-slate/70 mt-1">Wait for your teacher to start a session.</p>
                  </Card3D>
                ) : (
                  <motion.div initial="hidden" animate="show" variants={stagger} className="space-y-4">
                    {sessions.map((s) => (
                      <motion.div key={s.id} variants={fadeUp}>
                        <Card3D className="p-5">
                          <div className="flex items-center justify-between">
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-mono text-sm text-bauhaus-gold bg-bauhaus-gold/10 px-2 py-0.5 border border-bauhaus-gold/20">
                                  {s.id}
                                </span>
                                <span className="font-mono text-xs text-green-700 bg-green-100 px-2 py-0.5 uppercase flex items-center gap-1">
                                  <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                                  Live
                                </span>
                              </div>
                              <h3 className="font-display text-xl text-navy mt-1">{s.course_name}</h3>
                              <div className="flex items-center gap-4 mt-2 text-xs font-mono text-slate">
                                <span className="flex items-center gap-1">
                                  <Clock size={12} /> {timeLeft(s.expires_at)}
                                </span>
                                <span>Radius: {s.room_radius_meters}m</span>
                              </div>
                            </div>
                            <motion.button
                              whileHover={{ scale: 1.05 }}
                              whileTap={{ scale: 0.95 }}
                              onClick={() => markAttendance(s.id)}
                              disabled={!cameraOn || !location || marking === s.id}
                              className="px-6 py-3 bg-navy text-cream font-semibold border-2 border-navy shadow-bauhaus-sm hover:shadow-bauhaus transition-shadow disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
                            >
                              {marking === s.id ? (
                                <motion.div
                                  animate={{ rotate: 360 }}
                                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                                  className="w-5 h-5 border-2 border-cream/30 border-t-cream rounded-full"
                                />
                              ) : (
                                'Mark Present'
                              )}
                            </motion.button>
                          </div>
                          {(!cameraOn || !location) && (
                            <div className="mt-3 flex gap-3 text-xs font-mono">
                              {!cameraOn && (
                                <span className="text-orange-600 flex items-center gap-1">
                                  <AlertTriangle size={12} /> Camera off
                                </span>
                              )}
                              {!location && (
                                <span className="text-orange-600 flex items-center gap-1">
                                  <AlertTriangle size={12} /> No GPS
                                </span>
                              )}
                            </div>
                          )}
                        </Card3D>
                      </motion.div>
                    ))}
                  </motion.div>
                )}
              </div>
            </div>
          </div>
        </div>
      </PageTransition>
    </div>
  )
}

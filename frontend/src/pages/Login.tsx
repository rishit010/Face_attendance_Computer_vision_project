import { useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate, Link } from 'react-router-dom'
import { ScanFace, Mail, Lock, ArrowRight, ArrowLeft, ShieldAlert } from 'lucide-react'
import toast from 'react-hot-toast'
import Card3D from '../components/Card3D'
import { GridPattern } from '../components/BauhausShapes'
import { useAuthStore } from '../store/authStore'
import api from '../api/axios'

const ALLOWED_DOMAIN = '@muj.manipal.edu'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [domainError, setDomainError] = useState(false)
  const login = useAuthStore((s) => s.login)
  const navigate = useNavigate()

  const validateEmail = (value: string) => {
    setEmail(value)
    if (value.includes('@') && !value.toLowerCase().endsWith(ALLOWED_DOMAIN)) {
      setDomainError(true)
    } else {
      setDomainError(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!email.toLowerCase().endsWith(ALLOWED_DOMAIN)) {
      toast.error(`Only ${ALLOWED_DOMAIN} email addresses are allowed`)
      return
    }

    setLoading(true)
    try {
      const { data } = await api.post('/auth/login', { email: email.toLowerCase().trim(), password })
      login(data)
      toast.success(`Welcome, ${data.name}!`)
      navigate(data.role === 'teacher' ? '/teacher' : '/student')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-cream relative flex items-center justify-center px-6">
      <GridPattern />

      {/* Bauhaus decorative elements */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="absolute top-20 left-20 w-32 h-32 border-4 border-bauhaus-gold/20 rotate-45 hidden lg:block"
      />
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.7 }}
        className="absolute bottom-20 right-20 w-24 h-24 bg-bauhaus-red/10 rounded-full hidden lg:block"
      />

      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className="w-full max-w-md relative z-10"
      >
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-slate hover:text-navy mb-8 transition-colors"
        >
          <ArrowLeft size={16} />
          Back to home
        </Link>

        <Card3D className="p-8">
          {/* Header */}
          <div className="text-center mb-8">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 300, delay: 0.2 }}
              className="w-16 h-16 bg-navy mx-auto mb-4 flex items-center justify-center"
            >
              <ScanFace size={32} className="text-bauhaus-gold" />
            </motion.div>
            <h1 className="font-display text-3xl text-navy">Sign In</h1>
            <p className="text-xs font-mono text-slate mt-2 uppercase tracking-wider">
              Institutional Login Only
            </p>
            <div className="flex justify-center gap-1.5 mt-3">
              <div className="w-8 h-1 bg-bauhaus-red" />
              <div className="w-8 h-1 bg-bauhaus-gold" />
              <div className="w-8 h-1 bg-navy" />
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="text-xs font-mono uppercase tracking-wider text-slate mb-1.5 block">
                Institutional Email
              </label>
              <div className="relative">
                <Mail size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate/50" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => validateEmail(e.target.value)}
                  placeholder="yourname@muj.manipal.edu"
                  required
                  className={`w-full pl-10 pr-4 py-3 bg-cream border-2 outline-none text-navy font-sans transition-colors placeholder:text-slate/40 ${
                    domainError ? 'border-bauhaus-red focus:border-bauhaus-red' : 'border-navy/20 focus:border-navy'
                  }`}
                />
              </div>
              {domainError && (
                <motion.p
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-xs text-bauhaus-red mt-1.5 flex items-center gap-1"
                >
                  <ShieldAlert size={12} />
                  Only {ALLOWED_DOMAIN} emails are permitted
                </motion.p>
              )}
            </div>

            <div>
              <label className="text-xs font-mono uppercase tracking-wider text-slate mb-1.5 block">
                Password
              </label>
              <div className="relative">
                <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate/50" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                  required
                  className="w-full pl-10 pr-4 py-3 bg-cream border-2 border-navy/20 focus:border-navy outline-none text-navy font-sans transition-colors placeholder:text-slate/40"
                />
              </div>
            </div>

            <motion.button
              type="submit"
              disabled={loading || domainError}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="w-full py-3.5 bg-navy text-cream font-semibold flex items-center justify-center gap-2 border-2 border-navy shadow-bauhaus-sm hover:shadow-bauhaus transition-shadow disabled:opacity-50"
            >
              {loading ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  className="w-5 h-5 border-2 border-cream/30 border-t-cream rounded-full"
                />
              ) : (
                <>
                  Sign In <ArrowRight size={18} />
                </>
              )}
            </motion.button>
          </form>

          {/* Domain notice */}
          <div className="mt-5 p-3 bg-navy/5 border border-navy/10 flex items-start gap-2">
            <ShieldAlert size={14} className="text-bauhaus-blue mt-0.5 flex-shrink-0" />
            <p className="text-[11px] text-slate leading-relaxed">
              Access restricted to <strong>@muj.manipal.edu</strong> accounts.
              Students must verify their email via OTP before face enrollment.
              All attendance records are linked to your verified email.
            </p>
          </div>

          {/* Demo accounts hint */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            className="mt-4 p-4 bg-cream/50 border border-navy/10"
          >
            <p className="text-xs font-mono text-slate/70 mb-2 uppercase tracking-wider">Login Accounts</p>
            <div className="space-y-1 text-xs font-mono text-navy/70">
              <p>Teacher: teacher@muj.manipal.edu / teacher123</p>
              <p>Student Portal: student@muj.manipal.edu / student123</p>
            </div>
          </motion.div>
        </Card3D>
      </motion.div>
    </div>
  )
}

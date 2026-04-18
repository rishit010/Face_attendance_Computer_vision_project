import { motion } from 'framer-motion'
import { useNavigate, Link } from 'react-router-dom'
import { LogOut, ScanFace, User } from 'lucide-react'
import { useAuthStore } from '../store/authStore'

export default function Navbar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <motion.nav
      initial={{ y: -80 }}
      animate={{ y: 0 }}
      transition={{ type: 'spring', stiffness: 200, damping: 25 }}
      className="bg-navy text-cream border-b-4 border-bauhaus-gold sticky top-0 z-50"
    >
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 group">
          <motion.div
            whileHover={{ rotate: 360 }}
            transition={{ duration: 0.6 }}
            className="w-9 h-9 bg-bauhaus-red rounded-full flex items-center justify-center"
          >
            <ScanFace size={20} className="text-cream" />
          </motion.div>
          <span className="font-display text-xl tracking-tight">FaceAttend</span>
        </Link>

        {user && (
          <div className="flex items-center gap-5">
            <div className="flex items-center gap-2 text-sm text-cream/70">
              <User size={16} />
              <span className="font-medium text-cream">{user.name}</span>
              <span className="px-2 py-0.5 text-xs font-mono uppercase tracking-wider bg-bauhaus-gold/20 text-bauhaus-gold border border-bauhaus-gold/30">
                {user.role}
              </span>
            </div>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleLogout}
              className="flex items-center gap-1.5 text-sm text-cream/60 hover:text-bauhaus-red transition-colors"
            >
              <LogOut size={16} />
              Logout
            </motion.button>
          </div>
        )}
      </div>
    </motion.nav>
  )
}

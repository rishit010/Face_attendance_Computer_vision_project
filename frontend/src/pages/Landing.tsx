import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ScanFace, Shield, MapPin, Zap, ChevronRight } from 'lucide-react'
import { FloatingCircle, FloatingSquare, FloatingTriangle, GridPattern } from '../components/BauhausShapes'
import Card3D from '../components/Card3D'

const features = [
  {
    icon: ScanFace,
    title: 'Face Recognition',
    desc: 'ArcFace deep-learning embeddings verify student identity with sub-second latency.',
    color: 'bg-bauhaus-red',
  },
  {
    icon: Shield,
    title: 'Liveness Detection',
    desc: 'Passive and active anti-spoofing prevents photos, videos, and mask attacks.',
    color: 'bg-bauhaus-blue',
  },
  {
    icon: MapPin,
    title: 'Geofencing',
    desc: 'GPS classroom radius ensures students are physically present in the room.',
    color: 'bg-bauhaus-gold',
  },
  {
    icon: Zap,
    title: 'Real-time Pipeline',
    desc: 'Image filters, detection, quality checks, and recognition in one optimized pass.',
    color: 'bg-navy',
  },
]

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12 } },
}

const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] } },
}

export default function Landing() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-cream relative overflow-hidden">
      <GridPattern />

      {/* Bauhaus floating shapes */}
      <FloatingCircle className="w-32 h-32 bg-bauhaus-red/10 top-20 -left-10" />
      <FloatingSquare className="w-20 h-20 bg-bauhaus-gold/15 border-4 border-bauhaus-gold/30 top-40 right-20" />
      <FloatingTriangle className="text-bauhaus-blue/10 bottom-40 left-20" />
      <FloatingCircle className="w-16 h-16 bg-navy/5 bottom-20 right-40" />

      {/* Hero */}
      <section className="relative max-w-7xl mx-auto px-6 pt-20 pb-32">
        <motion.div
          initial="hidden"
          animate="show"
          variants={stagger}
          className="text-center max-w-3xl mx-auto"
        >
          {/* Bauhaus decorative bar */}
          <motion.div variants={fadeUp} className="flex justify-center gap-2 mb-8">
            <div className="w-12 h-3 bg-bauhaus-red" />
            <div className="w-12 h-3 bg-bauhaus-gold" />
            <div className="w-12 h-3 bg-navy" />
          </motion.div>

          <motion.div variants={fadeUp} className="mb-6">
            <span className="inline-block px-4 py-1.5 text-xs font-mono uppercase tracking-[0.2em] bg-navy text-cream border-2 border-navy">
              Computer Vision Powered
            </span>
          </motion.div>

          <motion.h1
            variants={fadeUp}
            className="font-display text-6xl md:text-7xl lg:text-8xl text-navy leading-[0.95] mb-6"
          >
            Face
            <br />
            <span className="text-bauhaus-red">Attendance</span>
            <br />
            System
          </motion.h1>

          <motion.p
            variants={fadeUp}
            className="text-lg text-slate max-w-xl mx-auto mb-10 leading-relaxed"
          >
            Automated attendance verification using face recognition, liveness detection,
            and classroom geofencing. No proxies. No cheating. Just presence.
          </motion.p>

          <motion.div variants={fadeUp} className="flex justify-center gap-4">
            <motion.button
              whileHover={{ scale: 1.03, x: 2, y: -2 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => navigate('/login')}
              className="px-8 py-4 bg-navy text-cream font-semibold text-lg border-2 border-navy shadow-bauhaus hover:shadow-bauhaus-hover transition-shadow flex items-center gap-2"
            >
              Get Started
              <ChevronRight size={20} />
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
              className="px-8 py-4 bg-transparent text-navy font-semibold text-lg border-2 border-navy hover:bg-navy/5 transition-colors"
            >
              Learn More
            </motion.button>
          </motion.div>
        </motion.div>

        {/* Hero geometric accent */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.8, duration: 0.6 }}
          className="absolute top-16 right-10 hidden lg:block"
        >
          <div className="w-24 h-24 border-4 border-bauhaus-gold rotate-45" />
        </motion.div>
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 1, duration: 0.6 }}
          className="absolute bottom-24 left-10 hidden lg:block"
        >
          <div className="w-16 h-16 bg-bauhaus-red rounded-full opacity-20" />
        </motion.div>
      </section>

      {/* Features */}
      <section id="features" className="relative bg-navy py-24">
        <div className="max-w-7xl mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center mb-16"
          >
            <div className="flex justify-center gap-2 mb-6">
              <div className="w-8 h-1 bg-bauhaus-red" />
              <div className="w-8 h-1 bg-bauhaus-gold" />
              <div className="w-8 h-1 bg-cream/30" />
            </div>
            <h2 className="font-display text-4xl md:text-5xl text-cream mb-4">
              How It Works
            </h2>
            <p className="text-cream/60 max-w-lg mx-auto">
              Four layers of verification ensure every attendance record is legitimate.
            </p>
          </motion.div>

          <motion.div
            initial="hidden"
            whileInView="show"
            viewport={{ once: true }}
            variants={stagger}
            className="grid md:grid-cols-2 lg:grid-cols-4 gap-6"
          >
            {features.map((f, i) => (
              <motion.div key={i} variants={fadeUp}>
                <Card3D className="p-6 h-full !bg-navy-light !border-navy-lighter !shadow-none">
                  <div className={`w-12 h-12 ${f.color} flex items-center justify-center mb-4`}>
                    <f.icon size={24} className="text-cream" />
                  </div>
                  <h3 className="font-display text-xl text-cream mb-2">{f.title}</h3>
                  <p className="text-cream/50 text-sm leading-relaxed">{f.desc}</p>
                </Card3D>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Pipeline diagram section */}
      <section className="py-24 bg-cream relative">
        <GridPattern />
        <div className="max-w-5xl mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="font-display text-4xl md:text-5xl text-navy mb-4">
              Verification Pipeline
            </h2>
            <p className="text-slate max-w-lg mx-auto">
              Every attendance request passes through this multi-stage verification.
            </p>
          </motion.div>

          <motion.div
            initial="hidden"
            whileInView="show"
            viewport={{ once: true }}
            variants={stagger}
            className="flex flex-col md:flex-row items-center justify-between gap-4"
          >
            {['GPS Check', 'Face Detect', 'Liveness', 'Recognition', 'Confirmed'].map((step, i) => (
              <motion.div key={step} variants={fadeUp} className="flex items-center gap-4">
                <div className="flex flex-col items-center">
                  <div className={`w-14 h-14 flex items-center justify-center font-mono text-lg font-bold border-2 border-navy ${
                    i === 4 ? 'bg-bauhaus-gold text-navy' : 'bg-white text-navy'
                  }`}>
                    {i + 1}
                  </div>
                  <span className="text-xs font-mono mt-2 text-slate">{step}</span>
                </div>
                {i < 4 && (
                  <ChevronRight size={20} className="text-navy/30 hidden md:block" />
                )}
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-navy border-t-4 border-bauhaus-gold py-10">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-bauhaus-red rounded-full flex items-center justify-center">
              <ScanFace size={16} className="text-cream" />
            </div>
            <span className="font-display text-lg text-cream">FaceAttend</span>
          </div>
          <p className="text-cream/40 text-sm font-mono">
            Built with InsightFace + FastAPI + React
          </p>
          <div className="flex gap-2">
            <div className="w-4 h-4 bg-bauhaus-red" />
            <div className="w-4 h-4 bg-bauhaus-gold" />
            <div className="w-4 h-4 rounded-full bg-cream/20" />
          </div>
        </div>
      </footer>
    </div>
  )
}

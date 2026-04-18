import { motion } from 'framer-motion'

interface ShapeProps {
  className?: string
}

export function FloatingCircle({ className = '' }: ShapeProps) {
  return (
    <motion.div
      className={`absolute rounded-full ${className}`}
      animate={{
        y: [0, -20, 0],
        rotate: [0, 180, 360],
      }}
      transition={{
        duration: 20,
        repeat: Infinity,
        ease: 'linear',
      }}
    />
  )
}

export function FloatingTriangle({ className = '' }: ShapeProps) {
  return (
    <motion.div
      className={`absolute ${className}`}
      style={{
        width: 0,
        height: 0,
        borderLeft: '40px solid transparent',
        borderRight: '40px solid transparent',
        borderBottom: '70px solid currentColor',
      }}
      animate={{
        y: [0, 15, 0],
        rotate: [0, -10, 10, 0],
      }}
      transition={{
        duration: 15,
        repeat: Infinity,
        ease: 'easeInOut',
      }}
    />
  )
}

export function FloatingSquare({ className = '' }: ShapeProps) {
  return (
    <motion.div
      className={`absolute ${className}`}
      animate={{
        y: [0, -15, 0],
        rotate: [0, 90, 0],
      }}
      transition={{
        duration: 18,
        repeat: Infinity,
        ease: 'easeInOut',
      }}
    />
  )
}

export function GridPattern() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-[0.03]">
      <svg width="100%" height="100%">
        <defs>
          <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
            <path d="M 60 0 L 0 0 0 60" fill="none" stroke="#0D1B2A" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>
    </div>
  )
}

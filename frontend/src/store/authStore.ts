import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AuthUser } from '../types'

interface AuthState {
  user: AuthUser | null
  login: (user: AuthUser) => void
  logout: () => void
  updateFaceEnrolled: (enrolled: boolean) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      login: (user) => set({ user }),
      logout: () => set({ user: null }),
      updateFaceEnrolled: (enrolled) =>
        set((state) => ({
          user: state.user ? { ...state.user, face_enrolled: enrolled } : null,
        })),
    }),
    { name: 'auth' },
  ),
)

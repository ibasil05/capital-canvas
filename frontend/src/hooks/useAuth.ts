import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { getAuthToken, removeAuthToken } from '@/lib/auth';

interface User {
  id: string;
  email: string;
  email_confirmed_at?: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  logout: () => void;
}

// Create a Zustand store with persistence
export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: !!getAuthToken(),
      
      // Set the current user
      setUser: (user: User | null) => 
        set({ 
          user, 
          isAuthenticated: !!user 
        }),
      
      // Logout the user
      logout: () => {
        removeAuthToken();
        set({ 
          user: null, 
          isAuthenticated: false 
        });
      },
    }),
    {
      name: 'capital-canvas-auth', // Name for localStorage
    }
  )
);

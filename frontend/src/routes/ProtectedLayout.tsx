import { Navigate, Outlet } from 'react-router-dom';
import { useEffect, useRef } from 'react';
import { isAuthenticated, removeAuthToken } from '@/lib/auth';
import { Header } from '@/components/aceternity/header';
import { Footer } from '@/components/aceternity/footer';
import { useAuth } from '@/hooks/useAuth';
import { authAPI } from '@/lib/api';

export default function ProtectedLayout() {
  const { user, setUser } = useAuth();
  const wasAuthAttempted = useRef(false);

  // Check if user is authenticated
  if (!isAuthenticated()) {
    return <Navigate to="/signin" replace />;
  }

  // Fetch user data if not already loaded
  useEffect(() => {
    let isMounted = true;
    if (!user && isAuthenticated()) { // Only fetch if no user AND token exists
      const fetchUser = async () => {
        try {
          const userData = await authAPI.getCurrentUser();
          if (isMounted) {
            setUser(userData);
          }
        } catch (error) {
          console.error('Failed to fetch user data (ProtectedLayout):', error);
          if (isMounted) {
            removeAuthToken(); // Remove invalid token
            setUser(null);     // Clear user in Zustand store
            // Navigation will be handled by the top-level !isAuthenticated() check on next render cycle
          }
        }
      };
      wasAuthAttempted.current = true;
      fetchUser();
    }
    return () => { isMounted = false; };
  }, [user, setUser]);

  // Final check after attempts to load user
  if (!isAuthenticated()) {
    return <Navigate to="/signin" replace />;
  }

  return (
    <div className="min-h-screen flex flex-col bg-white dark:bg-neutral-950">
      <Header />
      <main className="flex-1 w-full container mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <Outlet />
      </main>
      <Footer variant="app" />
    </div>
  );
}

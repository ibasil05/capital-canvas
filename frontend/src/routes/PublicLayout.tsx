import { Navigate, Outlet } from 'react-router-dom';
import { isAuthenticated } from '@/lib/auth';

export default function PublicLayout() {
  // If user is already authenticated, redirect to the app home page
  if (isAuthenticated()) {
    return <Navigate to="/app/home" replace />;
  }

  // For all public pages, just render the Outlet without additional layout
  // This allows each page to define its own layout
  return <Outlet />;
}

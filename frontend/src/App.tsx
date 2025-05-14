import { createBrowserRouter } from 'react-router-dom'

// Layouts
import PublicLayout from './routes/PublicLayout'
import ProtectedLayout from './routes/ProtectedLayout'

// Public Pages
import Landing from './pages/Landing'
import SignIn from './pages/SignIn'
import SignUp from './pages/SignUp'

// Protected Pages
import Home from './pages/Home'
import Model from './pages/Model'
import Settings from './pages/Settings'

// Define the router configuration
export const router = createBrowserRouter([
  // Public routes
  {
    path: '/',
    element: <PublicLayout />,
    children: [
      { index: true, element: <Landing /> },
      { path: 'signin', element: <SignIn /> },
      { path: 'signup', element: <SignUp /> },
    ],
  },
  // Protected routes
  {
    path: '/app',
    element: <ProtectedLayout />,
    children: [
      { path: 'home', element: <Home /> },
      { path: 'model/:symbol', element: <Model /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
])

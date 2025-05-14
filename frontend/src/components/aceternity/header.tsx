import { useState } from 'react';
import { motion, useScroll, useMotionValueEvent } from 'framer-motion';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Button } from './button';
import { useAuth } from '@/hooks/useAuth';

type HeaderProps = {
  className?: string;
};

export const Header = ({ className }: HeaderProps) => {
  const [isScrolled, setIsScrolled] = useState(false);
  const { scrollY } = useScroll();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  useMotionValueEvent(scrollY, "change", (latest) => {
    setIsScrolled(latest > 50);
  });

  const publicPaths = ['/', '/signin', '/signup']; 
  const isPublicRoute = publicPaths.includes(location.pathname);

  return (
    <motion.header 
      className={cn(
        "sticky top-0 z-40 transition-all duration-300",
        isScrolled ? 
          "border-b border-neutral-200 dark:border-neutral-800 py-3 bg-white/80 dark:bg-neutral-900/80 backdrop-blur-md" : 
          "py-4 bg-transparent",
        className
      )}
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="max-w-6xl mx-auto px-6 flex justify-between items-center">
        <motion.div 
          className="flex items-center gap-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <svg className="h-6 w-6 text-blue-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="20" x2="12" y2="10" />
            <line x1="18" y1="20" x2="18" y2="4" />
            <line x1="6" y1="20" x2="6" y2="16" />
          </svg>
          <h1 className="text-xl font-medium dark:text-white">CapitalCanvas</h1>
        </motion.div>
        
        <motion.div 
          className="flex items-center gap-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          {user && !isPublicRoute ? (
            <>
              <Link to="/app/settings">
                <Button 
                  size="sm" 
                  className="bg-black text-white hover:bg-neutral-800 dark:bg-white dark:text-black dark:hover:bg-neutral-200"
                >
                  Settings
                </Button>
              </Link>
              <Button 
                size="sm" 
                className="bg-black text-white hover:bg-neutral-800 dark:bg-white dark:text-black dark:hover:bg-neutral-200"
                onClick={async () => {
                  await logout();
                  navigate('/signin');
                }}
              >
                Sign Out
              </Button>
            </>
          ) : (
            <>
              <Link to="/signin" className="text-sm text-neutral-600 hover:text-neutral-900 dark:text-neutral-300 dark:hover:text-white transition-colors">
                Log in
              </Link>
              <Link to="/signup">
                <Button variant="default" size="sm">
                  Get Started
                </Button>
              </Link>
            </>
          )}
        </motion.div>
      </div>
    </motion.header>
  );
};

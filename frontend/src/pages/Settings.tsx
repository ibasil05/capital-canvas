import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/aceternity/button';

const Settings: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleSignOut = async () => {
    await logout();
    navigate('/signin');
  };

  // Extract username part from email
  const username = user?.email ? user.email.split('@')[0] : 'User';

  return (
    <>
      {/* This div is the main content wrapper for the Settings page, inside ProtectedLayout's <main> */}
      {/* It arranges the title and card vertically and grows to fill space */}
      <div className="flex flex-col flex-grow">
        <div className="space-y-2 text-center mb-12">
          <h1 className="text-4xl font-bold tracking-tight text-neutral-900 dark:text-neutral-50">
            Settings
          </h1>
          <p className="text-lg text-neutral-500 dark:text-neutral-400">
            Manage your account settings and preferences.
          </p>
        </div>
        
        <div className="bg-white dark:bg-neutral-900 shadow-xl ring-1 ring-neutral-900/5 sm:rounded-xl p-8 flex-grow flex flex-col justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-neutral-800 dark:text-neutral-100 mb-2">Account</h2>
            {user && (
              <div className="mb-6">
                <p className="text-md text-neutral-700 dark:text-neutral-300">
                  Logged in as: <span className="font-medium">{username}</span>
                </p>
                <p className="text-sm text-neutral-500 dark:text-neutral-400">
                  ({user.email})
                </p>
              </div>
            )}
            {/* Other settings options can be added here */} 
            <p className="text-neutral-600 dark:text-neutral-300">
              More account management options will be available here soon.
            </p>
          </div>
          
          <div className="mt-auto pt-6">
            <Button 
              variant="destructive" 
              className="w-full sm:w-auto"
              onClick={handleSignOut}
            >
              Sign Out
            </Button>
          </div>
        </div>
      </div>
    </>
  );
};

export default Settings;

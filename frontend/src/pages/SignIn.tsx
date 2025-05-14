import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { motion } from 'framer-motion';
import { useAuth } from '@/hooks/useAuth';
import { Header } from '@/components/aceternity/header';
import { Button } from '@/components/aceternity/button';
import { Input } from '@/components/aceternity/input';
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/aceternity/form';
import { Footer } from '@/components/aceternity/footer';

// Define the form schema with Zod
const formSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

type FormValues = z.infer<typeof formSchema>;

export default function SignIn() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { setUser } = useAuth();
  
  // Initialize react-hook-form
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  });
  
  // Form submission handler
  const onSubmit = async (data: FormValues, event?: React.BaseSyntheticEvent) => {
    event?.preventDefault(); // Explicitly prevent default browser action
    setIsLoading(true);
    setError(null);
    
    try {
      console.log('Making direct fetch call to signin endpoint');

      const response = await fetch('http://127.0.0.1:9000/auth/signin', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
        // credentials: 'include', // Consider if this is needed
      });

      console.log('Raw signin response object:', response);
      console.log('Signin response status:', response.status);

      if (!response.ok) {
        let errorData;
        try {
          errorData = await response.json();
          console.error('Signin error response JSON:', errorData);
        } catch (e) {
          const errorText = await response.text();
          console.error('Signin error response Text:', errorText);
          errorData = { detail: errorText || 'Failed to sign in due to network or server error.' };
        }
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const responseData = await response.json(); // This should be AuthResponse type
      console.log('Signin successful, response data:', responseData);

      // Assuming responseData contains the user and token as per AuthResponse type
      if (responseData.access_token) {
        localStorage.setItem('auth_token', responseData.access_token);
      }
      // Assuming responseData.user contains the user object
      setUser(responseData.user);
      navigate('/app/home');
    } catch (err: any) {
      console.error('Sign in error in onSubmit:', err);
      setError(err.message || 'Failed to sign in. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <div className="min-h-screen flex flex-col bg-white dark:bg-neutral-950">
      {/* Header */}
      <Header />
      
      <main className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-white dark:bg-neutral-900 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-800 p-8">
          <div className="space-y-6">
            {/* Form Header */}
            <div className="space-y-2 text-center">
              <motion.h1 
                className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-neutral-50"
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.1 }}
              >
                Sign In
              </motion.h1>
              <motion.p 
                className="text-sm text-neutral-500 dark:text-neutral-400"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5, delay: 0.2 }}
              >
                Enter your email and password to access your account
              </motion.p>
            </div>
            
            {error && (
              <motion.div 
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-6"
              >
                {error}
              </motion.div>
            )}
            
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input 
                        placeholder="name@example.com" 
                        type="email" 
                        disabled={isLoading} 
                        {...field} 
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Password</FormLabel>
                    <FormControl>
                      <Input 
                        placeholder="••••••••" 
                        type="password" 
                        disabled={isLoading} 
                        {...field} 
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <Button 
                type="submit" 
                className="w-full bg-black text-white hover:bg-neutral-800 dark:bg-white dark:text-black dark:hover:bg-neutral-200" 
                disabled={isLoading}
                isLoading={isLoading}
              >
                {isLoading ? 'Signing in...' : 'Sign In'}
              </Button>
            </form>
            
            <div className="mt-6 text-center">
              <Link to="/reset-password" className="text-sm text-black hover:text-neutral-700 dark:text-white dark:hover:text-neutral-300 transition-colors">
                Forgot your password?
              </Link>
            </div>
            
            <div className="mt-6 pt-6 border-t border-neutral-200 text-center">
              <p className="text-sm text-neutral-600">
                Don't have an account?{' '}
                <Link to="/signup" className="text-black hover:text-neutral-700 dark:text-white dark:hover:text-neutral-300 transition-colors font-medium">
                  Sign up
                </Link>
              </p>
            </div>
          </div>
        </div>
      </main>
      
      <Footer />
    </div>
  );
}

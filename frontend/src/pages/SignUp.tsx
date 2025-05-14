import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { motion } from 'framer-motion';
// Import Aceternity UI components
import { Header } from '@/components/aceternity/header';
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/aceternity/form';
import { Input } from '@/components/aceternity/input';
import { Footer } from '@/components/aceternity/footer';
import { Button } from '@/components/aceternity/button';

// Define the form schema with Zod
const formSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirm_password: z.string().min(8, 'Password must be at least 8 characters'),
}).refine((data) => data.password === data.confirm_password, {
  message: "Passwords don't match",
  path: ["confirm_password"],
});

type FormValues = z.infer<typeof formSchema>;

export default function SignUp() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const navigate = useNavigate();
  
  // Initialize react-hook-form
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: '',
      password: '',
      confirm_password: '',
    },
  });
  
  // Form submission handler
  const onSubmit = async (data: FormValues, event?: React.BaseSyntheticEvent) => { 
    event?.preventDefault();
    console.log('onSubmit called with data:', data);
    setIsLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      console.log('Making direct fetch call to backend');
      
      // Direct fetch call (ensure backend is running and accessible)
      const response = await fetch('http://127.0.0.1:9000/auth/signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
        // credentials: 'include', // Consider if this is needed based on your backend CORS and auth setup
      });
      
      console.log('Raw response object:', response);
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        let errorData;
        try {
          errorData = await response.json();
          console.error('Error response JSON:', errorData);
        } catch (e) {
          // If response is not JSON, use text
          const errorText = await response.text();
          console.error('Error response Text:', errorText);
          errorData = { detail: errorText || 'Failed to create account due to network or server error.' };
        }
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      
      const responseData = await response.json();
      console.log('Signup successful, response data:', responseData);
      
      setSuccess('Account created successfully! Please check your email to verify your account.');
      form.reset(); // Clear the form
      
      // Redirect to sign in page after a delay
      setTimeout(() => {
        navigate('/signin');
      }, 3000);
    } catch (err: any) {
      console.error('Sign up error in onSubmit:', err);
      setError(err.message || 'Failed to create account. Please try again.');
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
                Create an account
              </motion.h1>
              <motion.p 
                className="text-sm text-neutral-500 dark:text-neutral-400"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5, delay: 0.2 }}
              >
                Enter your email and create a password to get started
              </motion.p>
            </div>
            
            {/* Alerts */}
            {error && (
              <motion.div 
                className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ type: 'spring', stiffness: 500, damping: 30 }}
              >
                {error}
              </motion.div>
            )}
            
            {success && (
              <motion.div 
                className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-md"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ type: 'spring', stiffness: 500, damping: 30 }}
              >
                {success}
              </motion.div>
            )}
            
            {/* Form */}
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
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
              
              <FormField
                control={form.control}
                name="confirm_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Confirm Password</FormLabel>
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
                {isLoading ? 'Creating account...' : 'Create Account'}
              </Button>
            </form>
            

            
            {/* Footer */}
            <div className="text-center mt-6">
              <p className="text-sm text-neutral-500 dark:text-neutral-400">
                Already have an account?{' '}
                <Link 
                  to="/signin" 
                  className="font-medium text-black hover:text-neutral-700 dark:text-white dark:hover:text-neutral-300 transition-colors"
                >
                  Sign in
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

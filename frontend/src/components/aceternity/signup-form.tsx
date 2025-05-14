import React from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { cn } from '@/lib/utils';

// Import Aceternity UI components
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from './form';
import { Input } from './input';
import { Button } from './button';

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

interface SignUpFormProps {
  onSubmit: (data: FormValues) => Promise<void>;
  isLoading?: boolean;
  error?: string | null;
  success?: string | null;
  className?: string;
}

export const SignUpForm: React.FC<SignUpFormProps> = ({
  onSubmit,
  isLoading = false,
  error = null,
  success = null,
  className,
}) => {
  // Initialize react-hook-form
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: '',
      password: '',
      confirm_password: '',
    },
  });
  
  const handleSubmit = async (data: FormValues) => {
    await onSubmit(data);
  };
  
  return (
    <div className={cn("space-y-6", className)}>
      {/* Alerts */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}
      
      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-md">
          {success}
        </div>
      )}
      
      {/* Form */}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
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
      </Form>
    </div>
  );
};

export default SignUpForm;

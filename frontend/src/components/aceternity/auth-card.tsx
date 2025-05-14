import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

type AuthCardProps = {
  children: React.ReactNode;
  className?: string;
};

export const AuthCard = ({ children, className }: AuthCardProps) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, type: 'spring', stiffness: 100 }}
      className={cn(
        'w-full max-w-md overflow-hidden rounded-2xl bg-white/80 backdrop-blur-sm shadow-xl border border-neutral-200/50 dark:bg-neutral-900/80 dark:border-neutral-800/50',
        className
      )}
    >
      <div className="absolute inset-0 -z-10 bg-gradient-to-br from-blue-50 via-white to-indigo-50 opacity-50 dark:from-blue-950/30 dark:via-neutral-950 dark:to-indigo-950/30" />
      <div className="relative z-10 p-8">
        {children}
      </div>
    </motion.div>
  );
};

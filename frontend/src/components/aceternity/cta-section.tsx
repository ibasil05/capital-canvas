import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

type CTASectionProps = {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  className?: string;
};

export const CTASection = ({
  title,
  subtitle,
  children,
  className,
}: CTASectionProps) => {
  return (
    <section className={cn("py-16 px-6 relative overflow-hidden", className)}>
      {/* Subtle background animation */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-white to-neutral-50 dark:from-neutral-900 dark:to-neutral-950" />
        
        <motion.div
          className="absolute -bottom-24 -right-24 w-96 h-96 rounded-full bg-blue-50/50 dark:bg-blue-900/10 blur-3xl"
          animate={{
            scale: [1, 1.1, 1],
            opacity: [0.3, 0.4, 0.3],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            repeatType: 'reverse',
          }}
        />
        
        <motion.div
          className="absolute -top-24 -left-24 w-96 h-96 rounded-full bg-purple-50/50 dark:bg-purple-900/10 blur-3xl"
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.2, 0.3, 0.2],
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            repeatType: 'reverse',
          }}
        />
      </div>
      
      <div className="max-w-4xl mx-auto text-center relative z-10">
        <motion.h2 
          className="text-3xl font-semibold mb-6 dark:text-white"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          viewport={{ once: true }}
        >
          {title}
        </motion.h2>
        
        <motion.p 
          className="text-lg text-neutral-600 dark:text-neutral-300 mb-8"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          viewport={{ once: true }}
        >
          {subtitle}
        </motion.p>
        
        <motion.div 
          className="flex flex-col sm:flex-row gap-4 justify-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          viewport={{ once: true }}
        >
          {children}
        </motion.div>
      </div>
    </section>
  );
};

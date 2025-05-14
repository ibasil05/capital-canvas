import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { TypewriterEffect } from './typewriter-effect';

type HeroSectionProps = {
  title: string;
  subtitle: string;
  children?: React.ReactNode;
  className?: string;
};

export const HeroSection = ({
  title,
  subtitle,
  children,
  className,
}: HeroSectionProps) => {
  return (
    <section className={cn("relative overflow-hidden py-24 px-6", className)}>
      {/* Animated background elements */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-b from-white via-neutral-50/70 to-white dark:from-neutral-950 dark:via-neutral-900/70 dark:to-neutral-950" />
        
        {/* Animated shapes */}
        <motion.div
          className="absolute top-1/4 left-1/4 w-64 h-64 rounded-full bg-blue-100/30 dark:bg-blue-900/10 blur-3xl"
          animate={{
            x: [0, 30, 0],
            y: [0, -30, 0],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            repeatType: 'reverse',
          }}
        />
        <motion.div
          className="absolute bottom-1/4 right-1/4 w-72 h-72 rounded-full bg-purple-100/30 dark:bg-purple-900/10 blur-3xl"
          animate={{
            x: [0, -20, 0],
            y: [0, 20, 0],
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            repeatType: 'reverse',
          }}
        />
      </div>
      
      <div className="max-w-5xl mx-auto text-center relative z-10">
        <motion.h1 
          className="text-5xl font-bold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-r from-neutral-900 to-neutral-600 dark:from-white dark:to-neutral-300"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <TypewriterEffect 
            text={title} 
            typingSpeed={60}
            delayBeforeStart={300}
            showCursor={true}
            cursorClassName="text-neutral-900 dark:text-white"
          />
        </motion.h1>
        
        <motion.p 
          className="text-xl text-neutral-600 dark:text-neutral-300 mb-10 max-w-3xl mx-auto"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          {subtitle}
        </motion.p>
        
        <motion.div 
          className="mb-16"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          {children}
        </motion.div>
      </div>
    </section>
  );
};

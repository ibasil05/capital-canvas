import React from 'react';
import { motion } from 'framer-motion';

type AnimatedBackgroundProps = {
  children: React.ReactNode;
  className?: string;
};

export const AnimatedBackground = ({ children, className = '' }: AnimatedBackgroundProps) => {
  return (
    <div className={`relative overflow-hidden ${className}`}>
      <div className="absolute inset-0 z-0">
        {/* Animated gradient background */}
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-50 via-white to-blue-50 dark:from-neutral-900 dark:via-neutral-950 dark:to-neutral-900" />
        
        {/* Animated circles */}
        <div className="absolute top-0 left-0 right-0 bottom-0 opacity-30">
          {Array.from({ length: 20 }).map((_, i) => {
            const size = Math.random() * 400 + 100;
            const xPos = Math.random() * 100;
            const yPos = Math.random() * 100;
            const duration = Math.random() * 20 + 10;
            
            return (
              <motion.div
                key={i}
                className="absolute rounded-full bg-gradient-to-br from-blue-400/20 to-indigo-400/20 dark:from-blue-600/10 dark:to-indigo-600/10"
                style={{
                  width: size,
                  height: size,
                  left: `${xPos}%`,
                  top: `${yPos}%`,
                  transform: 'translate(-50%, -50%)',
                }}
                animate={{
                  x: [0, Math.random() * 100 - 50],
                  y: [0, Math.random() * 100 - 50],
                }}
                transition={{
                  duration,
                  repeat: Infinity,
                  repeatType: 'reverse',
                  ease: 'easeInOut',
                }}
              />
            );
          })}
        </div>
        
        {/* Subtle grid pattern */}
        <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center [mask-image:linear-gradient(180deg,white,rgba(255,255,255,0))] opacity-10" />
      </div>
      
      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
};

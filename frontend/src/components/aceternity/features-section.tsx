import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

type FeaturesSectionProps = {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  className?: string;
};

export const FeaturesSection = ({
  title,
  subtitle,
  children,
  className,
}: FeaturesSectionProps) => {
  return (
    <section className={cn("py-20 px-6 relative overflow-hidden", className)}>
      {/* Subtle background pattern */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-neutral-50 dark:bg-neutral-900" />
        <div className="absolute inset-0 opacity-[0.03] dark:opacity-[0.05] bg-[radial-gradient(#3b82f6_1px,transparent_1px)] [background-size:20px_20px]" />
      </div>
      
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <motion.h2 
            className="text-3xl font-bold mb-4 dark:text-white"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            viewport={{ once: true }}
          >
            {title}
          </motion.h2>
          
          <motion.p 
            className="text-lg text-neutral-600 dark:text-neutral-300 max-w-2xl mx-auto"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            viewport={{ once: true }}
          >
            {subtitle}
          </motion.p>
        </div>
        
        <div className="grid md:grid-cols-3 gap-8">
          {children}
        </div>
      </div>
    </section>
  );
};

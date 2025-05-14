import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

type FeatureCardProps = {
  icon: React.ReactNode;
  title: string;
  description: string;
  iconBgColor?: string;
  iconColor?: string;
  className?: string;
};

export const FeatureCard = ({
  icon,
  title,
  description,
  iconBgColor = 'bg-blue-50 dark:bg-blue-900/20',
  iconColor = 'text-blue-600 dark:text-blue-400',
  className,
}: FeatureCardProps) => {
  return (
    <motion.div 
      className={cn(
        "bg-white dark:bg-neutral-900 p-6 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm hover:shadow-md transition-all",
        className
      )}
      whileHover={{ y: -5, transition: { duration: 0.2 } }}
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
    >
      <div className={cn("w-12 h-12 rounded-lg flex items-center justify-center mb-4", iconBgColor)}>
        <div className={cn("w-6 h-6", iconColor)}>
          {icon}
        </div>
      </div>
      <h3 className="text-xl font-semibold mb-3 dark:text-white">{title}</h3>
      <p className="text-neutral-600 dark:text-neutral-400">
        {description}
      </p>
    </motion.div>
  );
};

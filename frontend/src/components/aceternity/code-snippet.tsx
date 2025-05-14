import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

type CodeSnippetProps = {
  title: string;
  className?: string;
  children: React.ReactNode;
};

export const CodeSnippet = ({ title, className, children }: CodeSnippetProps) => {
  return (
    <motion.div 
      className={cn(
        "max-w-4xl mx-auto bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-lg shadow-lg overflow-hidden",
        className
      )}
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      viewport={{ once: true, margin: "-100px" }}
    >
      <div className="flex items-center border-b border-neutral-100 dark:border-neutral-800 p-4">
        <div className="flex space-x-2 mr-4">
          <motion.div 
            className="w-3 h-3 rounded-full bg-black dark:bg-white"
            initial={{ scale: 0 }}
            whileInView={{ scale: 1 }}
            transition={{ duration: 0.3, delay: 0.2 }}
            viewport={{ once: true }}
          />
          <motion.div 
            className="w-3 h-3 rounded-full bg-neutral-600 dark:bg-neutral-400"
            initial={{ scale: 0 }}
            whileInView={{ scale: 1 }}
            transition={{ duration: 0.3, delay: 0.3 }}
            viewport={{ once: true }}
          />
          <motion.div 
            className="w-3 h-3 rounded-full bg-neutral-300 dark:bg-neutral-700"
            initial={{ scale: 0 }}
            whileInView={{ scale: 1 }}
            transition={{ duration: 0.3, delay: 0.4 }}
            viewport={{ once: true }}
          />
        </div>
        <div className="flex-1 text-center text-sm text-neutral-500 dark:text-neutral-400 font-medium">{title}</div>
      </div>
      <div className="p-6 bg-white dark:bg-neutral-900 text-left overflow-x-auto">
        {children}
      </div>
    </motion.div>
  );
};

type CodeSnippetItemProps = {
  icon: React.ReactNode;
  title: string;
  items: Array<{ label: string; value: string; color?: string; }>;
  iconColor?: string;
  borderColor?: string;
  className?: string;
};

export const CodeSnippetItem = ({
  icon,
  title,
  items,
  iconColor = 'text-black dark:text-white',
  borderColor = 'border-neutral-300 dark:border-neutral-700',
  className,
}: CodeSnippetItemProps) => {
  return (
    <motion.div 
      className={cn("mb-4 last:mb-0", className)}
      initial={{ opacity: 0, x: -20 }}
      whileInView={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5 }}
      viewport={{ once: true }}
    >
      <div className="flex items-center mb-3">
        <div className={cn("w-4 h-4 mr-2", iconColor)}>
          {icon}
        </div>
        <span className={cn("font-medium", iconColor)}>{title}</span>
      </div>
      <motion.div 
        className={cn("pl-6 border-l-2 mb-4", borderColor)}
        initial={{ height: 0, opacity: 0 }}
        whileInView={{ height: "auto", opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.2 }}
        viewport={{ once: true }}
      >
        {items.map((item, index) => (
          <div key={index} className="text-neutral-800 dark:text-neutral-200 mb-1 last:mb-0">
            {item.label}: <span className={item.color || 'text-neutral-600 dark:text-neutral-400'}>{item.value}</span>
          </div>
        ))}
      </motion.div>
    </motion.div>
  );
};

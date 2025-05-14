import { type ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

type FooterProps = {
  className?: string;
  variant?: 'app' | 'landing';
};

type FooterColumnProps = {
  title: string;
  links: Array<{ label: string; href: string; }>;
  className?: string;
};

const FooterColumn = ({ title, links, className }: FooterColumnProps) => {
  return (
    <div className={className}>
      <h4 className="text-sm font-semibold uppercase tracking-wider mb-4 text-white">{title}</h4>
      <ul className="space-y-2">
        {links.map((link, index) => (
          <motion.li 
            key={index}
            initial={{ opacity: 0, x: -10 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 0.1 * index }}
            viewport={{ once: true }}
          >
            <a 
              href={link.href} 
              className="text-neutral-400 hover:text-white transition-colors inline-flex items-center gap-1 group"
            >
              <span>{link.label}</span>
              <svg 
                className="w-3 h-3 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" 
                viewBox="0 0 24 24" 
                fill="none" 
                stroke="currentColor" 
                strokeWidth="2" 
                strokeLinecap="round" 
                strokeLinejoin="round"
              >
                <polyline points="9 18 15 12 9 6"></polyline>
              </svg>
            </a>
          </motion.li>
        ))}
      </ul>
    </div>
  );
};

export const Footer = ({ className, variant = 'landing' }: FooterProps) => {
  const currentYear = new Date().getFullYear();
  
  const baseClasses = "py-6 px-6";
  const landingClasses = "bg-neutral-800 text-white";
  const appClasses = "bg-white dark:bg-neutral-950 text-neutral-600 dark:text-neutral-400";

  return (
    <footer className={cn(
      baseClasses,
      variant === 'app' ? appClasses : landingClasses,
      className
    )}>
      <div className="max-w-6xl mx-auto">
        <div className={cn(
          "text-center",
          variant === 'app' ? "text-neutral-500 dark:text-neutral-400" : "text-neutral-400"
        )}>
          {variant === 'landing' && (
            <p> {currentYear} CapitalCanvas</p>
          )}
          {/* For 'app' variant, this will be empty, effectively removing the copyright text */}
        </div>
      </div>
    </footer>
  );
};

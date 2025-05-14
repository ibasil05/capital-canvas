import { cn } from '@/lib/utils';
import React from 'react';

type CardProps = {
  className?: string;
  children: React.ReactNode;
};

export const Card = ({
  className,
  children,
}: CardProps) => {
  return (
    <div
      className={cn(
        'rounded-2xl border border-neutral-200 bg-white p-6 shadow-xl dark:border-neutral-800 dark:bg-neutral-950',
        className
      )}
    >
      {children}
    </div>
  );
};

export const CardHeader = ({
  className,
  children,
}: CardProps) => {
  return (
    <div
      className={cn(
        'mb-4 space-y-2',
        className
      )}
    >
      {children}
    </div>
  );
};

export const CardTitle = ({
  className,
  children,
}: CardProps) => {
  return (
    <h3
      className={cn(
        'text-2xl font-bold tracking-tight text-neutral-900 dark:text-neutral-50',
        className
      )}
    >
      {children}
    </h3>
  );
};

export const CardDescription = ({
  className,
  children,
}: CardProps) => {
  return (
    <p
      className={cn(
        'text-sm text-neutral-500 dark:text-neutral-400',
        className
      )}
    >
      {children}
    </p>
  );
};

export const CardContent = ({
  className,
  children,
}: CardProps) => {
  return (
    <div
      className={cn(
        'space-y-4',
        className
      )}
    >
      {children}
    </div>
  );
};

export const CardFooter = ({
  className,
  children,
}: CardProps) => {
  return (
    <div
      className={cn(
        'mt-6 flex items-center',
        className
      )}
    >
      {children}
    </div>
  );
};

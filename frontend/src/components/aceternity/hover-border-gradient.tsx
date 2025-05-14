import React from "react";
import { cn } from "@/lib/utils";

export const HoverBorderGradient = ({
  children,
  containerClassName,
  className,
  as: Component = "button",
  duration = 400,
  ...props
}: {
  children?: React.ReactNode;
  containerClassName?: string;
  className?: string;
  as?: React.ElementType;
  duration?: number;
  [key: string]: any;
}) => {
  return (
    <div className={cn("relative p-[1px] overflow-hidden rounded-lg", containerClassName)}>
      <div
        className="absolute inset-0 z-[1] bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
        aria-hidden="true"
      />
      <Component
        className={cn(
          "relative z-10 bg-white dark:bg-gray-950 rounded-lg group overflow-hidden",
          className
        )}
        {...props}
      >
        <div className="relative z-10">{children}</div>
        <div
          className="absolute inset-0 z-0 bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 opacity-0 group-hover:opacity-100 transition-opacity"
          style={{ transitionDuration: `${duration}ms` }}
          aria-hidden="true"
        />
      </Component>
    </div>
  );
};

export const HoverBorderGradientButton = ({
  children,
  className,
  containerClassName,
  duration = 400,
  ...props
}: {
  children?: React.ReactNode;
  className?: string;
  containerClassName?: string;
  duration?: number;
  [key: string]: any;
}) => {
  return (
    <HoverBorderGradient
      as="button"
      className={cn(
        "px-4 py-2 font-medium text-sm text-black dark:text-white transition-colors",
        className
      )}
      containerClassName={containerClassName}
      duration={duration}
      {...props}
    >
      {children}
    </HoverBorderGradient>
  );
};

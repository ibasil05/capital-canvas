import React from "react";
import { cn } from "@/lib/utils";

export const BackgroundGradient = ({
  children,
  className,
  containerClassName,
  as: Component = "div",
}: {
  children?: React.ReactNode;
  className?: string;
  containerClassName?: string;
  as?: React.ElementType;
}) => {
  return (
    <Component
      className={cn(
        "relative p-[4px] group/bg-gradient overflow-hidden rounded-lg",
        containerClassName
      )}
    >
      <div
        className="absolute inset-0 rounded-lg z-[1] bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 opacity-0 group-hover/bg-gradient:opacity-100 transition duration-500"
        aria-hidden="true"
      />
      <div
        className="absolute inset-0 rounded-lg z-[1] bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 opacity-0 blur-xl group-hover/bg-gradient:opacity-40 transition duration-500"
        aria-hidden="true"
      />
      <div
        className={cn(
          "relative z-10 bg-white dark:bg-gray-950 rounded-lg h-full",
          className
        )}
      >
        {children}
      </div>
    </Component>
  );
};

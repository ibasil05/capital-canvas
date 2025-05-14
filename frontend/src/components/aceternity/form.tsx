import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';
import * as React from 'react';
import { useFormContext, Controller } from 'react-hook-form';
import type { FieldPath, FieldValues } from 'react-hook-form';

const Form = React.forwardRef<
  HTMLFormElement,
  React.FormHTMLAttributes<HTMLFormElement>
>(({ className, ...props }, ref) => {
  return (
    <form
      ref={ref}
      className={cn('space-y-6', className)}
      {...props}
    />
  );
});
Form.displayName = 'Form';

type FormItemContextValue = {
  id: string;
};

const FormItemContext = React.createContext<FormItemContextValue>(
  {} as FormItemContextValue
);

const FormItem = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => {
  const id = React.useId();
  // Extract any Framer Motion specific props to avoid type conflicts
  const { initial, animate, transition, ...restProps } = props as any;

  return (
    <FormItemContext.Provider value={{ id }}>
      <motion.div
        ref={ref}
        className={cn('space-y-2', className)}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        {...restProps}
      />
    </FormItemContext.Provider>
  );
});
FormItem.displayName = 'FormItem';

const FormLabel = React.forwardRef<
  HTMLLabelElement,
  React.LabelHTMLAttributes<HTMLLabelElement>
>(({ className, ...props }, ref) => {
  const { id } = React.useContext(FormItemContext);

  return (
    <label
      ref={ref}
      htmlFor={id}
      className={cn(
        'text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 text-neutral-900 dark:text-neutral-50',
        className
      )}
      {...props}
    />
  );
});
FormLabel.displayName = 'FormLabel';

const FormControl = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ ...props }, ref) => {
  const { id } = React.useContext(FormItemContext);

  return (
    <div
      ref={ref}
      id={id}
      {...props}
    />
  );
});
FormControl.displayName = 'FormControl';

const FormDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => {
  return (
    <p
      ref={ref}
      className={cn('text-sm text-neutral-500 dark:text-neutral-400', className)}
      {...props}
    />
  );
});
FormDescription.displayName = 'FormDescription';

const FormMessage = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, children, ...props }, ref) => {
  return (
    <p
      ref={ref}
      className={cn('text-sm font-medium text-red-500 dark:text-red-400', className)}
      {...props}
    >
      {children}
    </p>
  );
});
FormMessage.displayName = 'FormMessage';

interface FormFieldContextValue<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
> {
  name: TName;
}

const FormFieldContext = React.createContext<FormFieldContextValue>(
  {} as FormFieldContextValue
);

const FormField = <
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
>({
  ...props
}: {
  control?: any;
  name: TName;
  render: (props: { field: any; fieldState?: any }) => React.ReactNode;
}) => {
  const { control, name, render } = props;
  const formContext = useFormContext();
  const methods = control || formContext.control;

  return (
    <FormFieldContext.Provider value={{ name }}>
      <Controller
        control={methods}
        name={name}
        render={({ field, fieldState }) => {
          // Use Fragment to wrap the rendered content, ensuring it's always a valid JSX element
          return <>{render({ field, fieldState })}</>;
        }}
      />
    </FormFieldContext.Provider>
  );
};

export {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
};

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/** 胶囊按钮（暗房霓虹）：default = 紫青渐变主按钮（深色文字）、
 *  secondary = 玻璃填充次按钮、outline = 描边胶囊、ghost = 无底、
 *  destructive = 红色危险态。 */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-pill text-sm font-medium transition duration-150 ease-out-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background active:scale-[0.97] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100 cursor-pointer",
  {
    variants: {
      variant: {
        default: "bg-grad-accent text-accent-fg font-bold hover:brightness-110",
        secondary: "bg-fill-2 border border-strong text-secondary hover:bg-fill-3 hover:text-primary",
        outline: "border border-strong bg-transparent text-secondary hover:bg-fill-2 hover:text-primary",
        ghost: "text-secondary hover:bg-fill-2 hover:text-primary",
        destructive: "bg-explicit-soft border border-explicit-edge text-explicit hover:bg-explicit hover:text-accent-fg",
      },
      size: {
        default: "h-10 px-5",
        sm: "h-[34px] px-3.5 text-xs",
        lg: "h-[42px] px-6",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  ),
);
Button.displayName = "Button";

export { Button, buttonVariants };

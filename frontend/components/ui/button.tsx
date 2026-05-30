import { Slot } from "@radix-ui/react-slot";
import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-body font-medium transition-colors focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-accent/20 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "border border-accent bg-accent text-accent-foreground hover:bg-accent-hover hover:border-accent-hover",
        secondary: "border border-border-default bg-transparent text-primary hover:border-border-strong",
        outline: "border border-border-default bg-transparent text-secondary hover:bg-elevated hover:text-primary",
        ghost: "border border-transparent bg-transparent text-secondary hover:bg-elevated hover:text-primary",
        quiet: "border border-border-default bg-transparent text-secondary hover:bg-elevated hover:text-primary",
        danger: "border border-border-default bg-transparent text-danger hover:bg-elevated",
        up: "border border-up bg-up/10 text-up hover:bg-up/20",
        down: "border border-down bg-down/10 text-down hover:bg-down/20",
      },
      size: {
        default: "h-[34px] px-4 py-0",
        sm: "h-8 px-3",
        lg: "h-11 px-6",
        icon: "h-[34px] w-[34px]",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };

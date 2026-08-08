<script lang="ts" module>
  import { tv, type VariantProps } from "tailwind-variants";

  export const buttonVariants = tv({
    base: "inline-flex shrink-0 items-center justify-center gap-2 rounded-md text-sm font-medium whitespace-nowrap transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        destructive: "bg-destructive text-white hover:bg-destructive/90",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 px-6",
        icon: "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  });

  export type ButtonVariant = VariantProps<typeof buttonVariants>["variant"];
  export type ButtonSize = VariantProps<typeof buttonVariants>["size"];
</script>

<script lang="ts">
  import type { HTMLButtonAttributes } from "svelte/elements";
  import type { Snippet } from "svelte";
  import { cn } from "$lib/utils.js";

  let {
    class: className,
    variant = "default",
    size = "default",
    type = "button",
    children,
    ...rest
  }: HTMLButtonAttributes & {
    variant?: ButtonVariant;
    size?: ButtonSize;
    children?: Snippet;
  } = $props();
</script>

<button {type} class={cn(buttonVariants({ variant, size }), className)} {...rest}>
  {@render children?.()}
</button>

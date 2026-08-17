import { Tooltip as TooltipPrimitive } from "bits-ui";
import Root from "./tooltip.svelte";
import Content from "./tooltip-content.svelte";

const Provider = TooltipPrimitive.Provider;
const Trigger = TooltipPrimitive.Trigger;
const Portal = TooltipPrimitive.Portal;

export {
  Root,
  Content,
  Provider,
  Trigger,
  Portal,
  Root as Tooltip,
  Content as TooltipContent,
  Provider as TooltipProvider,
  Trigger as TooltipTrigger,
};

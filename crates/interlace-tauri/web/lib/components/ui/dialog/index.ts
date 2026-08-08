import { Dialog as DialogPrimitive } from "bits-ui";
import Root from "./dialog.svelte";
import Content from "./dialog-content.svelte";
import Header from "./dialog-header.svelte";
import Footer from "./dialog-footer.svelte";
import Title from "./dialog-title.svelte";
import Description from "./dialog-description.svelte";

const Trigger = DialogPrimitive.Trigger;
const Close = DialogPrimitive.Close;
const Portal = DialogPrimitive.Portal;
const Overlay = DialogPrimitive.Overlay;

export {
  Root,
  Content,
  Header,
  Footer,
  Title,
  Description,
  Trigger,
  Close,
  Portal,
  Overlay,
};

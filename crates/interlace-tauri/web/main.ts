import { mount } from "svelte";
import App from "./App.svelte";
import "./app.css";

const el = document.getElementById("app")!;
el.replaceChildren();
mount(App, { target: el });

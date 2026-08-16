import { createApp } from "vue";
import "maplibre-gl/dist/maplibre-gl.css";
import "./index.css";
import App from "./App.vue";
import vuetify from "./plugins/vuetify";

createApp(App).use(vuetify).mount("#root");

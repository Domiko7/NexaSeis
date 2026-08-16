import "@mdi/font/css/materialdesignicons.css";
import "vuetify/styles";
import { createVuetify } from "vuetify";

export default createVuetify({
  theme: {
    defaultTheme: "nexaDark",
    themes: {
      nexaDark: {
        dark: true,
        colors: {
          background: "#101C2B",
          surface: "#172438",
          "surface-bright": "#20324A",
          primary: "#9ECAFF",
          secondary: "#BDC7D8",
          accent: "#9ECAFF",
          info: "#4FC3F7",
          success: "#4DB6AC",
          warning: "#FFB74D",
          error: "#EF5350",
        },
      },
    },
  },
  defaults: {
    VBtn: { rounded: "lg" },
    VCard: { rounded: "xl" },
  },
});

import js from "@eslint/js"
import tseslint from "typescript-eslint"
import globals from "globals";

export default tseslint.config(
  { ignores: ["dist", "node_modules"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.ts"],
    languageOptions: {
      globals: globals.browser,
    },
    rules: {
      "prefer-arrow-callback": "error",
    },
  },
);

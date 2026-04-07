import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  // Specify explicit React version to avoid eslint-plugin-react calling the
  // removed context.getFilename() API when using version: 'detect' with ESLint 10.
  {
    settings: {
      react: {
        version: "19",
      },
    },
  },
]);

export default eslintConfig;

// Flat config — STK-TS-03. typescript-eslint type-checked rules are the reason this
// pair (and not biome) is the house default; prettier config last to disable conflicts.
import js from "@eslint/js";
import prettier from "eslint-config-prettier";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist/", "coverage/", "node_modules/"] },
  js.configs.recommended,
  ...tseslint.configs.recommendedTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    // Config files themselves don't need type-aware linting.
    files: ["*.js", "*.config.ts"],
    ...tseslint.configs.disableTypeChecked,
  },
  prettier,
);

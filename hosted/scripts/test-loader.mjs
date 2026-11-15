import { registerHooks } from "node:module";
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { resolve } from "node:path";
import ts from "typescript";
registerHooks({
  resolve(specifier, context, nextResolve) {
    const base = specifier.startsWith("@/") ? pathToFileURL(resolve(specifier.slice(2))).href : specifier;
    try { return nextResolve(base, context); }
    catch (e) {
      if ((base.startsWith(".") || base.startsWith("file:")) && context.parentURL) {
        for (const extension of [".ts", ".tsx"]) { const url = new URL(base + extension, context.parentURL); if (existsSync(url)) return { url: url.href, shortCircuit: true }; }
      }
      throw e;
    }
  },
  load(url, context, nextLoad) {
    if (/\.tsx?$/.test(url)) {
      const source = readFileSync(fileURLToPath(url), "utf8");
      return { format: "module", source: ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext, jsx: ts.JsxEmit.ReactJSX } }).outputText, shortCircuit: true };
    }
    return nextLoad(url, context);
  },
});

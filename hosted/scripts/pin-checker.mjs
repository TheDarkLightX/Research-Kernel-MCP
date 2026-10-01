import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
const sha = createHash("sha256").update(readFileSync(new URL("../lib/core/checker.ts", import.meta.url))).digest("hex");
writeFileSync(new URL("../lib/checker-pin.ts", import.meta.url), '// Generated from exact checker source bytes.\nexport const CHECKER_SOURCE_SHA256 = "' + sha + '";\n');
const files = ["checker", "model", "validation", "transition"];
const core = createHash("sha256");
for (const file of files) { core.update(file + "\0"); core.update(readFileSync(new URL("../lib/core/" + file + ".ts", import.meta.url))); }
writeFileSync(new URL("../lib/kernel-pin.ts", import.meta.url), '// Generated from the exact functional core source bytes.\nexport const KERNEL_SOURCE_SHA256 = "' + core.digest("hex") + '";\n');

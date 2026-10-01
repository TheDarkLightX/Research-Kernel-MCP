// Pure, bounded integer interpreter. No eval, processes, network or filesystem.
export const CHECKER_ID = "integer-grid/v1";
export type Recipe = {
  checker: typeof CHECKER_ID;
  variables: Record<string, { min: number; max: number }>;
  left: string; right: string;
};
export type CheckResult = {
  outcome: "passed" | "counterexample" | "inconclusive";
  cases: number; totalCases: number; scope: string;
  counterexample: null | { inputs: Record<string, number>; left: string; right: string };
  error: string | null; outputsHash: string;
};
type Expr = { n: bigint } | { v: string } | { op: string; a: Expr; b: Expr };

function parse(source: string, variables: string[]): Expr {
  if (source.length > 400) throw new Error("Expression is limited to 400 characters.");
  const tokens = source.match(/[a-zA-Z_][a-zA-Z_0-9]*|[0-9]+|[()+*%^-]/g) ?? [];
  if (tokens.join("") !== source.replace(/\s/g, "")) throw new Error("Use integer arithmetic: +, -, *, %, ^ and parentheses.");
  if (tokens.length > 120) throw new Error("Expression is too complex.");
  let index = 0;
  const precedence: Record<string, number> = { "+": 1, "-": 1, "*": 2, "%": 2, "^": 3 };
  function expression(min = 0, depth = 0): Expr {
    if (depth > 30) throw new Error("Expression nesting is too deep.");
    const t = tokens[index++];
    let a: Expr;
    if (t === "-") a = { op: "-", a: { n: 0n }, b: expression(3, depth + 1) };
    else if (t === "(") {
      a = expression(0, depth + 1);
      if (tokens[index++] !== ")") throw new Error("Missing closing parenthesis.");
    } else if (t && /^\d+$/.test(t) && t.length <= 12) a = { n: BigInt(t) };
    else if (variables.includes(t)) a = { v: t };
    else throw new Error("Unknown variable or invalid integer.");
    while (index < tokens.length && (precedence[tokens[index]] ?? -1) >= min) {
      const op = tokens[index++];
      a = { op, a, b: expression(precedence[op] + (op === "^" ? 0 : 1), depth + 1) };
    }
    return a;
  }
  const result = expression();
  if (index !== tokens.length) throw new Error("Unexpected expression token.");
  return result;
}
function evaluate(e: Expr, inputs: Record<string, number>): bigint {
  if ("n" in e) return e.n;
  if ("v" in e) return BigInt(inputs[e.v]);
  const a = evaluate(e.a, inputs), b = evaluate(e.b, inputs);
  let r: bigint;
  switch (e.op) {
    case "+": r = a + b; break;
    case "-": r = a - b; break;
    case "*": r = a * b; break;
    case "%": if (b === 0n) throw new Error("Modulo by zero."); r = a % b; break;
    case "^": if (b < 0n || b > 8n) throw new Error("Exponent must be in 0..8."); r = a ** b; break;
    default: throw new Error("Unsupported operator.");
  }
  if (r.toString(2).length > 256) throw new Error("Arithmetic exceeds the 256-bit bound.");
  return r;
}
export function checkRecipe(recipe: Recipe, hash: (value: string) => string): CheckResult {
  const names = Object.keys(recipe.variables).sort();
  const result: CheckResult = { outcome: "inconclusive", cases: 0, totalCases: 0, scope: "", counterexample: null, error: null, outputsHash: hash("rk-integer-grid-transcript/1") };
  try {
    if (recipe.checker !== CHECKER_ID || names.length < 1 || names.length > 3) throw new Error("Use integer-grid/v1 with 1–3 variables.");
    let count = 1;
    for (const name of names) {
      const domain = recipe.variables[name];
      if (!/^[a-zA-Z][a-zA-Z0-9_]{0,15}$/.test(name) || !Number.isSafeInteger(domain.min) || !Number.isSafeInteger(domain.max) || domain.min > domain.max || Math.abs(domain.min) > 1000000 || Math.abs(domain.max) > 1000000) throw new Error("Invalid variable name or finite integer domain.");
      count *= domain.max - domain.min + 1;
      if (count > 2048) throw new Error("At most 2,048 combinations per check.");
    }
    result.totalCases = count;
    result.scope = names.map(n => n + " ∈ [" + recipe.variables[n].min + ", " + recipe.variables[n].max + "] ∩ ℤ").join("; ");
    const left = parse(recipe.left, names), right = parse(recipe.right, names);
    const inputs: Record<string, number> = {};
    function visit(i: number): boolean {
      if (i < names.length) {
        const n = names[i], d = recipe.variables[n];
        for (let v = d.min; v <= d.max; v++) { inputs[n] = v; if (!visit(i + 1)) return false; }
        return true;
      }
      const a = evaluate(left, inputs), b = evaluate(right, inputs); result.cases++;
      result.outputsHash = hash(JSON.stringify(["rk-integer-grid-transcript/1", result.outputsHash, names.map(n => [n, inputs[n]]), a.toString(), b.toString()]));
      if (a !== b) { result.counterexample = { inputs: { ...inputs }, left: a.toString(), right: b.toString() }; return false; }
      return true;
    }
    result.outcome = visit(0) ? "passed" : "counterexample";
  } catch (e) { result.error = e instanceof Error ? e.message : "Check failed."; result.outcome = "inconclusive"; }
  return result;
}

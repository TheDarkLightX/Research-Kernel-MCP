import type { Actor, ClaimInput } from "../lib/core/model";
import type { Recipe } from "../lib/core/checker";
export const owner: Actor = { userId: "owner", email: "owner@example.test", name: "Owner" };
export const editor: Actor = { userId: "editor", email: "editor@example.test", name: "Editor" };
export const reader: Actor = { userId: "reader", email: "reader@example.test", name: "Reader" };
export const recipe: Recipe = { checker: "integer-grid/v1", variables: { x: { min: -5, max: 5 }, y: { min: -5, max: 5 } }, left: "(x+y)^2", right: "x^2+2*x*y+y^2" };
export const input: ClaimInput = { title: "Square of a sum", statement: "The identity holds on the finite integer grid.", kind: "bounded", assumptions: "Integer arithmetic", scope: "Integers x,y in -5..5", recipe, dependencies: [] };

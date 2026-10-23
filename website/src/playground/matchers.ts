import { RE2JS } from "re2js";
import type { Plan } from "./model.ts";

export type LabelPredicate = (labels: Record<string, string>) => boolean;

/** Compile once per query, without a growing global regex cache. */
export function compileMatchers(matchers: Plan["matchers"]): LabelPredicate {
  const filters = matchers.map(({ label, op, value }) => {
    let pattern: RE2JS | undefined;
    if (op === "=~" || op === "!~") {
      try {
        // Prometheus anchors the entire label and enables dot-newline matching.
        // RE2JS implements Go/RE2 syntax rather than JavaScript RegExp syntax.
        pattern = RE2JS.compile(value, RE2JS.DOTALL);
      } catch (error) {
        throw new Error(
          `Invalid regex for label ${JSON.stringify(label)}: ${error instanceof Error ? error.message : String(error)}`,
        );
      }
    }
    return (labels: Record<string, string>) => {
      const actual = Object.hasOwn(labels, label) ? labels[label] : "";
      const matches = pattern ? pattern.matches(actual) : actual === value;
      return op === "!=" || op === "!~" ? !matches : matches;
    };
  });
  return (labels) => filters.every((matches) => matches(labels));
}

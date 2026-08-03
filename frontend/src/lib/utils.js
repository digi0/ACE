import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Conditional class names, with conflicting Tailwind utilities resolved.
 *
 * clsx flattens the conditionals; twMerge then makes the LAST utility win when
 * two target the same property. Plain string concat doesn't — `"p-2" + " p-4"`
 * leaves both in the class list and the winner is decided by the order the
 * rules happen to sit in the stylesheet, not by the order you wrote them. That
 * is what breaks the usual component pattern of a base class overridden by a
 * `className` prop from the caller.
 *
 *   cn("p-2 text-dim", isActive && "text-body", className)
 *
 * tailwind-merge must stay on v3+: v2 predates Tailwind v4 and mis-parses its
 * class syntax, so conflicts silently stop merging.
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

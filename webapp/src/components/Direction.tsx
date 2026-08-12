import type { ReactNode } from "react";

/** Направление (рост/падение) без цвета — глиф + текст, см. .dir в global.css. */
export function Direction({ value, children }: { value: number; children: ReactNode }) {
  const cls = value > 0 ? "dir" : value < 0 ? "dir dir-down" : "dir dir-flat";
  return <span className={cls}>{children}</span>;
}

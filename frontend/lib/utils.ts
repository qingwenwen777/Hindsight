import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** 合并 Tailwind 类名（shadcn 标准工具）。 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

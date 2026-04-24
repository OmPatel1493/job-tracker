import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// cn() merges Tailwind classes safely — handles conditional classes and deduplication.
// e.g. cn("px-2 py-1", isActive && "bg-blue-500") → "px-2 py-1 bg-blue-500"
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

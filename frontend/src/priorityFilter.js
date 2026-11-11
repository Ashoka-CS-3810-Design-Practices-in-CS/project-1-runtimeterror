export const PRIORITY_FILTERS = ["All", "High", "Medium", "Low", "Not set"];

export function matchesFilter(priority, filter) {
  if (filter === "All") return true;
  if (filter === "Not set") return !priority;
  return priority === filter;
}
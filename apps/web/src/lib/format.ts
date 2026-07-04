export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function formatAnalyte(value: number | null | undefined, unit: string): string {
  if (value === null || value === undefined) return "—";
  return `${value} ${unit}`;
}

export function formatProtocol(protocol: string): string {
  return protocol
    .split("_")
    .map((word) => word[0]?.toUpperCase() + word.slice(1))
    .join(" ");
}

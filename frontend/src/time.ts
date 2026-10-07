const exactFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

const timeFormatter = new Intl.DateTimeFormat(undefined, {
  hour: "numeric",
  minute: "2-digit",
});

const weekdayFormatter = new Intl.DateTimeFormat(undefined, {
  weekday: "long",
  hour: "numeric",
  minute: "2-digit",
});

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

const dateWithYearFormatter = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

const centralTimestampFormatter = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/Chicago",
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
  second: "2-digit",
  hour12: true,
  timeZoneName: "short",
});

function startOfDay(value: Date): number {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate()).getTime();
}

/** A concise local-time label for a recent timestamp, with dates for older values. */
export function humanizeTimestamp(value: string, now = new Date()): string {
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) return "Unknown time";

  const elapsedMs = now.getTime() - timestamp.getTime();
  const elapsedMinutes = Math.round(Math.abs(elapsedMs) / 60_000);
  const suffix = elapsedMs >= 0 ? "ago" : "from now";

  if (elapsedMinutes < 1) return "just now";
  if (elapsedMinutes < 60) return `${elapsedMinutes} minute${elapsedMinutes === 1 ? "" : "s"} ${suffix}`;

  const elapsedHours = Math.round(elapsedMinutes / 60);
  if (elapsedHours < 24) return `${elapsedHours} hour${elapsedHours === 1 ? "" : "s"} ${suffix}`;

  const dayDifference = Math.round((startOfDay(now) - startOfDay(timestamp)) / 86_400_000);
  if (dayDifference === 0) return `Today at ${timeFormatter.format(timestamp)}`;
  if (dayDifference === 1) return `Yesterday at ${timeFormatter.format(timestamp)}`;
  if (dayDifference > 1 && dayDifference < 7) return weekdayFormatter.format(timestamp);
  return (timestamp.getFullYear() === now.getFullYear() ? dateFormatter : dateWithYearFormatter).format(timestamp);
}

export function exactTimestamp(value: string): string {
  const timestamp = new Date(value);
  return Number.isNaN(timestamp.getTime()) ? value : exactFormatter.format(timestamp);
}

/** A precise Central-time timestamp for dashboard refresh metadata. */
export function centralTimestamp(value: string): string {
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) return value;

  const parts = Object.fromEntries(
    centralTimestampFormatter
      .formatToParts(timestamp)
      .filter((part) => part.type !== "literal")
      .map((part) => [part.type, part.value]),
  );
  return `${parts.month} ${parts.day}, ${parts.year} ${parts.hour}:${parts.minute}:${parts.second}${parts.dayPeriod} ${parts.timeZoneName}`;
}

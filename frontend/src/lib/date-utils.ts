/**
 * Parse an ISO-8601 datetime string as UTC.
 *
 * The backend stores all timestamps in UTC.  When the serialised string has no
 * explicit timezone indicator (no trailing `Z` or `±HH:MM` offset), JavaScript's
 * `Date` constructor treats it as *local* time.  For clients in UTC+N this
 * shifts every timestamp N hours into the past, causing "Xh ago" relative
 * labels and `toLocaleString()` absolute dates to be wrong.
 *
 * This helper appends `Z` to any timezone-naive ISO string so it is always
 * interpreted as UTC.  Strings that already carry timezone info are passed
 * through unchanged.
 */
export function parseUTC(iso: string): Date {
  return new Date(/Z|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : iso + 'Z');
}

/**
 * Format an ISO-8601 UTC timestamp as a human-readable relative time string
 * (e.g. "3m ago", "2h ago", "1d ago").  Returns "Never" for falsy input.
 */
export function formatRelative(iso?: string | null): string {
  if (!iso) return 'Never';
  const diff = Date.now() - parseUTC(iso).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

/**
 * Format an ISO-8601 UTC timestamp as a locale-aware short date + medium time
 * string, e.g. "28.03.26, 22:19:44".
 */
export function formatDate(iso: string): string {
  return parseUTC(iso).toLocaleString(undefined, {
    dateStyle: 'short',
    timeStyle: 'medium',
  });
}

/**
 * Format a duration in seconds as a human-readable string,
 * e.g. "3.1s" or "2m 5s".  Returns "—" for null/undefined input.
 */
export function formatDuration(seconds?: number | null): string {
  if (seconds == null) return '—';
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const totalSecs = Math.floor(seconds);
  return `${Math.floor(totalSecs / 60)}m ${totalSecs % 60}s`;
}

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

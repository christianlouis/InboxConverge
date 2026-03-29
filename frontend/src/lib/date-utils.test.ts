import { parseUTC, formatRelative, formatDate, formatDuration } from './date-utils';

describe('parseUTC', () => {
  it('should parse ISO string with Z suffix as UTC', () => {
    const date = parseUTC('2024-01-15T10:30:00Z');
    expect(date.toISOString()).toBe('2024-01-15T10:30:00.000Z');
  });

  it('should parse ISO string with positive timezone offset', () => {
    const date = parseUTC('2024-01-15T12:30:00+02:00');
    expect(date.toISOString()).toBe('2024-01-15T10:30:00.000Z');
  });

  it('should parse ISO string with negative timezone offset', () => {
    const date = parseUTC('2024-01-15T05:30:00-05:00');
    expect(date.toISOString()).toBe('2024-01-15T10:30:00.000Z');
  });

  it('should append Z to timezone-naive ISO string', () => {
    const date = parseUTC('2024-01-15T10:30:00');
    expect(date.toISOString()).toBe('2024-01-15T10:30:00.000Z');
  });

  it('should handle ISO string with milliseconds and Z', () => {
    const date = parseUTC('2024-01-15T10:30:00.123Z');
    expect(date.toISOString()).toBe('2024-01-15T10:30:00.123Z');
  });

  it('should handle ISO string with compact offset (no colon)', () => {
    const date = parseUTC('2024-01-15T12:30:00+0200');
    expect(date.toISOString()).toBe('2024-01-15T10:30:00.000Z');
  });
});

describe('formatRelative', () => {
  it('should return "Never" for undefined input', () => {
    expect(formatRelative(undefined)).toBe('Never');
  });

  it('should return "Never" for null input', () => {
    expect(formatRelative(null)).toBe('Never');
  });

  it('should return "Never" for empty string', () => {
    expect(formatRelative('')).toBe('Never');
  });

  it('should return "Just now" for timestamps less than 1 minute ago', () => {
    const now = new Date().toISOString();
    expect(formatRelative(now)).toBe('Just now');
  });

  it('should return minutes ago for timestamps less than 1 hour ago', () => {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    expect(formatRelative(fiveMinutesAgo)).toBe('5m ago');
  });

  it('should return hours ago for timestamps less than 1 day ago', () => {
    const threeHoursAgo = new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString();
    expect(formatRelative(threeHoursAgo)).toBe('3h ago');
  });

  it('should return days ago for timestamps 1+ days ago', () => {
    const twoDaysAgo = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString();
    expect(formatRelative(twoDaysAgo)).toBe('2d ago');
  });

  it('should return "1m ago" for exactly 1 minute ago', () => {
    const oneMinuteAgo = new Date(Date.now() - 60 * 1000).toISOString();
    expect(formatRelative(oneMinuteAgo)).toBe('1m ago');
  });

  it('should return "59m ago" for 59 minutes ago', () => {
    const fiftyNineMinutesAgo = new Date(Date.now() - 59 * 60 * 1000).toISOString();
    expect(formatRelative(fiftyNineMinutesAgo)).toBe('59m ago');
  });

  it('should return "1h ago" for exactly 60 minutes ago', () => {
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString();
    expect(formatRelative(oneHourAgo)).toBe('1h ago');
  });

  it('should return "23h ago" for 23 hours ago', () => {
    const twentyThreeHoursAgo = new Date(Date.now() - 23 * 60 * 60 * 1000).toISOString();
    expect(formatRelative(twentyThreeHoursAgo)).toBe('23h ago');
  });

  it('should return "1d ago" for exactly 24 hours ago', () => {
    const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    expect(formatRelative(oneDayAgo)).toBe('1d ago');
  });

  it('should handle timezone-naive timestamps correctly', () => {
    // Create a timestamp without Z suffix
    const now = new Date();
    const naive = now.toISOString().replace('Z', '');
    // parseUTC will append Z, so it should be interpreted as UTC
    const result = formatRelative(naive);
    expect(result).toBe('Just now');
  });
});

describe('formatDate', () => {
  it('should return a locale-formatted date string', () => {
    const result = formatDate('2024-01-15T10:30:00Z');
    // The exact format depends on locale, but it should contain key parts
    expect(typeof result).toBe('string');
    expect(result.length).toBeGreaterThan(0);
  });

  it('should handle timezone-naive ISO strings', () => {
    const result = formatDate('2024-01-15T10:30:00');
    expect(typeof result).toBe('string');
    expect(result.length).toBeGreaterThan(0);
  });
});

describe('formatDuration', () => {
  it('should return em dash for null', () => {
    expect(formatDuration(null)).toBe('—');
  });

  it('should return em dash for undefined', () => {
    expect(formatDuration(undefined)).toBe('—');
  });

  it('should format 0 seconds', () => {
    expect(formatDuration(0)).toBe('0.0s');
  });

  it('should format sub-minute durations with one decimal', () => {
    expect(formatDuration(3.14)).toBe('3.1s');
  });

  it('should format exactly 59.9 seconds', () => {
    expect(formatDuration(59.9)).toBe('59.9s');
  });

  it('should format exactly 60 seconds as minutes', () => {
    expect(formatDuration(60)).toBe('1m 0s');
  });

  it('should format 125 seconds as 2m 5s', () => {
    expect(formatDuration(125)).toBe('2m 5s');
  });

  it('should format large durations', () => {
    expect(formatDuration(3661)).toBe('61m 1s');
  });

  it('should format fractional seconds above 60', () => {
    expect(formatDuration(65.7)).toBe('1m 5s');
  });
});

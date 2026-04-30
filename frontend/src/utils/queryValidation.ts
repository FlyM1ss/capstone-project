// Keep patterns in sync with backend/app/services/validation.py. The backend
// is the real security barrier — this mirror exists so the UI can warn
// instantly without a round-trip.

const INJECTION_PATTERNS: RegExp[] = [
  /ignore\s+(all\s+)?previous\s+instructions/i,
  /system\s*prompt/i,
  /you\s+are\s+now/i,
  /<\s*script/i,
];

export const QUERY_BLOCKED_MESSAGE = 'This query was blocked for security reasons.';
export const QUERY_BLOCKED_CODE = 'query_blocked_pattern';

export function getQueryBlockReason(query: string): string | null {
  for (const pattern of INJECTION_PATTERNS) {
    if (pattern.test(query)) return QUERY_BLOCKED_MESSAGE;
  }
  return null;
}

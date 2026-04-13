const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function apiGet<T>(path: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(`${BASE_URL}${path}`);
    if (!res.ok) throw new Error(res.statusText);
    return res.json();
  } catch {
    console.warn(`[Fetch API] Unreachable: GET ${path} — using mock data`);
    return fallback;
  }
}

export async function apiPost<T>(
  path: string,
  body: unknown,
  fallback: T
): Promise<T> {
  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(res.statusText);
    return res.json();
  } catch {
    console.warn(`[Fetch API] Unreachable: POST ${path} — using mock data`);
    return fallback;
  }
}

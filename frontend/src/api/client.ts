export const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ApiErrorBody {
  detail?: string;
  error_code?: string;
  reason?: string;
  [key: string]: unknown;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body: ApiErrorBody | null = null,
  ) {
    super(message);
    this.name = 'ApiError';
  }

  get errorCode(): string | undefined {
    return this.body?.error_code;
  }

  get detail(): string | undefined {
    return this.body?.detail;
  }
}

async function parseErrorBody(res: Response): Promise<ApiErrorBody | null> {
  try {
    return (await res.json()) as ApiErrorBody;
  } catch {
    return null;
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    const body = await parseErrorBody(res);
    throw new ApiError(res.status, body?.detail ?? `GET ${path} failed: ${res.statusText}`, body);
  }
  return res.json();
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const errBody = await parseErrorBody(res);
    throw new ApiError(res.status, errBody?.detail ?? `POST ${path} failed: ${res.statusText}`, errBody);
  }
  return res.json();
}

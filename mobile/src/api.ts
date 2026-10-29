import * as SecureStore from 'expo-secure-store';

const API_BASE_URL = (process.env.EXPO_PUBLIC_API_BASE_URL || 'https://doccumind.duckdns.org').replace(/\/$/, '');
const TOKEN_KEY = 'documind.api-token';

export type DocumentItem = {
  id: number;
  file: string;
  display_name: string;
  collection: number | null;
  status: 'processing' | 'ready' | 'failed';
  processing_error: string;
  uploaded_at: string;
};

export type Citation = {
  document_title: string;
  page_number: number | null;
};

export type AnswerResult = {
  question: string;
  answer: string;
  sources: Citation[];
  answer_id: number;
};

export type AccountProfile = { id: number; username: string; email: string };

type ApiErrorBody = { detail?: string; error?: string; [key: string]: unknown };

async function parseResponse<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => ({} as ApiErrorBody));
  if (!response.ok) {
    const error = body as ApiErrorBody;
    const fieldError = Object.values(error).find((value) => Array.isArray(value) && typeof value[0] === 'string');
    throw new Error(error.detail || error.error || (fieldError as string[] | undefined)?.[0] || `Request failed (${response.status})`);
  }
  return body as T;
}

async function request<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Authorization', `Token ${token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  try {
    return await parseResponse<T>(response);
  } catch (cause) {
    (cause as Error & { status?: number }).status = response.status;
    throw cause;
  }
}

export async function readToken() {
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function saveToken(token: string) {
  await SecureStore.setItemAsync(TOKEN_KEY, token);
}

export async function clearToken() {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
}

export async function beginLogin(username: string, password: string) {
  const response = await fetch(`${API_BASE_URL}/api/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  return parseResponse<{ detail: string; username: string }>(response);
}

export async function verifyLogin(username: string, code: string) {
  const response = await fetch(`${API_BASE_URL}/api/auth/verify-otp/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, code }),
  });
  return parseResponse<{ token: string; username: string }>(response);
}

export async function listDocuments(token: string) {
  return request<DocumentItem[]>('/api/documents/', token);
}

export async function getMe(token: string) {
  return request<AccountProfile>('/api/auth/me/', token);
}

export async function uploadDocument(token: string, file: { uri: string; name: string; mimeType?: string | null }) {
  const form = new FormData();
  form.append('file', { uri: file.uri, name: file.name, type: file.mimeType || 'application/octet-stream' } as unknown as Blob);
  const response = await fetch(`${API_BASE_URL}/api/documents/`, {
    method: 'POST',
    headers: { Authorization: `Token ${token}` },
    body: form,
  });
  return parseResponse<DocumentItem>(response);
}

export async function askDocument(token: string, documentId: number, question: string) {
  return request<AnswerResult>(`/api/documents/${documentId}/ask/`, token, {
    method: 'POST',
    body: JSON.stringify({ question }),
  });
}

export async function logout(token: string) {
  await request<void>('/api/auth/logout/', token, { method: 'POST' });
  await clearToken();
}

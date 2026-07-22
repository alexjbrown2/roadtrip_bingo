import type { Difficulty, GameState, JoinResponse } from './types';

const BASE_URL = import.meta.env.VITE_API_URL ?? '/api';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; token?: string } = {},
): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (options.token) headers['X-Player-Token'] = options.token;

  const res = await fetch(`${BASE_URL}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (!res.ok) {
    const data = await res.json().catch(() => null);
    const firstFieldError = data && Object.values(data).find(Array.isArray)?.[0];
    const message =
      (data && (data.detail || firstFieldError || JSON.stringify(data))) ||
      `Request failed (${res.status})`;
    throw new ApiError(message, res.status);
  }

  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export function createGame(nickname: string) {
  return request<JoinResponse>('/games/', { method: 'POST', body: { nickname } });
}

export function joinGame(roomCode: string, nickname: string) {
  return request<JoinResponse>(`/games/${roomCode}/join/`, {
    method: 'POST',
    body: { nickname },
  });
}

export function startGame(roomCode: string, token: string) {
  return request<GameState>(`/games/${roomCode}/start/`, { method: 'POST', token });
}

export function replayGame(roomCode: string, token: string) {
  return request<GameState>(`/games/${roomCode}/replay/`, { method: 'POST', token });
}

export function resetToLobby(roomCode: string, token: string) {
  return request<GameState>(`/games/${roomCode}/reset/`, { method: 'POST', token });
}

export function undoWin(roomCode: string, token: string) {
  return request<GameState>(`/games/${roomCode}/undo-win/`, { method: 'POST', token });
}

export function updateSettings(roomCode: string, token: string, difficulty: Difficulty) {
  return request<GameState>(`/games/${roomCode}/settings/`, {
    method: 'PATCH',
    token,
    body: { difficulty },
  });
}

export function toggleCell(roomCode: string, token: string, cellId: number) {
  return request<GameState>(`/games/${roomCode}/cells/${cellId}/toggle/`, {
    method: 'POST',
    token,
  });
}

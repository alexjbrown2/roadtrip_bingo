import { useEffect, useRef, useState } from 'react';

const MAX_BACKOFF_MS = 10_000;

export function useGameSocket<T>(roomCode: string, token: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);

  const roomCodeRef = useRef(roomCode);
  const tokenRef = useRef(token);
  roomCodeRef.current = roomCode;
  tokenRef.current = token;

  useEffect(() => {
    if (!roomCode || !token) return;

    let cancelled = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let attempt = 0;

    const connect = () => {
      if (cancelled) return;

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const url = `${protocol}//${window.location.host}/ws/games/${roomCodeRef.current}/?token=${tokenRef.current}`;
      socket = new WebSocket(url);

      socket.onopen = () => {
        attempt = 0;
        setError(null);
      };

      socket.onmessage = (event) => {
        try {
          setData(JSON.parse(event.data) as T);
          setError(null);
        } catch {
          setError('Received a malformed update from the server.');
        }
      };

      socket.onerror = () => {
        setError('Connection lost, reconnecting…');
      };

      socket.onclose = () => {
        if (cancelled) return;
        setError('Connection lost, reconnecting…');
        const delay = Math.min(1000 * 2 ** attempt, MAX_BACKOFF_MS);
        attempt += 1;
        reconnectTimer = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [roomCode, token]);

  return { data, error };
}

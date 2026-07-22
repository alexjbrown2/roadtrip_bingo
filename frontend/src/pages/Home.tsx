import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createGame, joinGame, ApiError } from '../api/client';
import { saveSeat } from '../storage';

export default function Home() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<'create' | 'join'>('create');
  const [nickname, setNickname] = useState('');
  const [roomCode, setRoomCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nickname.trim()) {
      setError('Enter a nickname first.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result =
        mode === 'create'
          ? await createGame(nickname.trim())
          : await joinGame(roomCode.trim().toUpperCase(), nickname.trim());

      saveSeat({
        roomCode: result.room_code,
        playerToken: result.player_token,
        playerId: result.player_id,
        nickname: nickname.trim(),
      });
      navigate(`/game/${result.room_code}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-full flex items-center justify-center bg-sky-50 px-4 py-10">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-lg p-6">
        <h1 className="text-3xl font-bold text-center text-sky-700 mb-1">🚗 Road Trip Bingo</h1>
        <p className="text-center text-slate-500 mb-6">
          Spot it, mark it, shout bingo.
        </p>

        <div className="flex rounded-lg bg-slate-100 p-1 mb-5">
          <button
            type="button"
            className={`flex-1 py-2 rounded-md text-sm font-medium transition ${
              mode === 'create' ? 'bg-white shadow text-sky-700' : 'text-slate-500'
            }`}
            onClick={() => setMode('create')}
          >
            Create Game
          </button>
          <button
            type="button"
            className={`flex-1 py-2 rounded-md text-sm font-medium transition ${
              mode === 'join' ? 'bg-white shadow text-sky-700' : 'text-slate-500'
            }`}
            onClick={() => setMode('join')}
          >
            Join Game
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">
              Your nickname
            </label>
            <input
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-lg focus:outline-none focus:ring-2 focus:ring-sky-400"
              value={nickname}
              maxLength={50}
              onChange={(e) => setNickname(e.target.value)}
              placeholder="e.g. Alex"
              autoFocus
            />
          </div>

          {mode === 'join' && (
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">
                Room code
              </label>
              <input
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-lg tracking-widest uppercase focus:outline-none focus:ring-2 focus:ring-sky-400"
                value={roomCode}
                maxLength={6}
                onChange={(e) => setRoomCode(e.target.value.toUpperCase())}
                placeholder="ABC123"
              />
            </div>
          )}

          {error && <p className="text-red-600 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg bg-sky-600 text-white font-semibold py-3 text-lg hover:bg-sky-700 disabled:opacity-50 transition"
          >
            {busy ? 'Please wait…' : mode === 'create' ? 'Create Game' : 'Join Game'}
          </button>
        </form>
      </div>
    </div>
  );
}

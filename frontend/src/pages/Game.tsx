import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  startGame,
  toggleCell,
  updateSettings,
  replayGame,
  resetToLobby,
  undoWin,
  ApiError,
} from '../api/client';
import type { BoardCellInfo, Difficulty, GameState, PlayerInfo } from '../api/types';
import { loadSeat } from '../storage';
import { useGameSocket } from '../hooks/useGameSocket';

const DIFFICULTY_LABELS: Record<Difficulty, string> = {
  easy: 'Easy',
  medium: 'Medium',
  hard: 'Hard',
};

export default function Game() {
  const { roomCode = '' } = useParams();
  const navigate = useNavigate();
  const seat = loadSeat(roomCode);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [restartAction, setRestartAction] = useState<'replay' | 'lobby' | 'undo' | null>(
    null,
  );
  const [showSettings, setShowSettings] = useState(false);

  const { data: game, error } = useGameSocket<GameState>(
    seat?.roomCode ?? '',
    seat?.playerToken ?? '',
  );

  if (!seat) {
    return (
      <div className="min-h-full flex items-center justify-center px-4">
        <div className="text-center">
          <p className="text-slate-600 mb-4">
            You don't have a seat in game <strong>{roomCode}</strong> on this device.
          </p>
          <button
            className="rounded-lg bg-sky-600 text-white font-semibold px-4 py-2"
            onClick={() => navigate('/')}
          >
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  const me = game?.players.find((p) => p.id === seat.playerId);

  const handleStart = async () => {
    setPending(true);
    setActionError(null);
    try {
      await startGame(seat.roomCode, seat.playerToken);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Could not start game.');
    } finally {
      setPending(false);
    }
  };

  const handleToggle = async (cellId: number) => {
    setActionError(null);
    try {
      await toggleCell(seat.roomCode, seat.playerToken, cellId);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Could not mark cell.');
    }
  };

  const handleReplay = async () => {
    setRestartAction('replay');
    setActionError(null);
    try {
      await replayGame(seat.roomCode, seat.playerToken);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Could not start a new round.');
    } finally {
      setRestartAction(null);
    }
  };

  const handleBackToLobby = async () => {
    setRestartAction('lobby');
    setActionError(null);
    try {
      await resetToLobby(seat.roomCode, seat.playerToken);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Could not return to the lobby.');
    } finally {
      setRestartAction(null);
    }
  };

  const handleUndoWin = async () => {
    setRestartAction('undo');
    setActionError(null);
    try {
      await undoWin(seat.roomCode, seat.playerToken);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Could not undo the win.');
    } finally {
      setRestartAction(null);
    }
  };

  const handleSetDifficulty = async (difficulty: Difficulty) => {
    setActionError(null);
    try {
      await updateSettings(seat.roomCode, seat.playerToken, difficulty);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Could not update settings.');
    }
  };

  return (
    <div className="min-h-full bg-sky-50">
      <Header
        nickname={seat.nickname}
        game={game}
        canEditSettings={!!game && game.status === 'waiting' && !!me?.is_host}
        onToggleSettings={() => setShowSettings((v) => !v)}
      />

      <div className="max-w-md sm:max-w-lg md:max-w-2xl lg:max-w-3xl mx-auto px-4 py-6">
        {!game && !error && <p className="text-center text-slate-500">Loading game…</p>}
        {error && !game && <p className="text-center text-red-600">{error}</p>}

        {game && (
          <>
            {showSettings && game.status === 'waiting' && me?.is_host && (
              <SettingsPanel
                difficulty={game.difficulty}
                onChange={handleSetDifficulty}
              />
            )}

            {actionError && game.status !== 'completed' && (
              <p className="text-red-600 text-sm text-center my-3">{actionError}</p>
            )}

            {game.status === 'waiting' && (
              <div className="text-center mt-6">
                {me?.is_host ? (
                  <button
                    onClick={handleStart}
                    disabled={pending}
                    className="rounded-lg bg-sky-600 text-white font-semibold px-6 py-3 text-lg hover:bg-sky-700 disabled:opacity-50 transition"
                  >
                    {pending ? 'Starting…' : 'Start Game'}
                  </button>
                ) : (
                  <p className="text-slate-500">Waiting for the host to start the game…</p>
                )}
              </div>
            )}

            {game.board && (
              <BoardGrid
                board={game.board}
                size={game.board_size}
                disabled={game.status !== 'in_progress'}
                onToggle={handleToggle}
              />
            )}
          </>
        )}
      </div>

      {game && game.status === 'completed' && game.winner && (
        <WinOverlay
          winnerName={game.winner.nickname}
          isHost={!!me?.is_host}
          restartAction={restartAction}
          actionError={actionError}
          onReplay={handleReplay}
          onBackToLobby={handleBackToLobby}
          onUndo={handleUndoWin}
        />
      )}
    </div>
  );
}

function WinOverlay({
  winnerName,
  isHost,
  restartAction,
  actionError,
  onReplay,
  onBackToLobby,
  onUndo,
}: {
  winnerName: string;
  isHost: boolean;
  restartAction: 'replay' | 'lobby' | 'undo' | null;
  actionError: string | null;
  onReplay: () => void;
  onBackToLobby: () => void;
  onUndo: () => void;
}) {
  return (
    <div className="fixed inset-0 z-40 bg-black/60 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-6 max-w-sm w-full text-center">
        <p className="text-3xl mb-1">🎉</p>
        <p className="text-xl font-bold text-amber-700 mb-5">{winnerName} got BINGO!</p>

        {actionError && <p className="text-red-600 text-sm mb-3">{actionError}</p>}

        {isHost ? (
          <div className="space-y-3">
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={onReplay}
                disabled={restartAction !== null}
                className="rounded-lg bg-sky-600 text-white font-semibold px-4 py-2 hover:bg-sky-700 disabled:opacity-50 transition"
              >
                {restartAction === 'replay' ? 'Starting…' : 'Play Again'}
              </button>
              <button
                onClick={onBackToLobby}
                disabled={restartAction !== null}
                className="rounded-lg bg-white border border-sky-600 text-sky-700 font-semibold px-4 py-2 hover:bg-sky-50 disabled:opacity-50 transition"
              >
                {restartAction === 'lobby' ? 'Returning…' : 'Back to Lobby'}
              </button>
            </div>
            <button
              onClick={onUndo}
              disabled={restartAction !== null}
              className="text-sm text-slate-500 hover:text-slate-700 underline underline-offset-2 disabled:opacity-50 transition"
            >
              {restartAction === 'undo' ? 'Undoing…' : 'Undo last bingo & keep playing'}
            </button>
          </div>
        ) : (
          <p className="text-slate-500 text-sm">Waiting for the host to continue…</p>
        )}
      </div>
    </div>
  );
}

function Header({
  nickname,
  game,
  canEditSettings,
  onToggleSettings,
}: {
  nickname: string;
  game: GameState | null;
  canEditSettings: boolean;
  onToggleSettings: () => void;
}) {
  return (
    <header className="sticky top-0 z-10 bg-white shadow-sm">
      <div className="max-w-md sm:max-w-lg md:max-w-2xl lg:max-w-3xl mx-auto px-4 py-3 flex items-center justify-between gap-x-4 gap-y-2 flex-wrap">
        <div>
          <h1 className="text-lg sm:text-xl font-bold text-sky-700 leading-tight">
            🚗 Road Trip Bingo
          </h1>
          <p className="text-slate-500 text-xs sm:text-sm">
            Playing as <strong>{nickname}</strong>
          </p>
        </div>

        {game && (
          <div className="flex items-center gap-2 flex-wrap">
            <PlayersConnected players={game.players} />
            <span className="inline-flex items-center gap-1.5 bg-slate-50 rounded-full px-3 py-1 text-sm">
              <span className="text-slate-400 text-xs uppercase tracking-wide">Room</span>
              <span className="font-mono font-semibold tracking-widest text-sky-700">
                {game.room_code}
              </span>
            </span>
            <span className="inline-flex items-center gap-1.5 bg-slate-50 rounded-full px-3 py-1 text-sm text-slate-600">
              Difficulty:{' '}
              <span className="font-semibold">{DIFFICULTY_LABELS[game.difficulty]}</span>
              {canEditSettings && (
                <button
                  aria-label="Game settings"
                  onClick={onToggleSettings}
                  className="ml-1 text-slate-400 hover:text-sky-600 transition"
                >
                  <GearIcon />
                </button>
              )}
            </span>
          </div>
        )}
      </div>
    </header>
  );
}

function SettingsPanel({
  difficulty,
  onChange,
}: {
  difficulty: Difficulty;
  onChange: (difficulty: Difficulty) => void;
}) {
  const options: Difficulty[] = ['easy', 'medium', 'hard'];
  return (
    <div className="bg-white rounded-xl shadow p-4 mb-4">
      <p className="text-xs uppercase tracking-wide text-slate-400 mb-2">Game Settings</p>
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm text-slate-600">Difficulty</span>
        <div className="flex rounded-lg bg-slate-100 p-1">
          {options.map((option) => (
            <button
              key={option}
              onClick={() => onChange(option)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition ${
                difficulty === option ? 'bg-white shadow text-sky-700' : 'text-slate-500'
              }`}
            >
              {DIFFICULTY_LABELS[option]}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function GearIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-4 h-4"
    >
      <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
    </svg>
  );
}

function PlayersConnected({ players }: { players: PlayerInfo[] }) {
  return (
    <span className="relative group inline-flex items-center bg-slate-50 rounded-full px-3 py-1 text-sm text-slate-600 cursor-default">
      Players Connected <span className="font-semibold ml-1">({players.length})</span>

      <div className="invisible opacity-0 group-hover:visible group-hover:opacity-100 transition-opacity absolute right-0 top-full mt-2 min-w-[160px] bg-white rounded-lg shadow-lg border border-slate-200 py-1.5 z-20">
        <ul>
          {players.map((p) => (
            <li
              key={p.id}
              className="px-3 py-1 text-sm text-slate-700 whitespace-nowrap text-left"
            >
              {p.is_host && '👑 '}
              {p.nickname}
            </li>
          ))}
        </ul>
      </div>
    </span>
  );
}

function BoardGrid({
  board,
  size,
  disabled,
  onToggle,
}: {
  board: BoardCellInfo[];
  size: number;
  disabled: boolean;
  onToggle: (cellId: number) => void;
}) {
  const sorted = [...board].sort((a, b) => a.row - b.row || a.col - b.col);
  return (
    <div
      className="grid gap-1.5 sm:gap-2 md:gap-3 mx-auto"
      style={{
        gridTemplateColumns: `repeat(${size}, minmax(0, 1fr))`,
        maxWidth: `${size * 176}px`,
      }}
    >
      {sorted.map((cell) =>
        cell.is_free_space ? (
          <div
            key={cell.id}
            className="aspect-square rounded-lg border border-slate-300 bg-white opacity-90 flex items-center justify-center text-center p-1 sm:p-2"
          >
            <span className="text-[11px] sm:text-sm leading-tight font-medium">★ FREE</span>
          </div>
        ) : (
          <button
            key={cell.id}
            disabled={disabled}
            onClick={() => onToggle(cell.id)}
            className="aspect-square block [perspective:1000px]"
          >
            <div
              className={`relative w-full h-full transition-transform duration-200 ease-out [transform-style:preserve-3d] ${
                cell.marked ? '[transform:rotateY(180deg)]' : ''
              }`}
            >
              {/* Front: unmarked */}
              <div className="absolute inset-0 [backface-visibility:hidden] rounded-lg border border-slate-300 bg-white text-slate-700 flex flex-col items-center justify-center text-center gap-0.5 p-1 sm:p-2 active:bg-slate-100 transition">
                <img
                  src={`/assets/${cell.image}`}
                  alt=""
                  className="w-2/3 aspect-square object-contain"
                />
                <span className="text-[9px] sm:text-xs leading-tight font-medium">
                  {cell.item_text}
                </span>
              </div>

              {/* Back: marked */}
              <div className="absolute inset-0 [backface-visibility:hidden] [transform:rotateY(180deg)] rounded-lg border border-slate-300 bg-white overflow-hidden">
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-0.5 p-1 sm:p-2 blur-[2px]">
                  <img
                    src={`/assets/${cell.image}`}
                    alt=""
                    className="w-2/3 aspect-square object-contain"
                  />
                  <span className="text-[9px] sm:text-xs leading-tight font-medium text-slate-700">
                    {cell.item_text}
                  </span>
                </div>
                <div className="absolute inset-0 bg-black/30" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="bg-white/90 rounded-full p-1.5 sm:p-2 shadow-md">
                    <XMark />
                  </div>
                </div>
              </div>
            </div>
          </button>
        ),
      )}
    </div>
  );
}

function XMark() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="w-6 h-6 sm:w-9 sm:h-9 text-red-500"
      fill="none"
      stroke="currentColor"
      strokeWidth={3.5}
      strokeLinecap="round"
    >
      <line x1="5" y1="5" x2="19" y2="19" />
      <line x1="19" y1="5" x2="5" y2="19" />
    </svg>
  );
}

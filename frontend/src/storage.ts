export interface StoredSeat {
  roomCode: string;
  playerToken: string;
  playerId: number;
  nickname: string;
}

const key = (roomCode: string) => `roadtrip-bingo:${roomCode.toUpperCase()}`;

export function saveSeat(seat: StoredSeat) {
  localStorage.setItem(key(seat.roomCode), JSON.stringify(seat));
}

export function loadSeat(roomCode: string): StoredSeat | null {
  const raw = localStorage.getItem(key(roomCode));
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredSeat;
  } catch {
    return null;
  }
}

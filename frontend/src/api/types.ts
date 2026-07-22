export type GameStatus = 'waiting' | 'in_progress' | 'completed';
export type Difficulty = 'easy' | 'medium' | 'hard';

export interface PlayerInfo {
  id: number;
  nickname: string;
  is_host: boolean;
  has_bingo: boolean;
}

export interface BoardCellInfo {
  id: number;
  item_text: string;
  image: string;
  row: number;
  col: number;
  is_free_space: boolean;
  marked: boolean;
}

export interface GameState {
  room_code: string;
  status: GameStatus;
  board_size: number;
  difficulty: Difficulty;
  players: PlayerInfo[];
  winner: PlayerInfo | null;
  board: BoardCellInfo[] | null;
}

export interface JoinResponse {
  room_code: string;
  player_token: string;
  player_id: number;
}

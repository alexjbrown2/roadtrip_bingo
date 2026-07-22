import random

from django.utils import timezone

from .models import BoardCell, Item

DIFFICULTY_TIERS = {
    "easy": ["easy"],
    "medium": ["easy", "medium"],
    "hard": ["easy", "medium", "hard"],
}

BOARD_SIZES = [5, 4, 3]


def _cells_needed(board_size):
    has_free_space = board_size % 2 == 1
    total = board_size * board_size
    return total - 1 if has_free_space else total


def _choose_board_size(pool_count):
    for size in BOARD_SIZES:
        if pool_count >= _cells_needed(size):
            return size
    raise ValueError(
        f"Not enough items yet for this difficulty (need at least "
        f"{_cells_needed(BOARD_SIZES[-1])}, have {pool_count}). "
        "Add more items or pick an easier difficulty."
    )


def reset_for_new_round(game):
    """Clear a completed game's boards/winner so it can be started again."""
    BoardCell.objects.filter(player__game=game).delete()
    game.players.update(has_bingo=False)
    game.status = game.STATUS_WAITING
    game.winner = None
    game.winning_cell = None
    game.item_pool = []
    game.save(update_fields=["status", "winner", "winning_cell", "item_pool"])


def undo_win(game):
    """Revert the cell that completed the last bingo and resume play."""
    cell = game.winning_cell
    if cell is None:
        raise ValueError("There is no winning move to undo.")

    cell.marked = False
    cell.marked_at = None
    cell.save(update_fields=["marked", "marked_at"])

    if game.winner is not None:
        game.winner.has_bingo = False
        game.winner.save(update_fields=["has_bingo"])

    game.status = game.STATUS_IN_PROGRESS
    game.winner = None
    game.winning_cell = None
    game.save(update_fields=["status", "winner", "winning_cell"])


def start_game(game):
    """Pick the item pool and generate every player's board. Mutates and saves `game`."""
    tiers = DIFFICULTY_TIERS[game.difficulty]
    available = list(
        Item.objects.filter(difficulty__in=tiers).values_list("text", "image_filename")
    )

    board_size = _choose_board_size(len(available))
    has_free_space = board_size % 2 == 1
    items_needed = _cells_needed(board_size)

    chosen = random.sample(available, items_needed)
    game.item_pool = [{"text": text, "image": image} for text, image in chosen]
    game.board_size = board_size
    game.status = game.STATUS_IN_PROGRESS
    game.save(update_fields=["item_pool", "board_size", "status"])

    center = board_size // 2
    for player in game.players.all():
        shuffled = list(game.item_pool)
        random.shuffle(shuffled)
        cells = []
        item_iter = iter(shuffled)
        for row in range(board_size):
            for col in range(board_size):
                is_free = has_free_space and row == center and col == center
                item = None if is_free else next(item_iter)
                cells.append(
                    BoardCell(
                        player=player,
                        item_text="Free Space" if is_free else item["text"],
                        image_filename="" if is_free else item["image"],
                        row=row,
                        col=col,
                        is_free_space=is_free,
                        marked=is_free,
                        marked_at=timezone.now() if is_free else None,
                    )
                )
        BoardCell.objects.bulk_create(cells)


def check_bingo(player, cell):
    """Return True and record the win if `player`'s board now has a complete line.

    `cell` is the cell that was just toggled — recorded as the winning move so
    it can be undone later without guessing which cell caused the bingo.
    """
    size = player.game.board_size
    grid = [[False] * size for _ in range(size)]
    for c in player.cells.all():
        grid[c.row][c.col] = c.marked

    lines = [grid[r] for r in range(size)]
    lines += [[grid[r][c] for r in range(size)] for c in range(size)]
    lines.append([grid[i][i] for i in range(size)])
    lines.append([grid[i][size - 1 - i] for i in range(size)])

    won = any(all(line) for line in lines)
    if won and not player.has_bingo:
        player.has_bingo = True
        player.save(update_fields=["has_bingo"])
        game = player.game
        game.status = game.STATUS_COMPLETED
        game.winner = player
        game.winning_cell = cell
        game.save(update_fields=["status", "winner", "winning_cell"])
    return won

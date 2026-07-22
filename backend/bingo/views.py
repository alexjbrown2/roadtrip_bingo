from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import get_player_for_game
from .models import DIFFICULTY_CHOICES, BoardCell, Game, Player
from .realtime import broadcast_game_update
from .serializers import GameStateSerializer
from .services import check_bingo, reset_for_new_round, start_game, undo_win


class CreateGameView(APIView):
    def post(self, request):
        nickname = (request.data.get("nickname") or "").strip()
        if not nickname:
            raise ValidationError({"nickname": "This field is required."})

        game = Game.objects.create()
        player = Player.objects.create(game=game, nickname=nickname, is_host=True)
        return Response(
            {
                "room_code": game.room_code,
                "player_token": str(player.token),
                "player_id": player.id,
            },
            status=201,
        )


class JoinGameView(APIView):
    def post(self, request, room_code):
        game = get_object_or_404(Game, room_code=room_code.upper())
        if game.status != Game.STATUS_WAITING:
            raise ValidationError("This game has already started.")

        nickname = (request.data.get("nickname") or "").strip()
        if not nickname:
            raise ValidationError({"nickname": "This field is required."})

        player = Player.objects.create(game=game, nickname=nickname)
        broadcast_game_update(game)
        return Response(
            {
                "room_code": game.room_code,
                "player_token": str(player.token),
                "player_id": player.id,
            },
            status=201,
        )


class GameStateView(APIView):
    def get(self, request, room_code):
        game = get_object_or_404(Game, room_code=room_code.upper())
        player = get_player_for_game(request, game)
        serializer = GameStateSerializer(game, context={"player": player})
        return Response(serializer.data)


class StartGameView(APIView):
    def post(self, request, room_code):
        game = get_object_or_404(Game, room_code=room_code.upper())
        player = get_player_for_game(request, game)
        if not player.is_host:
            raise PermissionDenied("Only the host can start the game.")
        if game.status != Game.STATUS_WAITING:
            raise ValidationError("This game has already started.")
        if game.players.count() < 1:
            raise ValidationError("Need at least one player to start.")

        try:
            start_game(game)
        except ValueError as exc:
            raise ValidationError(str(exc))
        broadcast_game_update(game)
        serializer = GameStateSerializer(game, context={"player": player})
        return Response(serializer.data)


class GameSettingsView(APIView):
    def patch(self, request, room_code):
        game = get_object_or_404(Game, room_code=room_code.upper())
        player = get_player_for_game(request, game)
        if not player.is_host:
            raise PermissionDenied("Only the host can change game settings.")
        if game.status != Game.STATUS_WAITING:
            raise ValidationError("Settings can only be changed before the game starts.")

        difficulty = request.data.get("difficulty")
        valid_values = {value for value, _ in DIFFICULTY_CHOICES}
        if difficulty not in valid_values:
            raise ValidationError({"difficulty": f"Must be one of {sorted(valid_values)}."})

        game.difficulty = difficulty
        game.save(update_fields=["difficulty"])
        broadcast_game_update(game)
        serializer = GameStateSerializer(game, context={"player": player})
        return Response(serializer.data)


class ReplayGameView(APIView):
    def post(self, request, room_code):
        game = get_object_or_404(Game, room_code=room_code.upper())
        player = get_player_for_game(request, game)
        if not player.is_host:
            raise PermissionDenied("Only the host can start a new round.")
        if game.status != Game.STATUS_COMPLETED:
            raise ValidationError("The game must be completed to play again.")

        reset_for_new_round(game)
        try:
            start_game(game)
        except ValueError as exc:
            raise ValidationError(str(exc))
        broadcast_game_update(game)
        serializer = GameStateSerializer(game, context={"player": player})
        return Response(serializer.data)


class ResetToLobbyView(APIView):
    def post(self, request, room_code):
        game = get_object_or_404(Game, room_code=room_code.upper())
        player = get_player_for_game(request, game)
        if not player.is_host:
            raise PermissionDenied("Only the host can return to the lobby.")
        if game.status != Game.STATUS_COMPLETED:
            raise ValidationError("The game must be completed to return to the lobby.")

        reset_for_new_round(game)
        broadcast_game_update(game)
        serializer = GameStateSerializer(game, context={"player": player})
        return Response(serializer.data)


class UndoWinView(APIView):
    def post(self, request, room_code):
        game = get_object_or_404(Game, room_code=room_code.upper())
        player = get_player_for_game(request, game)
        if not player.is_host:
            raise PermissionDenied("Only the host can undo the winning move.")
        if game.status != Game.STATUS_COMPLETED:
            raise ValidationError("There's no winning move to undo right now.")

        try:
            undo_win(game)
        except ValueError as exc:
            raise ValidationError(str(exc))
        broadcast_game_update(game)
        serializer = GameStateSerializer(game, context={"player": player})
        return Response(serializer.data)


class ToggleCellView(APIView):
    def post(self, request, room_code, cell_id):
        game = get_object_or_404(Game, room_code=room_code.upper())
        player = get_player_for_game(request, game)
        cell = get_object_or_404(BoardCell, id=cell_id, player=player)

        if game.status != Game.STATUS_IN_PROGRESS:
            raise ValidationError("This game is not in progress.")
        if cell.is_free_space:
            raise ValidationError("The free space can't be toggled.")

        cell.marked = not cell.marked
        cell.marked_at = timezone.now() if cell.marked else None
        cell.save(update_fields=["marked", "marked_at"])

        check_bingo(player, cell)
        game.refresh_from_db()
        broadcast_game_update(game)
        serializer = GameStateSerializer(game, context={"player": player})
        return Response(serializer.data)

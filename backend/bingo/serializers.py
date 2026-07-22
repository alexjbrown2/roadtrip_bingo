from rest_framework import serializers

from .models import BoardCell, Game, Player


class BoardCellSerializer(serializers.ModelSerializer):
    image = serializers.CharField(source="image_filename")

    class Meta:
        model = BoardCell
        fields = ["id", "item_text", "image", "row", "col", "is_free_space", "marked"]


class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ["id", "nickname", "is_host", "has_bingo"]


class GameStateSerializer(serializers.ModelSerializer):
    players = PlayerSerializer(many=True, read_only=True)
    winner = PlayerSerializer(read_only=True)
    board = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = [
            "room_code",
            "status",
            "board_size",
            "difficulty",
            "players",
            "winner",
            "board",
        ]

    def get_board(self, game):
        player = self.context.get("player")
        if player is None or game.status == Game.STATUS_WAITING:
            return None
        return BoardCellSerializer(player.cells.all(), many=True).data

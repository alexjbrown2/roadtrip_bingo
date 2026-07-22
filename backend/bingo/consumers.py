from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .auth import InvalidPlayerToken, resolve_player
from .models import Game, Player
from .serializers import GameStateSerializer


class GameConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        room_code = self.scope["url_route"]["kwargs"]["room_code"].upper()
        token = parse_qs(self.scope["query_string"].decode()).get("token", [None])[0]

        try:
            player = await self._resolve_player(room_code, token)
        except (Game.DoesNotExist, InvalidPlayerToken):
            await self.close(code=4001)
            return

        self.room_code = room_code
        self.player_id = player.id
        self.group_name = f"game_{room_code}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_state()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def game_update(self, event):
        await self.send_state()

    async def send_state(self):
        await self.send_json(await self._serialize_state())

    @database_sync_to_async
    def _resolve_player(self, room_code, token):
        game = Game.objects.get(room_code=room_code)
        return resolve_player(token, game)

    @database_sync_to_async
    def _serialize_state(self):
        game = Game.objects.get(room_code=self.room_code)
        player = Player.objects.get(id=self.player_id)
        return GameStateSerializer(game, context={"player": player}).data

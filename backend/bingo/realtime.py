from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_game_update(game):
    """Notify every connected socket in this game's room that state has changed.

    The message carries no payload — each consumer re-serializes state for its
    own player (boards are player-specific) when it receives this event.
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"game_{game.room_code}", {"type": "game_update"}
    )

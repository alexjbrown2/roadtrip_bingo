import uuid

from rest_framework.exceptions import AuthenticationFailed

from .models import Player

TOKEN_HEADER = "HTTP_X_PLAYER_TOKEN"


class InvalidPlayerToken(Exception):
    """Raised by resolve_player() when the token doesn't identify a player in the game."""


def resolve_player(raw_token, game):
    """Resolve the Player identified by `raw_token` (a UUID string), scoped to `game`."""
    if not raw_token:
        raise InvalidPlayerToken("Missing player token.")
    try:
        token = uuid.UUID(raw_token)
    except ValueError:
        raise InvalidPlayerToken("Malformed player token.")
    try:
        return Player.objects.get(token=token, game=game)
    except Player.DoesNotExist:
        raise InvalidPlayerToken("Player token does not match this game.")


def get_player_for_game(request, game):
    """Resolve the Player identified by the X-Player-Token header, scoped to `game`."""
    raw_token = request.META.get(TOKEN_HEADER)
    try:
        return resolve_player(raw_token, game)
    except InvalidPlayerToken as exc:
        raise AuthenticationFailed(str(exc))

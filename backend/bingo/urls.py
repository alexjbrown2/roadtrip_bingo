from django.urls import path

from . import views

urlpatterns = [
    path("games/", views.CreateGameView.as_view(), name="game-create"),
    path("games/<str:room_code>/", views.GameStateView.as_view(), name="game-state"),
    path("games/<str:room_code>/join/", views.JoinGameView.as_view(), name="game-join"),
    path("games/<str:room_code>/start/", views.StartGameView.as_view(), name="game-start"),
    path(
        "games/<str:room_code>/settings/",
        views.GameSettingsView.as_view(),
        name="game-settings",
    ),
    path("games/<str:room_code>/replay/", views.ReplayGameView.as_view(), name="game-replay"),
    path("games/<str:room_code>/reset/", views.ResetToLobbyView.as_view(), name="game-reset"),
    path(
        "games/<str:room_code>/undo-win/",
        views.UndoWinView.as_view(),
        name="game-undo-win",
    ),
    path(
        "games/<str:room_code>/cells/<int:cell_id>/toggle/",
        views.ToggleCellView.as_view(),
        name="cell-toggle",
    ),
]

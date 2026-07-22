from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from config.asgi import application

from .models import BoardCell, Game, Item, Player


def seed_items(n=30, difficulty="easy"):
    for i in range(n):
        Item.objects.create(text=f"Item {i}", image_filename=f"item{i}.png", difficulty=difficulty)


class GameFlowTests(TestCase):
    def setUp(self):
        seed_items()

    def create_game(self, nickname="Host"):
        resp = self.client.post(
            reverse("game-create"), {"nickname": nickname}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)
        return resp.json()

    def join_game(self, room_code, nickname="Guest"):
        resp = self.client.post(
            reverse("game-join", args=[room_code]),
            {"nickname": nickname},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        return resp.json()

    def get_state(self, room_code, token):
        return self.client.get(
            reverse("game-state", args=[room_code]), HTTP_X_PLAYER_TOKEN=token
        )

    def test_create_and_join_game(self):
        host = self.create_game("Alice")
        self.assertEqual(len(host["room_code"]), 6)

        guest = self.join_game(host["room_code"], "Bob")
        self.assertNotEqual(host["player_token"], guest["player_token"])

        resp = self.get_state(host["room_code"], host["player_token"])
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "waiting")
        self.assertEqual(data["difficulty"], "easy")
        self.assertEqual(len(data["players"]), 2)
        self.assertIsNone(data["board"])

    def test_join_requires_nickname(self):
        host = self.create_game()
        resp = self.client.post(
            reverse("game-join", args=[host["room_code"]]),
            {"nickname": ""},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_cannot_join_started_game(self):
        host = self.create_game()
        self.client.post(
            reverse("game-start", args=[host["room_code"]]),
            HTTP_X_PLAYER_TOKEN=host["player_token"],
        )
        resp = self.client.post(
            reverse("game-join", args=[host["room_code"]]),
            {"nickname": "Late"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_only_host_can_start(self):
        host = self.create_game()
        guest = self.join_game(host["room_code"])
        resp = self.client.post(
            reverse("game-start", args=[host["room_code"]]),
            HTTP_X_PLAYER_TOKEN=guest["player_token"],
        )
        self.assertEqual(resp.status_code, 403)

    def test_start_generates_unique_boards(self):
        host = self.create_game()
        guest = self.join_game(host["room_code"])

        resp = self.client.post(
            reverse("game-start", args=[host["room_code"]]),
            HTTP_X_PLAYER_TOKEN=host["player_token"],
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "in_progress")
        self.assertEqual(len(data["board"]), 25)
        free_spaces = [c for c in data["board"] if c["is_free_space"]]
        self.assertEqual(len(free_spaces), 1)
        self.assertTrue(free_spaces[0]["marked"])
        non_free = [c for c in data["board"] if not c["is_free_space"]]
        self.assertTrue(all(c["image"] for c in non_free))

        host_items = {c["item_text"] for c in non_free}

        guest_resp = self.get_state(host["room_code"], guest["player_token"])
        guest_board = guest_resp.json()["board"]
        guest_items = {c["item_text"] for c in guest_board if not c["is_free_space"]}

        self.assertEqual(host_items, guest_items)  # same pool
        host_layout = [c["item_text"] for c in data["board"]]
        guest_layout = [c["item_text"] for c in guest_board]
        self.assertNotEqual(host_layout, guest_layout)  # different arrangement

    def test_wrong_token_rejected(self):
        host = self.create_game()
        resp = self.get_state(host["room_code"], "not-a-real-token")
        self.assertEqual(resp.status_code, 403)

    def test_missing_token_rejected(self):
        host = self.create_game()
        resp = self.client.get(reverse("game-state", args=[host["room_code"]]))
        self.assertEqual(resp.status_code, 403)

    def test_toggle_and_bingo_detection(self):
        host = self.create_game()
        self.client.post(
            reverse("game-start", args=[host["room_code"]]),
            HTTP_X_PLAYER_TOKEN=host["player_token"],
        )
        player = Player.objects.get(token=host["player_token"])

        # Mark the entire top row (row=0) to force a bingo.
        top_row_cells = BoardCell.objects.filter(player=player, row=0)
        game_status = None
        for cell in top_row_cells:
            resp = self.client.post(
                reverse("cell-toggle", args=[host["room_code"], cell.id]),
                HTTP_X_PLAYER_TOKEN=host["player_token"],
            )
            self.assertEqual(resp.status_code, 200)
            game_status = resp.json()["status"]

        self.assertEqual(game_status, "completed")
        player.refresh_from_db()
        self.assertTrue(player.has_bingo)

    def test_cannot_toggle_someone_elses_cell(self):
        host = self.create_game()
        guest = self.join_game(host["room_code"])
        self.client.post(
            reverse("game-start", args=[host["room_code"]]),
            HTTP_X_PLAYER_TOKEN=host["player_token"],
        )
        host_player = Player.objects.get(token=host["player_token"])
        cell = BoardCell.objects.filter(player=host_player, is_free_space=False).first()

        resp = self.client.post(
            reverse("cell-toggle", args=[host["room_code"], cell.id]),
            HTTP_X_PLAYER_TOKEN=guest["player_token"],
        )
        self.assertEqual(resp.status_code, 404)

    def test_free_space_cannot_be_toggled(self):
        host = self.create_game()
        self.client.post(
            reverse("game-start", args=[host["room_code"]]),
            HTTP_X_PLAYER_TOKEN=host["player_token"],
        )
        player = Player.objects.get(token=host["player_token"])
        free_cell = BoardCell.objects.get(player=player, is_free_space=True)

        resp = self.client.post(
            reverse("cell-toggle", args=[host["room_code"], free_cell.id]),
            HTTP_X_PLAYER_TOKEN=host["player_token"],
        )
        self.assertEqual(resp.status_code, 400)


class GameSettingsTests(TestCase):
    def setUp(self):
        seed_items()

    def create_game(self, nickname="Host"):
        resp = self.client.post(
            reverse("game-create"), {"nickname": nickname}, content_type="application/json"
        )
        return resp.json()

    def join_game(self, room_code, nickname="Guest"):
        resp = self.client.post(
            reverse("game-join", args=[room_code]),
            {"nickname": nickname},
            content_type="application/json",
        )
        return resp.json()

    def patch_settings(self, room_code, token, difficulty):
        return self.client.patch(
            reverse("game-settings", args=[room_code]),
            {"difficulty": difficulty},
            content_type="application/json",
            HTTP_X_PLAYER_TOKEN=token,
        )

    def test_host_can_change_difficulty(self):
        host = self.create_game()
        resp = self.patch_settings(host["room_code"], host["player_token"], "hard")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["difficulty"], "hard")

    def test_non_host_cannot_change_difficulty(self):
        host = self.create_game()
        guest = self.join_game(host["room_code"])
        resp = self.patch_settings(host["room_code"], guest["player_token"], "hard")
        self.assertEqual(resp.status_code, 403)

    def test_invalid_difficulty_rejected(self):
        host = self.create_game()
        resp = self.patch_settings(host["room_code"], host["player_token"], "extreme")
        self.assertEqual(resp.status_code, 400)

    def test_cannot_change_difficulty_after_start(self):
        host = self.create_game()
        self.client.post(
            reverse("game-start", args=[host["room_code"]]),
            HTTP_X_PLAYER_TOKEN=host["player_token"],
        )
        resp = self.patch_settings(host["room_code"], host["player_token"], "hard")
        self.assertEqual(resp.status_code, 400)


class DifficultyPoolTests(TestCase):
    def setUp(self):
        Item.objects.all().delete()
        for i in range(4):
            Item.objects.create(text=f"Easy {i}", image_filename=f"easy{i}.png", difficulty="easy")
        for i in range(4):
            Item.objects.create(text=f"Medium {i}", image_filename=f"med{i}.png", difficulty="medium")
        for i in range(4):
            Item.objects.create(text=f"Hard {i}", image_filename=f"hard{i}.png", difficulty="hard")

    def create_game(self, nickname="Host"):
        resp = self.client.post(
            reverse("game-create"), {"nickname": nickname}, content_type="application/json"
        )
        return resp.json()

    def start(self, room_code, token):
        return self.client.post(
            reverse("game-start", args=[room_code]), HTTP_X_PLAYER_TOKEN=token
        )

    def test_medium_difficulty_pool_is_cumulative_and_shrinks_board(self):
        host = self.create_game()
        self.client.patch(
            reverse("game-settings", args=[host["room_code"]]),
            {"difficulty": "medium"},
            content_type="application/json",
            HTTP_X_PLAYER_TOKEN=host["player_token"],
        )
        resp = self.start(host["room_code"], host["player_token"])
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # 8 items available (4 easy + 4 medium) -> exactly meets the 3x3 floor (8 cells).
        self.assertEqual(data["board_size"], 3)
        board_texts = {c["item_text"] for c in data["board"] if c["item_text"] != "Free Space"}
        easy_and_medium = {f"Easy {i}" for i in range(4)} | {f"Medium {i}" for i in range(4)}
        hard = {f"Hard {i}" for i in range(4)}
        self.assertTrue(board_texts.issubset(easy_and_medium))
        self.assertFalse(board_texts & hard)

    def test_easy_difficulty_with_too_few_items_returns_400(self):
        Item.objects.filter(difficulty="easy").exclude(text="Easy 0").delete()
        host = self.create_game()  # difficulty defaults to "easy", only 1 easy item left
        resp = self.start(host["room_code"], host["player_token"])
        self.assertEqual(resp.status_code, 400)


class ChannelsTests(TransactionTestCase):
    """WebSocketCommunicator-based tests need TransactionTestCase: the consumer's
    database_sync_to_async calls run on a separate thread that can't see rows
    created inside TestCase's uncommitted wrapping transaction."""

    def setUp(self):
        seed_items()

    def _create_game(self, nickname="Host"):
        resp = self.client.post(
            reverse("game-create"), {"nickname": nickname}, content_type="application/json"
        )
        return resp.json()

    def _join_game(self, room_code, nickname="Guest"):
        resp = self.client.post(
            reverse("game-join", args=[room_code]),
            {"nickname": nickname},
            content_type="application/json",
        )
        return resp.json()

    def _start_game(self, room_code, token):
        return self.client.post(
            reverse("game-start", args=[room_code]), HTTP_X_PLAYER_TOKEN=token
        )

    async def test_connect_rejects_invalid_token(self):
        host = await sync_to_async(self._create_game)()
        communicator = WebsocketCommunicator(
            application, f"/ws/games/{host['room_code']}/?token=not-a-real-token"
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_connect_delivers_initial_state(self):
        host = await sync_to_async(self._create_game)()
        communicator = WebsocketCommunicator(
            application, f"/ws/games/{host['room_code']}/?token={host['player_token']}"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        message = await communicator.receive_json_from()
        self.assertEqual(message["room_code"], host["room_code"])
        self.assertEqual(message["status"], "waiting")

        await communicator.disconnect()

    async def test_toggle_broadcasts_bingo_to_all_connected_sockets(self):
        host = await sync_to_async(self._create_game)()
        guest = await sync_to_async(self._join_game)(host["room_code"])

        host_ws = WebsocketCommunicator(
            application, f"/ws/games/{host['room_code']}/?token={host['player_token']}"
        )
        guest_ws = WebsocketCommunicator(
            application, f"/ws/games/{host['room_code']}/?token={guest['player_token']}"
        )
        await host_ws.connect()
        await guest_ws.connect()
        await host_ws.receive_json_from()  # initial "waiting" push
        await guest_ws.receive_json_from()

        await sync_to_async(self._start_game)(host["room_code"], host["player_token"])
        host_state = await host_ws.receive_json_from()
        guest_state = await guest_ws.receive_json_from()
        self.assertEqual(host_state["status"], "in_progress")
        self.assertEqual(guest_state["status"], "in_progress")

        top_row_cell_ids = await sync_to_async(
            lambda: list(
                BoardCell.objects.filter(
                    player__token=host["player_token"], row=0
                ).values_list("id", flat=True)
            )
        )()
        self.assertTrue(top_row_cell_ids)

        for cell_id in top_row_cell_ids:
            await sync_to_async(self.client.post)(
                reverse("cell-toggle", args=[host["room_code"], cell_id]),
                HTTP_X_PLAYER_TOKEN=host["player_token"],
            )
            await host_ws.receive_json_from()
            guest_state = await guest_ws.receive_json_from()

        self.assertEqual(guest_state["status"], "completed")
        self.assertEqual(guest_state["winner"]["nickname"], "Host")

        await host_ws.disconnect()
        await guest_ws.disconnect()


class RestartTests(TestCase):
    def setUp(self):
        seed_items()

    def create_game(self, nickname="Host"):
        resp = self.client.post(
            reverse("game-create"), {"nickname": nickname}, content_type="application/json"
        )
        return resp.json()

    def join_game(self, room_code, nickname="Guest"):
        resp = self.client.post(
            reverse("game-join", args=[room_code]),
            {"nickname": nickname},
            content_type="application/json",
        )
        return resp.json()

    def start_game(self, room_code, token):
        return self.client.post(
            reverse("game-start", args=[room_code]), HTTP_X_PLAYER_TOKEN=token
        )

    def win_game(self, room_code, token):
        """Mark the host's entire top row to reach a completed game."""
        player = Player.objects.get(token=token)
        cell_ids = BoardCell.objects.filter(player=player, row=0).values_list("id", flat=True)
        for cell_id in cell_ids:
            self.client.post(
                reverse("cell-toggle", args=[room_code, cell_id]),
                HTTP_X_PLAYER_TOKEN=token,
            )

    def test_replay_generates_fresh_boards_and_resumes_play(self):
        host = self.create_game()
        self.start_game(host["room_code"], host["player_token"])
        self.win_game(host["room_code"], host["player_token"])

        resp = self.client.post(
            reverse("game-replay", args=[host["room_code"]]),
            HTTP_X_PLAYER_TOKEN=host["player_token"],
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "in_progress")
        self.assertIsNone(data["winner"])
        self.assertFalse(any(p["has_bingo"] for p in data["players"]))
        self.assertTrue(all(not c["marked"] for c in data["board"] if not c["is_free_space"]))

    def test_replay_rejected_for_non_host(self):
        host = self.create_game()
        guest = self.join_game(host["room_code"])
        self.start_game(host["room_code"], host["player_token"])
        self.win_game(host["room_code"], host["player_token"])

        resp = self.client.post(
            reverse("game-replay", args=[host["room_code"]]),
            HTTP_X_PLAYER_TOKEN=guest["player_token"],
        )
        self.assertEqual(resp.status_code, 403)

    def test_replay_rejected_when_not_completed(self):
        host = self.create_game()
        resp = self.client.post(
            reverse("game-replay", args=[host["room_code"]]),
            HTTP_X_PLAYER_TOKEN=host["player_token"],
        )
        self.assertEqual(resp.status_code, 400)

    def test_reset_returns_to_lobby_and_clears_board(self):
        host = self.create_game()
        self.start_game(host["room_code"], host["player_token"])
        self.win_game(host["room_code"], host["player_token"])

        resp = self.client.post(
            reverse("game-reset", args=[host["room_code"]]),
            HTTP_X_PLAYER_TOKEN=host["player_token"],
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "waiting")
        self.assertIsNone(data["winner"])
        self.assertIsNone(data["board"])

        player = Player.objects.get(token=host["player_token"])
        self.assertFalse(player.has_bingo)
        self.assertEqual(BoardCell.objects.filter(player=player).count(), 0)

    def test_reset_rejected_for_non_host(self):
        host = self.create_game()
        guest = self.join_game(host["room_code"])
        self.start_game(host["room_code"], host["player_token"])
        self.win_game(host["room_code"], host["player_token"])

        resp = self.client.post(
            reverse("game-reset", args=[host["room_code"]]),
            HTTP_X_PLAYER_TOKEN=guest["player_token"],
        )
        self.assertEqual(resp.status_code, 403)

    def test_can_join_again_after_reset(self):
        host = self.create_game()
        self.start_game(host["room_code"], host["player_token"])
        self.win_game(host["room_code"], host["player_token"])
        self.client.post(
            reverse("game-reset", args=[host["room_code"]]),
            HTTP_X_PLAYER_TOKEN=host["player_token"],
        )

        resp = self.client.post(
            reverse("game-join", args=[host["room_code"]]),
            {"nickname": "Latecomer"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_undo_win_reverts_winning_cell_and_resumes_play(self):
        host = self.create_game()
        self.start_game(host["room_code"], host["player_token"])
        self.win_game(host["room_code"], host["player_token"])

        player = Player.objects.get(token=host["player_token"])
        # BoardCell's default ordering is (row, col), matching the order win_game
        # marks them in — the last one marked is the one that completed the bingo.
        winning_cell_id = list(
            BoardCell.objects.filter(player=player, row=0).values_list("id", flat=True)
        )[-1]

        resp = self.client.post(
            reverse("game-undo-win", args=[host["room_code"]]),
            HTTP_X_PLAYER_TOKEN=host["player_token"],
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "in_progress")
        self.assertIsNone(data["winner"])
        self.assertFalse(any(p["has_bingo"] for p in data["players"]))

        # The rest of the top row stays marked — only the winning cell reverted.
        top_row = {c["id"]: c["marked"] for c in data["board"] if c["row"] == 0}
        self.assertFalse(top_row[winning_cell_id])
        self.assertTrue(any(marked for cid, marked in top_row.items() if cid != winning_cell_id))

        # Play can continue: re-marking the reverted cell wins again.
        resp = self.client.post(
            reverse("cell-toggle", args=[host["room_code"], winning_cell_id]),
            HTTP_X_PLAYER_TOKEN=host["player_token"],
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "completed")

    def test_undo_win_rejected_for_non_host(self):
        host = self.create_game()
        guest = self.join_game(host["room_code"])
        self.start_game(host["room_code"], host["player_token"])
        self.win_game(host["room_code"], host["player_token"])

        resp = self.client.post(
            reverse("game-undo-win", args=[host["room_code"]]),
            HTTP_X_PLAYER_TOKEN=guest["player_token"],
        )
        self.assertEqual(resp.status_code, 403)

    def test_undo_win_rejected_when_not_completed(self):
        host = self.create_game()
        self.start_game(host["room_code"], host["player_token"])

        resp = self.client.post(
            reverse("game-undo-win", args=[host["room_code"]]),
            HTTP_X_PLAYER_TOKEN=host["player_token"],
        )
        self.assertEqual(resp.status_code, 400)

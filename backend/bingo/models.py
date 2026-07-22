import random
import uuid

from django.db import models

DIFFICULTY_CHOICES = [
    ("easy", "Easy"),
    ("medium", "Medium"),
    ("hard", "Hard"),
]


def generate_room_code():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I
    while True:
        code = "".join(random.choices(alphabet, k=6))
        if not Game.objects.filter(room_code=code).exists():
            return code


class Item(models.Model):
    text = models.CharField(max_length=200, unique=True)
    image_filename = models.CharField(max_length=200)
    difficulty = models.CharField(
        max_length=10, choices=DIFFICULTY_CHOICES, default="easy"
    )

    def __str__(self):
        return self.text


class Game(models.Model):
    STATUS_WAITING = "waiting"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_WAITING, "Waiting"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_COMPLETED, "Completed"),
    ]

    room_code = models.CharField(
        max_length=6, unique=True, default=generate_room_code
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_WAITING
    )
    board_size = models.PositiveSmallIntegerField(default=5)
    difficulty = models.CharField(
        max_length=10, choices=DIFFICULTY_CHOICES, default="easy"
    )
    item_pool = models.JSONField(default=list, blank=True)
    winner = models.ForeignKey(
        "Player",
        null=True,
        blank=True,
        related_name="won_games",
        on_delete=models.SET_NULL,
    )
    winning_cell = models.ForeignKey(
        "BoardCell",
        null=True,
        blank=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.room_code


class Player(models.Model):
    game = models.ForeignKey(Game, related_name="players", on_delete=models.CASCADE)
    nickname = models.CharField(max_length=50)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_host = models.BooleanField(default=False)
    has_bingo = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["joined_at"]

    def __str__(self):
        return f"{self.nickname} ({self.game.room_code})"


class BoardCell(models.Model):
    player = models.ForeignKey(Player, related_name="cells", on_delete=models.CASCADE)
    item_text = models.CharField(max_length=200)
    image_filename = models.CharField(max_length=200, blank=True)
    row = models.PositiveSmallIntegerField()
    col = models.PositiveSmallIntegerField()
    is_free_space = models.BooleanField(default=False)
    marked = models.BooleanField(default=False)
    marked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["row", "col"]
        constraints = [
            models.UniqueConstraint(
                fields=["player", "row", "col"], name="unique_cell_position_per_player"
            )
        ]

    def __str__(self):
        return f"{self.player.nickname} [{self.row},{self.col}] {self.item_text}"

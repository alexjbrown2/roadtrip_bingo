from django.contrib import admin

from .models import BoardCell, Game, Item, Player


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ["text", "difficulty", "image_filename"]
    list_filter = ["difficulty"]
    search_fields = ["text", "image_filename"]


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ["room_code", "status", "difficulty", "created_at"]
    search_fields = ["room_code"]


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ["nickname", "game", "is_host", "has_bingo"]


admin.site.register(BoardCell)

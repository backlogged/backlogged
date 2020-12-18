from django.contrib import admin

from app.models import *


class BackloggedGamesAdmin(admin.ModelAdmin):
    list_display = ("entry_id", "get_user", "game_name", "platform_name", "status_name", "date_added")

    def get_user(self, obj):
        return obj.user.username
    get_user.short_description = "User"
    get_user.admin_order_field = "user__username"


admin.site.register(BackloggedGamesModel, BackloggedGamesAdmin)

"""
Database models.
"""

from django.contrib.auth.models import User
from django.db import models


class BackloggedGame(models.Model):
    """
    Model for all games in user backlogs.
    """
    entry_id = models.AutoField(primary_key=True)  # uniquely identifies the backlog entry in the database
    game_id = models.CharField(max_length=1024)  # the game's unique identifier
    game_name = models.CharField(max_length=1024)  # the game's name
    cover_url = models.URLField()  # a link to an image of the game's over art
    platform_id = models.IntegerField()  # the unique identifier for a platform on IGDB
    platform_name = models.CharField(max_length=1024)  # the name of a platform
    status_id = models.IntegerField(default=0)  # the game's status; 1 = backlog, 2 = Now Playing
    status_name = models.CharField(max_length=1024)  # the name corresponding to status_id
    date_added = models.DateField()  # the date the game was added; YYYY-MM-DD
    is_custom = models.BooleanField(default=False)  # indicates whether the game is a custom game
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # the id of the user who added the game

    @property
    def custom_data(self):
        try:
            return self.customgame
        except CustomGame.DoesNotExist:
            return None


class CustomGame(models.Model):
    """
    Model for custom games.
    """
    backlogged = models.OneToOneField(BackloggedGame, primary_key=True, on_delete=models.CASCADE)
    involved_companies = models.CharField(max_length=1024, default=None)
    summary = models.CharField(max_length=3000, default=None)
    cover_img = models.ImageField(upload_to="Backlogged Custom Games/")
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class UserTimezone(models.Model):
    """
    Model for user time zones.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # an id of a user
    timezone = models.CharField(max_length=1024)  # a time zone (e.g. America/New_York)

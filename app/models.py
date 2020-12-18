from django.db import models
from django.contrib.auth.models import User


class BackloggedGameModel(models.Model):
    entry_id = models.AutoField(primary_key=True)
    game_id = models.IntegerField()
    game_name = models.CharField(max_length=1024, default="")
    cover_url = models.URLField(default="")
    platform_id = models.IntegerField()
    platform_name = models.CharField(max_length=1024, default="")
    status_id = models.IntegerField(default=0)
    status_name = models.CharField(max_length=1024)
    date_added = models.DateField(default="1970-01-01")
    user = models.ForeignKey(User, on_delete=models.CASCADE)

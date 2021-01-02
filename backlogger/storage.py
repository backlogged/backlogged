import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class OverwriteStorage(FileSystemStorage):
    """
    If a model field with this storage class attempts to save a file with the same name as an existing file,
    the existing file will be deleted before the new file is saved.
    """
    def get_available_name(self, name, max_length=None):

        if self.exists(name):
            os.remove(os.path.join(settings.MEDIA_ROOT, name))

        return name

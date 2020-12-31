"""
Forms.
"""

import pytz
from crispy_forms.helper import FormHelper
from django import forms

from app.helpers import platform_getter


class GameSearchForm(forms.Form):
    """
    Faciliates IGDB-dependent game searches.
    """
    # static fields
    query = forms.CharField(max_length=1024, widget=forms.TextInput(attrs={"placeholder": "Search for a game"}))

    def __init__(self, *args, **kwargs):
        # super call
        super().__init__(*args, **kwargs)

        # crispy-forms attributes
        self.helper = FormHelper()
        self.helper.form_show_labels = False

        # html attribute assignments
        self.fields["query"].widget.attrs["class"] = "form-control"


class BacklogSearchForm(forms.Form):
    """
    Facilitates backlog game searches, which use Backlogged's own database.
    """
    # static fields
    query = forms.CharField(max_length=1024, widget=forms.TextInput(attrs={"placeholder": "Search your backlog"}))

    def __init__(self, *args, **kwargs):
        # super call
        super().__init__(*args, **kwargs)

        # crispy-forms attributes
        self.helper = FormHelper()
        self.helper.form_show_labels = False

        # html attribute assignments
        self.fields["query"].widget.attrs["class"] = "form-control"


class BacklogFilterForm(forms.Form):
    """
    Faciliates backlog sorting functionality.
    """
    # static fields
    sort_option = forms.CharField()


class GameUpdateForm(forms.Form):
    """
    Faciliates the handling of information about an individual game in a user's backlog, including adding and removing
    said game, the game's Now Playing status (or lack thereof), and the platform on which the user has indicated they
    have the game.
    """
    # static fields
    now_playing = forms.BooleanField(required=False)
    update_mode = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        # kwargs retrieval
        self.game_dict = kwargs.pop("game_dict")
        self.num_now_playing = kwargs.pop("num_now_playing")

        # super call
        super().__init__(*args, **kwargs)

        # crispy-forms attributes
        self.helper = FormHelper()
        self.helper.form_show_labels = False

        try:
            self.game_dict["platforms"]
        except KeyError:
            pass
        else:
            # dynamic platform field initialization
            self.platform_list = []
            for platform in self.game_dict["platforms"]:
                platform_str = f"{platform['platform_id']},{platform['platform_name']}"
                self.platform_list.append((platform_str, platform["platform_name"]))

            self.fields["platform"] = forms.ChoiceField(choices=self.platform_list, required=False)

            # html attribute assignments
            self.fields["platform"].widget.attrs["class"] = "select btn btn-secondary"
            self.fields["now_playing"].widget.attrs["id"] = "npCheckbox"
            self.fields["now_playing"].widget.attrs["onclick"] = "statusToggle()"
            if self.num_now_playing >= 10:
                self.fields["now_playing"].widget.attrs["disabled"] = ""
                self.fields["now_playing"].widget.attrs["style"] = "pointer-events: none;"


class TimezoneUpdateForm(forms.Form):
    """
    Faciliates the updating of a user's time zone.
    """

    def __init__(self, *args, **kwargs):
        # super call
        super().__init__(*args, **kwargs)

        # timezone field initialization
        self.timezone_list = []
        for tz in pytz.all_timezones:
            self.timezone_list.append((tz, tz.replace("_", " ")))

        self.fields["timezone"] = forms.ChoiceField(label="Time zone", choices=self.timezone_list)


class CustomGameForm(forms.Form):
    """
    Faciliates adding and editing custom games.
    """
    # static fields
    game_name = forms.CharField(max_length=1024,
                                widget=forms.TextInput(attrs={"placeholder": "Game name (e.g. Sonic the Hedgehog 2)"}))
    involved_companies = forms.CharField(max_length=1024, required=False, widget=forms.TextInput(
        attrs={"placeholder": "Involved companies (e.g. Sega, Sonic Team) (optional)"}))
    summary = forms.CharField(max_length=1024, widget=forms.TextInput(attrs={"placeholder": "Game summary (optional)"}),
                              required=False)
    cover_img = forms.ImageField(label="Cover art (optional)", required=False)
    now_playing = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        # kwargs retrieval
        self.num_now_playing = kwargs.pop("num_now_playing", 0)

        # super call
        super().__init__(*args, **kwargs)

        # crispy-forms attributes
        self.helper = FormHelper()
        self.helper.form_show_labels = False

        # platform field
        self.platform_list = []
        for platform in platform_getter():
            platform_str = f"{platform['platform_id']},{platform['platform_name']}"
            platform_group = (platform_str, platform["platform_name"])
            if platform_group not in self.platform_list:
                self.platform_list.append(platform_group)

        self.fields["platform"] = forms.ChoiceField(choices=self.platform_list)

        # html attribute assignments
        self.fields["involved_companies"].widget.attrs["style"] = "width: 35em"

        self.fields["game_name"].widget.attrs["style"] = "width: 20em"

        self.fields["summary"].widget.attrs["style"] = "height: 6em"

        self.fields["platform"].widget.attrs["class"] = "select btn btn-secondary"

        self.fields["cover_img"].widget.attrs["type"] = "file"
        self.fields["cover_img"].widget.attrs["class"] = "custom-file-input"
        self.fields["cover_img"].widget.attrs["id"] = "customFile"
        self.fields["cover_img"].widget.attrs["style"] = "width: 264px"

        if self.num_now_playing >= 10:
            self.fields["now_playing"].widget.attrs["disabled"] = ""
            self.fields["now_playing"].widget.attrs["style"] = "pointer-events: none;"


class CustomGameSubmit(forms.Form):
    # static fields
    submit = forms.CharField()


class PasswordCheckForm(forms.Form):
    # static fields
    password = forms.CharField(widget=forms.PasswordInput())

    def __init__(self, *args, **kwargs):
        # kwargs retrieval
        self.user = kwargs.pop("user")
        # super call
        super().__init__(*args, **kwargs)

        # crispy-forms attributes
        self.helper = FormHelper()
        self.helper.form_show_labels = False

        self.fields["password"].widget.attrs = {"placeholder": "Password", "oninput": "checkPasswordField();"}

    def clean_password(self):
        password = self.cleaned_data["password"]

        if not self.user.check_password(password):
            raise forms.ValidationError("That's the wrong password.")
        else:
            self.user.delete()

        return password

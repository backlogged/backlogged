from crispy_forms.helper import FormHelper
from django import forms


class GameSearchForm(forms.Form):
    # static fields
    query = forms.CharField(max_length=1024, widget=forms.TextInput(attrs={"placeholder": "Search for a game"}))

    def __init__(self, *args, **kwargs):
        # crispy-forms attributes
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False

        # html attribute assignment
        self.fields["query"].widget.attrs["class"] = "form-control"


class BacklogSearchForm(forms.Form):
    # static fields
    query = forms.CharField(max_length=1024, widget=forms.TextInput(attrs={"placeholder": "Search your backlog"}))

    def __init__(self, *args, **kwargs):
        # crispy-forms attributes
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False

        # html attribute assignment
        self.fields["query"].widget.attrs["class"] = "form-control"


class BacklogFilterForm(forms.Form):
    # static fields
    sort_option = forms.CharField()


class AddGameForm(forms.Form):
    # static fields
    now_playing = forms.BooleanField(required=False)
    update_mode = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        # kwargs retrieval
        self.game_dict = kwargs.pop("game_dict")
        self.num_now_playing = kwargs.pop("num_now_playing")

        super().__init__(*args, **kwargs)
        # crispy-forms attributes
        self.helper = FormHelper()
        self.helper.form_show_labels = False

        # dynamic platform field initialization
        self.platform_list = []
        for platform in self.game_dict["platforms"]:
            platform_str = f"{platform['platform_id']},{platform['platform_name']}"
            self.platform_list.append((platform_str, platform["platform_name"]))

        self.fields["platform"] = forms.CharField(widget=forms.Select(choices=self.platform_list), required=False)

        # html attribute assignments
        self.fields["platform"].widget.attrs["class"] = "select btn btn-secondary"
        self.fields["now_playing"].widget.attrs["id"] = "npCheckbox"
        self.fields["now_playing"].widget.attrs["onclick"] = "statusToggle()"
        if self.num_now_playing >= 7:
            self.fields["now_playing"].widget.attrs["disabled"] = ""
            self.fields["now_playing"].widget.attrs["style"] = "pointer-events: none;"

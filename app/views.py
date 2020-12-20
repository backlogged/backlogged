import json
import os
from datetime import datetime

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.shortcuts import redirect, render
from django.views.generic import CreateView, UpdateView, DeleteView, FormView, TemplateView, ListView

import app.helpers as helpers
from app.forms import *
from app.models import *

backlog = BackloggedGamesModel.objects
timezones = UserTimezoneModel.objects


class HomePageView(TemplateView):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("backlog")
        else:
            return render(request, template_name="home.html")


class SignUpView(CreateView):
    form_class = UserCreationForm
    success_url = "/login"
    template_name = "signup.html"


class SignInView(LoginView):
    redirect_authenticated_user = True
    template_name = "login.html"


class BacklogView(LoginRequiredMixin, ListView):
    login_url = "/login"
    template_name = "backlog.html"
    paginate_by = 21

    def __init__(self):
        super().__init__()
        self.is_searching = False
        self.is_filtering = False
        self.search_query = None
        self.filter_mode = None

    def get_queryset(self):
        user_id = self.request.user.id
        search_form = BacklogSearchForm(self.request.GET)
        filter_form = BacklogFilterForm(self.request.GET)
        queryset = backlog.filter(user_id=user_id).order_by("-status_id")

        if filter_form.is_valid():
            self.filter_mode = self.request.GET
            self.is_filtering = True
            filter_data = filter_form.cleaned_data
            sort_option = filter_data["sort_option"]
            queryset = backlog.filter(user_id=user_id).order_by("game_name")

            if sort_option == "alphabetic":
                self.filter_mode = "A-Z"
            elif sort_option.startswith("date"):
                if sort_option == "date_oldest":
                    self.filter_mode = "Date Added (Oldest)"
                    queryset = queryset.order_by("date_added")
                elif sort_option == "date_newest":
                    self.filter_mode = "Date Added (Newest)"
                    queryset = queryset.order_by("-date_added")
            else:
                filter_platform_id = int(filter_data["sort_option"])
                filter_platform_name = \
                    backlog.filter(platform_id=filter_platform_id).values_list("platform_name", flat=True).distinct()
                self.filter_mode = filter_platform_name[0]
                queryset = queryset.filter(platform_id=filter_platform_id)

        if search_form.is_valid():
            self.search_query = self.request.GET
            self.is_searching = True
            search_data = search_form.cleaned_data
            if search_data["query"]:
                search_query = "\W*".join(search_data["query"])
                queryset = backlog.filter(user_id=user_id, game_name__iregex=search_query).order_by("game_name")

        return queryset

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "search_form": BacklogSearchForm(self.search_query),
            "filter_form": BacklogFilterForm(self.filter_mode),
        })

        user_id = self.request.user.id

        try:
            timezones.get(user_id=user_id)
        except UserTimezoneModel.DoesNotExist:
            current_date = helpers.get_local_date(self.request, use_api=True)
        else:
            current_date = helpers.get_local_date(self.request, use_api=False)

        context["current_date"] = current_date

        page_obj = context["page_obj"]
        last_page = page_obj.paginator.num_pages
        page_range = helpers.pagination_helper(page_obj.number, last_page)

        context.update({
            "page_range": page_range,
            "last_page": last_page
        })

        if self.is_searching:
            search_form = BacklogSearchForm(self.search_query)
            context.update({
                "is_searching": True,
                "search_form": search_form,
            })

        if self.is_filtering:
            context.update({
                "is_filtering": True,
                "filter_mode": self.filter_mode,
            })

        user_platforms = backlog.filter(user_id=user_id).values(
            "platform_id", "platform_name").distinct().order_by("platform_name")

        num_now_playing = backlog.filter(user_id=user_id, status_id=2).count()

        if page_obj.number == 1 and not (self.is_searching or self.is_filtering):
            game_slice = f"0:{num_now_playing}"
            remaining_slice = f"{num_now_playing}:"
            context["remaining_slice"] = remaining_slice
        else:
            game_slice = ":"

        url_parameters = helpers.request_constructor(self.request.GET)

        context.update({
            "user_platforms": user_platforms,
            "game_slice": game_slice,
            "url_parameters": url_parameters
        })

        return context


class AddGameSearchView(LoginRequiredMixin, FormView):
    template_name = "addgamesearch.html"
    form_class = GameSearchForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            "search_form": GameSearchForm()
        })

        return context


class AddGameSearchResultsView(LoginRequiredMixin, TemplateView):

    def get(self, request, *args, **kwargs):
        search_form = GameSearchForm(self.request.GET)

        if search_form.is_valid():
            self.request.session["request_data"] = self.request.GET
        else:
            search_form = GameSearchForm(self.request.session["request_data"])
            if search_form.is_valid():
                pass

        search_data = search_form.cleaned_data
        page = kwargs.get("page", 1)
        offset = (page - 1) * 50
        game_info_dicts = helpers.get_search_view_dicts(search_data["query"], offset=offset)
        if len(game_info_dicts) == 1 and offset == 0:
            game = game_info_dicts[0]
            return redirect('game-info', game_id=game["id"])
        next_page_exists = bool(helpers.get_search_view_dicts(search_data["query"], offset=offset + 50))

        context = {
            "game_info_dicts": game_info_dicts,
            "search_form": search_form,
            "page": page,
            "next_page_exists": next_page_exists
        }

        return render(request, template_name="addgamesearchresults.html", context=context)


class GameInfoView(LoginRequiredMixin, FormView):
    template_name = "gameinfo.html"
    form_class = GameUpdateForm

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()

        self.kwargs.update({
            "game_dict": helpers.get_game_info_dict(self.kwargs.get("game_id"))
        })

        form_kwargs.update({
            "game_dict": self.kwargs.get("game_dict"),
            "num_now_playing": backlog.filter(status_name="Now Playing", user_id=self.request.user.id).count()
        })

        return form_kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        game_dict = self.kwargs.get("game_dict")

        context.update({
            "game": game_dict,
            "num_now_playing": backlog.filter(status_name="Now Playing", user_id=self.request.user.id).count(),
            "now_playing_message": "You can only have up to 7 games in your Now Playing at a time. "
                                   "Remove some games from your Now Playing before adding this one."
        })

        try:
            existing_game_entry = backlog.get(game_id=game_dict["id"], user_id=self.request.user.id)
        except BackloggedGamesModel.DoesNotExist:
            pass
        else:
            recorded_platform_id, recorded_status = existing_game_entry.platform_id, existing_game_entry.status_name
            recorded_platform_name = existing_game_entry.platform_name
            multiple_platforms_exist = bool(len(game_dict["platforms"]) > 1)

            context.update({
                "game_entry_exists": True,
                "recorded_platform_name": recorded_platform_name,
                "recorded_status": recorded_status,
                "changing_platform": self.request.session.pop("changing_platform", False),
                "multiple_platforms_exist": multiple_platforms_exist
            })

        return context

    def form_valid(self, form):
        form_data = form.cleaned_data
        user_id = self.request.user.id
        game_dict = self.kwargs.get("game_dict")
        game_id, game_name, cover_url = game_dict["id"], game_dict["name"], game_dict["cover_url"]

        update_mode = form_data["update_mode"]
        if not update_mode:
            return redirect('game-info', game_id=game_id)
        if update_mode == "add":
            try:
                backlog.get(game_id=game_id, user_id=user_id)
            except BackloggedGamesModel.DoesNotExist:
                status_name = "Now Playing" if form_data["now_playing"] else "backlog"
                status_id = 2 if status_name == "Now Playing" else 1
                platform_id, platform_name = form_data["platform"].split(sep=",")

                if platform_id == "203":
                    platform_id = "170"

                backlog.create(user_id=user_id,
                               game_id=game_id, game_name=game_name,
                               cover_url=cover_url,
                               platform_id=platform_id, platform_name=platform_name,
                               status_name=status_name, status_id=status_id,
                               date_added=datetime.today().date())
        else:
            existing_game_entry = backlog.get(game_id=game_id, user_id=user_id)
            if update_mode == "move":
                new_status_name = "Now Playing" if existing_game_entry.status_name == "backlog" else "backlog"
                new_status_id = 2 if new_status_name == "Now Playing" else 1
                existing_game_entry.status_name, existing_game_entry.status_id = new_status_name, new_status_id
                existing_game_entry.save()
            elif update_mode == "change_platform":
                self.request.session["changing_platform"] = True
                return redirect('game-info', game_id=game_id)
            elif update_mode == "platform_update":
                new_platform_id, new_platform_name = form_data["platform"].split(sep=",")

                if new_platform_id == "203":
                    new_platform_id = "170"

                existing_game_entry.platform_id, existing_game_entry.platform_name = new_platform_id, new_platform_name
                existing_game_entry.save()
            elif update_mode == "remove":
                existing_game_entry.delete()

        return redirect("backlog")


class AccountSettingsView(LoginRequiredMixin, TemplateView):
    template_name = "accountsettings.html"


class ChangeUsernameView(LoginRequiredMixin, UpdateView):
    model = User
    fields = ["username"]
    success_url = "/settings"
    template_name = "changeusername.html"

    def get_object(self, queryset=None):
        return User.objects.get(id=self.request.user.id)


class ChangeUserPasswordView(PasswordChangeView):
    template_name = "changepassword.html"
    success_url = "/settings"


class ChangeTimezoneView(FormView):
    success_url = "/settings"
    template_name = "changetimezone.html"
    form_class = TimezoneUpdateForm

    def get_initial(self):
        initial = super().get_initial()
        initial["timezone"] = timezones.filter(user_id=self.request.user.id).values_list("timezone", flat=True)[0]

        return initial

    def form_valid(self, form):
        form_data = form.cleaned_data
        existing_timezone_entry = timezones.get(user_id=self.request.user.id)
        existing_timezone_entry.timezone = form_data["timezone"]
        existing_timezone_entry.save()

        return redirect("settings")


class DeleteAccountPromptView(LoginRequiredMixin, TemplateView):
    template_name = "deleteaccount.html"


class AccountDeletionView(LoginRequiredMixin, DeleteView):
    model = User
    success_url = "/"

    def get_object(self, queryset=None):
        return self.request.user


class AdminRedirectView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        if self.request.user.is_staff:
            return redirect(f"/{os.getenv('ADMIN_URL')}")
        else:
            return render(request, template_name="adminredirect.html")


class AboutView(TemplateView):
    template_name = "about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["version"] = helpers.get_latest_github_release()

        return context


class SoftwareLicensesView(TemplateView):
    template_name = "licenses.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["licenses"] = json.load(open("miscellaneous/licenses.json"))

        return context

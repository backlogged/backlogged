"""backlogger URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path
from strgen import StringGenerator as strgen

from app.views import *

os.environ["ADMIN_URL"] = strgen("[\w\d]{20}").render()

urlpatterns = [
    path(f'{os.getenv("ADMIN_URL")}/', admin.site.urls),
    path('admin/', AdminRedirectView.as_view(), name='admin'),
    path('', HomePageView.as_view(), name='home'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', SignInView.as_view(), name='signin'),
    path('logout/', LogoutView.as_view(), name='signout'),
    path('backlog/', BacklogView.as_view(), name='backlog'),
    path('backlog/search/?page=<int:page>', BacklogView.as_view(), name='backlog-search'),
    path('backlog/games/add-game/', AddGameSearchResultsView.as_view(), name='add-game'),
    path('backlog/games/add-game/page=<int:page>/', AddGameSearchResultsView.as_view()),
    path('backlog/games/id=<int:game_id>/', GameInfoView.as_view(), name='game-info'),
    path('backlog/games/add-game/search/', AddGameSearchView.as_view(), name='add-game-search'),
    path('settings/', AccountSettingsView.as_view(), name='settings'),
    path('settings/change-username/', ChangeUsernameView.as_view(), name='change-username'),
    path('settings/change-password/', ChangeUserPasswordView.as_view(), name='change-password'),
    path('settings/delete-account/', DeleteAccountPromptView.as_view(), name='delete-account-prompt'),
    path('settings/delete-account/no-like-actually-delete-my-account', AccountDeletionView.as_view(),
         name='delete-account-real'),
    path('about/', AboutView.as_view(), name='about'),
    path('about/licenses/', SoftwareLicensesView.as_view(), name='licenses'),
]

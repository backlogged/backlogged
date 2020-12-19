from django.shortcuts import redirect


class HerokuRedirectMixin:
    def dispatch(self, request, *args, **kwargs):
        heroku_url = "backlogger-project.herokuapp.com"
        absolute_uri = request.build_absolute_uri()
        if heroku_url in absolute_uri:
            redirect_url = absolute_uri.replace(heroku_url, "backlogged.games")
            return redirect(redirect_url, permanent=True)

        return super().dispatch(request, *args, **kwargs)

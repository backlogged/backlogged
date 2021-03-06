"""
Custom middleware.
"""

from django.shortcuts import redirect


class HerokuRedirectMiddleware:
    """
    Sends browsers attempting to access Backlogged via its Heroku domain
    an HTTP 301 Moved Permanently response code and redirects them to https://backlogged.games.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        heroku_url = "backlogger-project.herokuapp.com"
        absolute_uri = request.build_absolute_uri()
        if heroku_url in absolute_uri:
            redirect_url = absolute_uri.replace(heroku_url, "backlogged.games")
            return redirect(redirect_url, permanent=True)

        return response

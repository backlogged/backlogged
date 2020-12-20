import os
import re
from operator import itemgetter

import arrow
import requests
from django.http import QueryDict, HttpRequest
from github import Github
from github.GithubException import UnknownObjectException
from igdb.igdbapi_pb2 import GameResult
from igdb.wrapper import IGDBWrapper

from app.models import UserTimezoneModel


def igdb_request(query: str):
    """
    Sends an API request to IGDB's Games endpoint (https://api-docs.igdb.com/#game).
    @param query: The body of the API request.
    @return: A GameResult object containing the contents of IGDB's response.
    """
    wrapper = IGDBWrapper(client_id=os.getenv("IGDB_CLIENT_ID"), auth_token=os.getenv("IGDB_AUTH_TOKEN"))
    results = GameResult()
    response = wrapper.api_request(endpoint='games.pb', query=query)

    results.ParseFromString(response)
    return results


def get_search_view_dicts(search: str, offset: int = 0):
    """
    Gets game information dictionaries for AddGameSearchResultsView().
    @param search: The search query to send to IGDB, determined by user input into an on-site search form.
    @param offset: Tells IGBD how many results to skip. This value is calculated in AddGameSearchResultsView() and used
    for pagination.
    @return: A list of dictionaries containing information about the games retrieved from IGDB.
    """
    game_info_dicts = []

    results = igdb_request(query=f'search "{search}";'
                                 f'fields name, cover.url, platforms;'
                                 f'where category = 0;'
                                 f'offset {offset};'
                                 f'limit 50;')

    for game in results.games:
        if game.cover.url and game.platforms:
            game_dict = {
                "id": game.id,
                "name": game.name,
                "cover_url": f"https:{game.cover.url}".replace("t_thumb", "t_cover_big")
            }

            game_info_dicts.append(game_dict)

    return game_info_dicts


def get_game_info_dict(game_id: int):
    """
    Gets game information dictionary for GameInfoView().
    @param game_id: The game's unique identifier on IGDB.
    @return: A dictionary containing information about the game identified by game_id.
    """
    results = igdb_request(
        query=f'fields name, url, cover.url, summary, platforms.name,'
              f'involved_companies.company.name, involved_companies.developer,'
              f'involved_companies.publisher;'
              f'where id = {game_id};'
    )

    game = results.games[0]

    game_dict = {
        "id": game.id,
        "name": game.name,
        "igdb_url": game.url,
        "cover_url": f"https:{game.cover.url}".replace("t_thumb", "t_cover_big"),
        "summary": "",
        "platforms": [],
        "involved_companies": set(),
    }

    for company in game.involved_companies:
        if company.developer or company.publisher:
            game_dict["involved_companies"].add(company.company.name)

    def platform_handler(platforms: list):
        """
        Manages special cases for game platforms.
        @param platforms: A list of platforms on which the game uniquely identified by game_id is available.
        @return: A list of dictionaries containing each platform's name and unique identifier on IGDB.
        """
        platform_dicts = []

        for platform in platforms:
            platform_replacements = {
                # Replacing name: name to replace
                "Microsoft Windows (PC)": ["PC (Microsoft Windows)"],
                "macOS": ["Mac"],
                "Xbox Series X|S": ["Xbox Series"],
                "Stadia": ["Google Stadia"],
                "NES": ["Nintendo Entertainment System (NES)"],
                "SNES": ["Super Nintendo Entertainment System (SNES)"],
                "Famicom": ["Family Computer Disk System"]
            }

            platform_name = platform.name
            for replacement, flags in platform_replacements.items():
                if platform_name in flags:
                    platform_name = replacement

            platform_dicts.append({"platform_id": platform.id, "platform_name": platform_name})
            platform_dicts.sort(key=itemgetter("platform_name"))

        return platform_dicts

    def format_summary(summary: str, truncated: bool = False):
        """
        Enforces pretty-printing and reasonable length restrictions for game summaries retrieved from IGDB.
        @param summary: The IGDB summary of the game uniquely identified by game_id.
        @param truncated: Identifies whether or not the passed-in summary was truncated for being longer than the
        maximum summary length (200 characters).
        @return: A string containing the formatted summary.
        """
        # noinspection PyTypeChecker
        platform_names = (platform["platform_name"] for platform in game_dict["platforms"])
        length_controller = len(
            max(game_dict["name"], ", ".join(game_dict["involved_companies"]), max(platform_names, key=len), key=len)
        )
        max_summary_line_length = 45 if length_controller < 45 else length_controller + 5
        newlines = 200 // max_summary_line_length
        summary = re.sub("^\W+", "", summary)
        split_summary = list(summary)

        while "\n" in split_summary:
            split_summary.remove("\n")

        insertion_skips = 0
        for i in range(1, newlines + 1):
            try:
                index = split_summary.index(" ", max_summary_line_length + insertion_skips)
                split_summary.insert(index, "\n")
                split_summary.pop(index + 1)
                insertion_skips = index
            except ValueError:
                break

        if truncated:
            try:
                index = split_summary.index(" ", -4)
                split_summary.pop(index)
            except ValueError:
                try:
                    index = split_summary.index("\n", -4)
                    split_summary.pop(index)
                except ValueError:
                    pass

        return "".join(split_summary)

    game_dict["platforms"].extend(platform_handler(game.platforms))

    if len(game.summary) <= 200:
        game_dict["summary"] = format_summary(game.summary)
    else:
        game_dict["summary"] = format_summary(game.summary[:200] + "...", truncated=True)

    return game_dict


def get_latest_github_release():
    """
    Gets the name of the most recent release tag from Backlogged's GitHub repository.
    @return: A string containing the name of the release tag.
    """
    github = Github(os.getenv("GITHUB_TOKEN"))
    repo = github.get_repo(os.getenv("GITHUB_REPO"))

    try:
        release = repo.get_latest_release()
        return release.tag_name
    except UnknownObjectException:
        return ""


def pagination_helper(page: int, last_page: int):
    """
    Provides pagination assistance for BacklogVIew().
    @param page: The number of the page currently being viewed by the user.
    @param last_page: The number of the last page in the user's backlog.
    @return: A range of page numbers to be displayed on the backlog's paginator.
    """
    if last_page > 5:
        if page > 3:
            end = min(page + 2, last_page)
            start = page - 2 if end != last_page else last_page - 4
            page_range = range(start, end + 1)
        else:
            page_range = range(1, 6)
    else:
        page_range = range(1, last_page + 1)

    return page_range


def request_constructor(querydict: QueryDict):
    """
    Assists in maintaining backlog search and sort parameters throughout pagination.
    @param querydict: A Django QueryDict object.
    @return: A string containing the request parameters of the search or sort query.
    """
    request = "?"
    for key, value in querydict.items():
        if key != "page":
            request += f"{key}={value}&"

    return request


def get_local_date(request: HttpRequest, use_api: bool):
    """
    Gets the current date in the user's timezone for BacklogView().
    @param request: A Django HttpRequest object.
    @param use_api: If True, this function will determine the user's timezone by making an API request with the user's
    IP address to http://ipwhois.app. If False, this function will retrieve the user's timezone from UserTimezoneModel.
    @return: A date object representing the user's local date.
    """
    timezones = UserTimezoneModel.objects

    def get_ip_address():
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[-1].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    if use_api:
        ip_address = get_ip_address()
        geo_info = requests.get(f"http://ipwhois.app/json/{ip_address}").json()
        user_timezone = geo_info["timezone"]
        timezones.create(user_id=request.user.id, timezone=user_timezone)
    else:
        user_timezone = timezones.filter(user_id=request.user.id).values_list("timezone", flat=True)[0]

    utc = arrow.utcnow()
    local_date = utc.to(user_timezone).date()

    return local_date

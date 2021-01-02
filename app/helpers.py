"""
Miscellaneous utility functions gathered in one place for ease of maintenance and
cross-module use.
"""

import base64
import os
import re
import string
import urllib.parse
import uuid

import arrow
import requests
from django.core.files.base import ContentFile
from django.http import HttpRequest, QueryDict
from igdb.igdbapi_pb2 import GameResult, PlatformResult
from igdb.wrapper import IGDBWrapper

import app.models as models


def igdb_request(endpoint: str, query: str):
    """
    Sends an API request to IGDB (https://api-docs.igdb.com/).
    @param endpoint: The endpoint to send the request to.
    @param query: The body of the API request.
    @return: An object containing the contents of IGDB's response.
    """
    result_types = {
        "games": GameResult(),
        "platforms": PlatformResult()
    }

    wrapper = IGDBWrapper(client_id=os.getenv("IGDB_CLIENT_ID"), auth_token=os.getenv("IGDB_AUTH_TOKEN"))
    results = result_types[endpoint]
    response = wrapper.api_request(endpoint=f'{endpoint}.pb', query=query)

    results.ParseFromString(response)
    return results


def get_search_view_dicts(search: str, user_id: str, offset: int = 0):
    """
    Gets game information dictionaries for AddGameSearchResultsView.
    @param search: The search query to send to IGDB, determined by user input into an on-site search form.
    @param offset: Tells IGBD how many results to skip. This value is calculated in AddGameSearchResultsView() and used
    for pagination.
    @param user_id: The ID of a user.
    @return: A list of dictionaries containing information about the games retrieved from IGDB.
    """
    game_info_dicts = []

    results = igdb_request(endpoint='games', query=f'search "{search}";'
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

            try:
                backlog = models.BackloggedGame.objects
                backlogged = backlog.get(game_id=game.id, user_id=user_id)
            except models.BackloggedGame.DoesNotExist:
                pass
            else:
                game_dict["status_id"] = backlogged.status_id

            game_info_dicts.append(game_dict)

    return game_info_dicts


# noinspection PyUnboundLocalVariable
def get_game_info_dict(game_id: int, mode: str, user_id: int):
    """
    Gets game information dictionary for GameInfoView.
    @param game_id: The game's unique identifier.
    @param mode: Defines which kind of game dictionary to get ("igdb" for games on IGDB or
    "custom" for games created by a user).
    @param user_id: The ID of a user.
    @return: A dictionary containing information about the game identified by game_id.
    """

    game_dict = {}

    try:
        backlogged = models.BackloggedGame.objects.get(game_id=game_id, user_id=user_id)
    except models.BackloggedGame.DoesNotExist:
        pass
    else:
        game_dict["status_id"] = backlogged.status_id

    if mode == "igdb":
        results = igdb_request(
            endpoint='games',
            query=f'fields name, url, cover.url, summary, platforms.name,'
                  f'involved_companies.company.name, involved_companies.developer,'
                  f'involved_companies.publisher;'
                  f'where id = {game_id};'
        )

        game = results.games[0]

        game_dict.update({
            "id": game.id,
            "name": game.name,
            "cover_url": f"https:{game.cover.url}".replace("t_thumb", "t_cover_big"),
            "platforms": [],
            "involved_companies": "",
            "is_custom": False
        })

        companies = set()
        for company in game.involved_companies:
            if company.developer or company.publisher:
                companies.add(company.company.name)

        game_dict["involved_companies"] = ", ".join(companies)

        game_dict["platforms"].extend(platform_handler(game.platforms))
        game_dict.update(format_summary(game.summary, game_dict))

    if mode == "custom":
        game_dict.update({
            "id": backlogged.game_id,
            "name": backlogged.game_name,
            "cover_url": backlogged.cover_url,
            "involved_companies": backlogged.custom_data.involved_companies,
            "is_custom": True,
            "add_str": f"this game is already in your {backlogged.status_name} for {backlogged.platform_name}."
        })

        game_dict.update(format_summary(backlogged.custom_data.summary, game_dict))

    return game_dict


def platform_getter(platform_id=None):
    """
    Gets platform information from IGDB.
    @param platform_id: Optional. Including this parameter narrows things down to a single platform uniquely identified
    by its value.
    @return: A list of dictionaries containing names and unique identifiers for platforms on IGDB.
    """
    if platform_id:
        query = f'fields name;' \
                f'where id = {platform_id}'
    else:
        query = 'fields name;' \
                'limit 500;'

    results = igdb_request(endpoint='platforms', query=query)

    return platform_handler(results.platforms)


def platform_handler(platforms: list):
    """
    Identifies and eliminates duplicate platforms in IGDB results and enforces specific naming conventions for a small
    handful of platforms.
    @param platforms: A list of game platforms.
    @return: A list of dictionaries containing each platform's name and unique identifier on IGDB.
    """
    platform_dicts = []

    platform_name_replacements = {
        # Replacing name: name to replace
        "Microsoft Windows (PC)": ["PC (Microsoft Windows)"],
        "macOS": ["Mac"],
        "Xbox Series X|S": ["Xbox Series"],
        "Stadia": ["Google Stadia"],
        "NES": ["Nintendo Entertainment System (NES)"],
        "SNES": ["Super Nintendo Entertainment System (SNES)"],
        "Famicom": ["Family Computer Disk System", "Family Computer (FAMICOM)"]
    }

    platform_id_replacements = {
        # Replacing id: id to replace
        "170": [203],  # Google Stadia
        "99": [51],  # Famicom
    }

    for platform in platforms:
        platform_name = platform.name
        for replacement, flags in platform_name_replacements.items():
            if platform_name in flags:
                platform_name = replacement

        platform_id = platform.id
        for replacement, flags in platform_id_replacements.items():
            if platform_id in flags:
                platform_id = int(replacement)

        platform_dicts.append({"platform_id": platform_id, "platform_name": platform_name})

    platform_dicts.sort(key=lambda k: k["platform_name"].casefold())

    return platform_dicts


def format_summary(summary: str, game_dict: dict):
    """
    Enforces pretty-printing and reasonable length restrictions for game summaries.
    @param summary: The summary of a game.
    @param game_dict: A dictionary of information about a game.
    @return: A string containing the formatted summary.
    """
    summaries = {"full_summary": None}

    if len(summary) >= 200:
        summaries["full_summary"] = summary

    try:
        platform_names = (platform["platform_name"] for platform in game_dict["platforms"])
    except KeyError:
        length_controller = len(
            max(game_dict["name"], game_dict["involved_companies"], game_dict["add_str"], key=len)
        )
    else:
        length_controller = len(
            max(game_dict["name"], game_dict["involved_companies"], max(platform_names, key=len), key=len)
        )

    max_summary_line_length = 45 if length_controller < 45 else length_controller + 5
    newlines = 200 // max_summary_line_length
    summary = re.sub("^\W+", "", summary)
    split_summary = list(summary[:200])

    if summaries["full_summary"]:
        split_summary.extend(list("..."))

    while "\n" in split_summary:
        split_summary.remove("\n")

    insertion_skips = 0
    for i in range(1, newlines + 1):
        try:
            index = split_summary.index(" ", max_summary_line_length + insertion_skips)
        except ValueError:
            index = max_summary_line_length + insertion_skips

        try:
            split_summary.insert(index, "\n")
            split_summary.pop(index + 1)
            insertion_skips = index
        except IndexError:
            break

    try:
        while split_summary[-4] in string.punctuation + string.whitespace:
            split_summary.pop(-4)
    except IndexError:
        pass

    if summaries["full_summary"]:
        summaries["short_summary"] = "".join(split_summary)
    else:
        summaries["full_summary"] = "".join(split_summary)

    return summaries


# noinspection PyTypeChecker
def create_custom_game_dict(cg_data: dict):
    """
    Prepares data for CustomGameForm for further processing.
    @param cg_data: Cleaned data from a valid CustomGameForm.
    @return: A dictionary of custom game data.
    """
    game_dict = {}

    game_dict.update({
        "game_id": f"custom-{uuid.uuid4()}",
        "name": cg_data["game_name"],
        "status_id": 1 if not cg_data["now_playing"] else 2,
        "status_name": "backlog" if not cg_data["now_playing"] else "Now Playing",
        "involved_companies": cg_data["involved_companies"],
    })

    game_dict["recorded_platform_id"], game_dict["recorded_platform_name"] = cg_data["platform"].split(sep=",")
    game_dict["add_str"] = f"add this game to your {game_dict['status_name']} " \
                           f"for {game_dict['recorded_platform_name']}?"

    game_dict.update(format_summary(cg_data["summary"], game_dict))

    if not cg_data["cover_img"]:
        with open(f"miscellaneous{os.sep}defaultcover.txt") as file:
            game_dict["cover_img"] = file.read()
    else:
        game_dict["cover_img"] = base64.b64encode(cg_data["cover_img"].read()).decode("ascii")

    return game_dict


def create_custom_cover_file(ascii_str: str, name: str):
    """
    Creates a file containing uploaded cover art for a custom game.
    @param ascii_str: A string representing the ASCII decoding of the image file.
    @param name: The name to give the file.
    @return: A ContentFile object containing the uploaded cover art.
    """
    file = ContentFile(base64.b64decode(ascii_str))
    file.name = name

    return file


def pagination_helper(page: int, last_page: int):
    """
    Provides pagination assistance for BacklogView.
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


def request_constructor(querydict: QueryDict, excluded=None):
    """
    Constructs request parameter strings from dictionaries.
    @param querydict: A dictionary of request parameters.
    @param excluded: A list of parameters to exclude during construction.
    @return: A string containing the request parameters of the search or sort query.
    """

    if excluded is None:
        excluded = []

    params = {key: value for key, value in querydict.items() if key not in excluded}

    request = f"?{urllib.parse.urlencode(params)}"

    return request


def get_local_date(request: HttpRequest, use_api: bool):
    """
    Gets the current date in the user's timezone for BacklogView.
    @param request: A Django HttpRequest object.
    @param use_api: If True, this function will determine the user's timezone by making an API request with the user's
    IP address to http://ipwhois.app. If False, this function will retrieve the user's timezone from UserTimezoneModel.
    @return: A date object representing the user's local date.
    """
    timezones = models.UserTimezone.objects

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

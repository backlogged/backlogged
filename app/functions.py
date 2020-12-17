import os
import re

from igdb.igdbapi_pb2 import GameResult, PlatformResult
from igdb.wrapper import IGDBWrapper


def igdb_request(endpoint, query):
    result_types = {
        "games": GameResult(),
        "platforms": PlatformResult()
    }

    wrapper = IGDBWrapper(client_id=os.getenv("IGDB_CLIENT_ID"), auth_token=os.getenv("IGDB_AUTH_TOKEN"))
    results = result_types[endpoint]
    response = wrapper.api_request(endpoint=f'{endpoint}.pb', query=query)

    results.ParseFromString(response)
    return results


def get_search_view_dicts(search, offset=0):
    game_info_dicts = []

    results = igdb_request(endpoint='games',
                           query=f'search "{search}";'
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


def get_game_info_dict(game_id):
    results = igdb_request(
        endpoint='games',
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

    def platform_handler(platforms):
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

            return platform_dicts

    def format_summary(summary, truncated=False):
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
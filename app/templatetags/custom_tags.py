"""
Custom template tags and filters.
"""

import os

from django import template
from github import Github
from github.GithubException import UnknownObjectException

register = template.Library()


@register.simple_tag(name="github_repo")
def get_github_repo():
    """
    Returns the URL to Backlogged's GitHub Repository.
    @return: The URL to Backlogged's GitHub Repository.
    """
    return "https://github.com/backlogged/backlogged-new"


@register.simple_tag(name="github_release")
def get_latest_github_release(mode: str):
    """
    Gets the tag name or description of the most recent release from Backlogged's GitHub repository
    (https://github.com/backlogged/backlogged).
    @param mode: "tag" or "body".
    @return: A string containing the tag name or body.
    """
    github = Github(os.getenv("GITHUB_TOKEN"))
    repo = github.get_repo("backlogged/backlogged")

    try:
        release = repo.get_latest_release()
    except UnknownObjectException:
        return ""
    else:
        if mode == "tag":
            return release.tag_name
        elif mode == "body":
            return release.body

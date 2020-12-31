import os

from django import template
from github import Github
from github.GithubException import UnknownObjectException

register = template.Library()


@register.simple_tag(name="github_version")
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

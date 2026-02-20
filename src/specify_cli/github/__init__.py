"""GitHub Projects integration for Specify CLI."""

from .auth import resolve_github_token, validate_token
from .config import GitHubProjectsConfig, load_config, save_config
from .graphql_client import GraphQLClient, GitHubGraphQLError, RateLimitError
from .api import GitHubProjectsAPI, load_api_for_repo
from . import queries
from . import mutations

__all__ = [
    "resolve_github_token",
    "validate_token",
    "GitHubProjectsConfig",
    "load_config",
    "save_config",
    "GraphQLClient",
    "GitHubGraphQLError",
    "RateLimitError",
    "GitHubProjectsAPI",
    "load_api_for_repo",
    "queries",
    "mutations",
]

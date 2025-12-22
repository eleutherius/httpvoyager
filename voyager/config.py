from .models import GraphQLTabSpec

DEFAULT_ENDPOINT = "https://nginx.pm-repository.orb.local/graphql"
DEFAULT_QUERY = ""  # Empty by default; enter your own query.
DEFAULT_VARIABLES = "{}\n"

DEFAULT_TABS = [
    GraphQLTabSpec(
        id="main",
        title="Voyager",
        endpoint=DEFAULT_ENDPOINT,
        query=DEFAULT_QUERY,
        variables=DEFAULT_VARIABLES,
    )
]

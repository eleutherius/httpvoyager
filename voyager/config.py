from .models import GraphQLTabSpec, HttpTabSpec, WebSocketTabSpec

DEFAULT_ENDPOINT = "https://nginx.pm-repository.orb.local/graphql"
DEFAULT_QUERY = ""  # Empty by default; enter your own query.
DEFAULT_VARIABLES = "{}\n"
DEFAULT_HTTP_ENDPOINT = "https://httpbin.org/get"
DEFAULT_WS_ENDPOINT = "wss://echo.websocket.events"

DEFAULT_TABS = [
    GraphQLTabSpec(
        id="main",
        title="Voyager",
        endpoint=DEFAULT_ENDPOINT,
        query=DEFAULT_QUERY,
        variables=DEFAULT_VARIABLES,
    )
]

DEFAULT_HTTP_TAB = HttpTabSpec(
    id="http",
    title="HTTP",
    url=DEFAULT_HTTP_ENDPOINT,
    method="GET",
    body="",
    headers="",
    verify_tls=True,
)

DEFAULT_WS_TAB = WebSocketTabSpec(
    id="ws",
    title="WebSocket",
    url=DEFAULT_WS_ENDPOINT,
    message='{"message": "hello"}',
    headers="",
    verify_tls=True,
)

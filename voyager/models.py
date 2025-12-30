from dataclasses import dataclass


@dataclass
class GraphQLTabSpec:
    id: str
    title: str
    endpoint: str
    query: str
    variables: str
    headers: str = ""
    verify_tls: bool = True


@dataclass
class GraphQLResponse:
    status: int
    text: str
    duration_ms: float


@dataclass
class HttpTabSpec:
    id: str
    title: str
    url: str
    method: str = "GET"
    body: str = ""
    headers: str = ""
    verify_tls: bool = True


@dataclass
class WebSocketTabSpec:
    id: str
    title: str
    url: str
    message: str = ""
    headers: str = ""
    verify_tls: bool = True

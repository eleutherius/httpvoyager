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

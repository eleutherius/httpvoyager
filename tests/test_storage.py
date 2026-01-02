import json

from voyager.models import GraphQLTabSpec
from voyager.storage import load_last_state, save_state, _config_path


def _make_spec(endpoint: str) -> GraphQLTabSpec:
    return GraphQLTabSpec(
        id="main",
        title="Voyager",
        endpoint=endpoint,
        query="{}",
        variables="{}",
    )


def test_load_defaults_when_file_missing(tmp_config_dir):
    spec = _make_spec("http://default")
    loaded = load_last_state(spec, section="graphql")
    assert loaded.endpoint == "http://default"


def test_save_and_load_roundtrip(tmp_config_dir):
    spec = _make_spec("http://saved")
    save_state(spec, section="graphql")

    base_spec = _make_spec("http://default")
    loaded = load_last_state(base_spec, section="graphql")
    assert loaded.endpoint == "http://saved"
    assert loaded.title == base_spec.title  # fields preserved


def test_load_handles_broken_json(tmp_config_dir):
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{broken", encoding="utf-8")

    spec = _make_spec("http://default")
    loaded = load_last_state(spec, section="graphql")
    assert loaded.endpoint == "http://default"


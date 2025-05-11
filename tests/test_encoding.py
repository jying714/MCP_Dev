import sys
import os
import json
import pytest
import requests

# Ensure the 'src' directory is on sys.path to import our API modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from api.encoding import save_to_maxroll

class DummyResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

class DummySession:
    def __init__(self):
        self.last_get_url = None
        self.last_post_args = None

    def get(self, url):
        self.last_get_url = url
        return DummyResponse({}, 200)

    def post(self, url, json=None, headers=None, timeout=None):
        self.last_post_args = {
            'url': url,
            'json': json,
            'headers': headers,
            'timeout': timeout
        }
        return DummyResponse({'id': 'abc123'}, 200)

@pytest.fixture(autouse=True)
def patch_session(monkeypatch):
    dummy = DummySession()
    monkeypatch.setattr('api.encoding.requests.Session', lambda: dummy)
    return dummy


def test_save_to_maxroll_returns_url(patch_session):
    node_list = [10, 20, 30]
    version_id = 401
    char_class = 'DexFour'
    ascendancy = 'Deadeye'
    url = save_to_maxroll(
        node_list, version_id, char_class, ascendancy,
        name='TestBuild', public=True, folder=5
    )
    assert url == 'https://maxroll.gg/poe2/passive-tree/abc123'

    # Verify session.get was called to seed cookies
    assert patch_session.last_get_url == 'https://maxroll.gg/poe2/pob/'

    # Verify POST arguments
    post = patch_session.last_post_args
    assert post['url'] == 'https://planners.maxroll.gg/profiles/poe2'
    payload = post['json']
    assert payload['name'] == 'TestBuild'
    assert payload['public'] == 1
    assert payload['folder'] == 5
    assert payload['type'] == 'pob'
    # The data field should be a JSON string containing passive_tree
    data_dict = json.loads(payload['data'])
    assert data_dict['passive_tree']['version'] == 401
    assert data_dict['passive_tree']['charClass'] == 'DexFour'
    assert data_dict['passive_tree']['ascendancy'] == 'Deadeye'
    assert data_dict['passive_tree']['variants'][0]['history'] == node_list


def test_save_to_maxroll_raises_on_error(monkeypatch):
    class ErrorSession(DummySession):
        def post(self, *args, **kwargs):
            return DummyResponse({'error': 'fail'}, 500)
    monkeypatch.setattr('api.encoding.requests.Session', lambda: ErrorSession())

    with pytest.raises(requests.HTTPError):
        save_to_maxroll([1], 401, 'DexFour', '', name=None, public=False, folder=0)

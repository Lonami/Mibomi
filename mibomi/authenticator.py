"""
Helper module to authenticate a client at Mojang servers.

See https://wiki.vg/Authentication.
"""
import requests

AUTH_URL = 'https://authserver.mojang.com'
SESSION_URL = 'https://sessionserver.mojang.com'


class Profile:
    """
    Represents a profile, with `id`, `name` and `legacy` flag.
    """
    def __init__(self, data):
        self.id = data['id']
        self.name = data['name']
        self.legacy = data.get('legacy', False)


class AuthenticateResponse:
    """
    Represents the response to the authenticate API call, which contains
    `access_token`, `client_token`, the `selected_profile` and a list of
    `available_profiles`.
    """
    def __init__(self, data):
        self.access_token = data['accessToken']
        self.client_token = data['clientToken']
        self.selected_profile = Profile(data['selectedProfile'])
        self.available_profiles = [
            Profile(x) for x in data['availableProfiles']]


def authenticate(username, password, token=None):
    """
    Authenticates the given username (or email address) with the
    correct account password.

    If a token for the client is given, it generally should be a
    persistent ``str(uuid.uuid4())`` that is able to identify the
    client. Using an empty token will cause previous ones to be
    invalidated, and the server will generate and return one.
    """
    data = requests.post(AUTH_URL + '/authenticate', json=dict(
        agent=dict(
            name='Minecraft',
            version=1
        ),
        username=username,
        password=password,
        **(dict(clientToken=token) if token else {}),
        # requestUser=True
    )).json()
    if 'error' in data:
        raise ValueError('{}: {}'.format(data['error'], data['errorMessage']))
    else:
        return AuthenticateResponse(data)


def session_join(access_token, profile_id, server_hash):
    """
    Joins a Minecraft online session. Returns ``True`` on success.
    """
    return requests.post(SESSION_URL + '/session/minecraft/join', json=dict(
        accessToken=access_token,
        selectedProfile=profile_id,
        serverId=server_hash
    )).status_code == 204

"""Shared HubSpot auth — reads API key from ~/.hubspot-ops.env.

Supports multiple key types:
  - Private app token (pat-na1-xxx) → Bearer auth
  - OAuth access token → Bearer auth
  - Legacy API key (hapikey) → query param auth (deprecated, limited API support)

Auto-detects format. Checks env vars first, then .env file.
Accepts any of: HUBSPOT_API_KEY, HUBSPOT_ACCESS_TOKEN, HUBSPOT_PRIVATE_APP_TOKEN.
"""

import os

_ENV_PATH = os.path.expanduser("~/.hubspot-ops.env")
_KEY_NAMES = ["HUBSPOT_API_KEY", "HUBSPOT_ACCESS_TOKEN", "HUBSPOT_PRIVATE_APP_TOKEN"]


def _load_env_file():
    """Load key=value pairs from .env file into os.environ."""
    if not os.path.exists(_ENV_PATH):
        return
    with open(_ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            os.environ[key.strip()] = value.strip()


def load_hubspot_key():
    """Return the HubSpot API key/token from env vars or .env file."""
    # Check env vars first
    for name in _KEY_NAMES:
        val = os.environ.get(name)
        if val:
            return val

    # Fall back to .env file
    _load_env_file()
    for name in _KEY_NAMES:
        val = os.environ.get(name)
        if val:
            return val

    raise RuntimeError(
        "No HubSpot key found. Create ~/.hubspot-ops.env with:\n"
        "  HUBSPOT_API_KEY=your-key-here\n"
        "\nAccepted env var names: " + ", ".join(_KEY_NAMES)
    )


def is_bearer_token(key):
    """Detect whether the key should be used as a Bearer token vs query param."""
    # Private app tokens start with pat-
    # OAuth tokens are typically long alphanumeric strings
    # Legacy API keys are shorter UUID-style strings (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
    if key.startswith("pat-"):
        return True
    # Legacy hapikeys are 36-char UUIDs with dashes
    if len(key) == 36 and key.count("-") == 4:
        return False
    # Default to Bearer — most modern keys use it
    return True


def get_headers():
    """Return auth headers for HubSpot API calls."""
    key = load_hubspot_key()
    headers = {"Content-Type": "application/json"}
    if is_bearer_token(key):
        headers["Authorization"] = f"Bearer {key}"
    return headers


def get_auth_params():
    """Return query params for legacy API key auth. Empty dict for Bearer."""
    key = load_hubspot_key()
    if not is_bearer_token(key):
        return {"hapikey": key}
    return {}


BASE_URL = "https://api.hubapi.com"

"""Shared Salesforce auth — reads credentials from ~/.sf-attribution.env."""

import os

_ENV_PATH = os.path.expanduser("~/.sf-attribution.env")


def load_sf_credentials():
    """Return (client_id, client_secret, instance_url) from env vars or .env file."""
    client_id = os.environ.get("SALESFORCE_CLIENT_ID")
    client_secret = os.environ.get("SALESFORCE_CLIENT_SECRET")
    instance_url = os.environ.get("SALESFORCE_INSTANCE_URL")

    if client_id and client_secret and instance_url:
        return client_id, client_secret, instance_url

    if os.path.exists(_ENV_PATH):
        with open(_ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip()

        client_id = os.environ.get("SALESFORCE_CLIENT_ID")
        client_secret = os.environ.get("SALESFORCE_CLIENT_SECRET")
        instance_url = os.environ.get("SALESFORCE_INSTANCE_URL")

        if client_id and client_secret and instance_url:
            return client_id, client_secret, instance_url

    raise RuntimeError(
        "No SF credentials found. Create ~/.sf-attribution.env with:\n"
        "  SALESFORCE_CLIENT_ID=...\n"
        "  SALESFORCE_CLIENT_SECRET=...\n"
        "  SALESFORCE_INSTANCE_URL=..."
    )

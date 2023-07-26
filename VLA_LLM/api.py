"""Methods for accessing the Funnel API."""

import requests

from VLA_LLM import config


def get_community_info(community_id: int):
    """Get community data for given community ID."""
    url = f'https://nestiolistings.com/api/virtualagent/communities/{community_id}/'
    response = requests.get(url, auth=(config.CHUCK_API_KEY, None))

    if response.status_code == 200:
        return response.json()

    return {}

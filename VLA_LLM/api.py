"""Methods for accessing the Funnel API."""

import datetime
import requests
from typing import List

from VLA_LLM import config


def get_community_info(community_id: int):
    """Get community information.

    Args:
        community_id: ID of community

    Returns:
        Community information for provided ID

    """
    url = f'https://nestiolistings.com/api/virtualagent/communities/{community_id}/'
    response = requests.get(url, auth=(config.CHUCK_API_KEY, None))

    if response.status_code == 200:
        return response.json()

    return {}


def schedule_appointment(appt_time: datetime.datetime, client_id: int, group_id: int) -> bool:
    """Attempt to schedule appointment for given time.

    Args:
        appt_time: Time to schedule for
        client_id: ID of client to schedule for
        group_id: ID of group

    Returns:
        Whether scheduling was successful

    """
    url = f"https://nestiolistings.com/api/virtualagent/clients/{client_id}/groups/{group_id}/appointments/"

    data = {
        'appointment': {
            'start': appt_time.isoformat(),
            # hardcode the type of tour for now
            'tour_type': 'guided',
            'is_video_tour': False
        }
    }

    response = requests.post(
        url, json=data, headers={'Content-Type': 'application/json'}, auth=(config.CHUCK_API_KEY, None)
    )

    return response.status_code == 200


def available_appointment_times(appt_date: datetime.datetime, group_id: int, api_key: str) -> List[str]:
    """Get available appointment times on provided date.

    Args:
        appt_date: Date to get available times for
        group_id: ID of group
        api_key: API key to access times for given group ID

    Returns:
        List of available appointment times

    """
    url = f"https://nestiolistings.com/api/v2/appointments/group/{group_id}/available-times/"

    params = {
        "from_date": appt_date.strftime('%Y-%m-%d'),
        "tour_type": "guided"
    }

    response = requests.get(url, params=params, auth=(api_key, ''))
    if response.status_code != 200:
        return []

    return response.json().get('available_times', [])

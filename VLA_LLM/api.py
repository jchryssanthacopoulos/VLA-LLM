"""Methods for accessing the Funnel API."""

import datetime
import requests
from typing import Dict
from typing import List
from typing import Optional

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


def schedule_appointment(appt_time: datetime.datetime, client_id: int, group_id: int) -> Dict:
    """Attempt to schedule appointment for given time.

    Args:
        appt_time: Time to schedule for
        client_id: ID of client to schedule for
        group_id: ID of group

    Returns:
        Response from API

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

    return response.json()


def reschedule_appointment(appt_time: datetime.datetime, appointment_id: int, group_id: int, api_key: str) -> Dict:
    """Reschedule an appointment.

    Args:
        appt_time: Appointment time datetime object
        appointment_id: ID of appointment to reschedule
        group_id: Group to create an appointment with
        api_key: API key corresponding to management company

    Returns:
        Response from API

    """
    url = f"https://nestiolistings.com/api/v2/appointments/{appointment_id}/group/{group_id}/book"

    data = {
        'appointment': {
            'start': appt_time.isoformat()
        }
    }

    response = requests.put(
        url, json=data, headers={'Content-Type': 'application/json'}, auth=(api_key, '')
    )

    return response.json()


def cancel_appointment(appointment_id: int, api_key: str) -> bool:
    """Cancel an appointment.

    Args:
        appointment_id: ID of appointment to cancel
        api_key: API key corresponding to management company

    Returns:
        Whether or not rescheduling was successful

    """
    url = f"https://nestiolistings.com/api/v2/appointments/{appointment_id}"

    response = requests.delete(url, auth=(api_key, ''))

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


def delete_client_preferences(client_id: int):
    """Delete preferences on client's guest card.

    Args:
        client_id: ID of client to delete preferences for

    """
    url = f"https://nestiolistings.com/api/virtualagent/clients/{client_id}/delete-preferences/"

    requests.delete(
        url, headers={'Content-Type': 'application/json'}, auth=(config.CHUCK_API_KEY, '')
    )


def enable_vla(client_id: int, group_id: int):
    """Enable VLA for client.

    Args:
        client_id: ID of client to enable the VLA for
        group_id: Group ID associated with client

    """
    url = f"https://nestiolistings.com/api/virtualagent/clients/{client_id}/groups/{group_id}/enable-vla/"

    requests.put(
        url, json={}, headers={'Content-Type': 'application/json'}, auth=(config.CHUCK_API_KEY, '')
    )


def get_client_appointments(client_id: int, api_key: str) -> List:
    """Get client appointments.

    Args:
        client_id: Client ID
        api_key: API key corresponding to management company with client

    Returns:
        Client appointments (empty if it couldn't be retrieved or if there are no appointments)

    """
    url = f"https://nestiolistings.com/api/v2/clients/{client_id}/appointments"

    response = requests.get(url, headers={'Content-Type': 'application/json'}, auth=(api_key, ''))

    if response.status_code == 200:
        return response.json().get('data', {}).get('appointments', [])

    return []


def update_client(
        client_id: int, move_in_date: Optional[datetime.datetime] = None, layout: Optional[List] = None,
        price_ceiling: Optional[str] = None
):
    """Update client with provided information.

    Args:
        client_id: ID of client to update
        move_in_date: Move-in date to set or update to (if None, do not set)
        layout: List of preferred layout types (if None, do not set)
        price_ceiling: Budget (if None, do not set)

    Returns:
        Response from API

    """
    data = {}

    if move_in_date:
        data['move_in_date'] = move_in_date.strftime('%Y-%m-%d')
    if layout:
        data['layout'] = layout
    if price_ceiling:
        data['price_ceiling'] = price_ceiling

    if not data:
        # no client information was provided, so do not call API
        return {}

    url = f"https://nestiolistings.com/api/virtualagent/clients/{client_id}/edit/"

    response = requests.put(
        url, json=data, headers={'Content-Type': 'application/json'}, auth=(config.CHUCK_API_KEY, '')
    )

    return response.json()


def get_available_units(
        community_id: int, move_in_date: Optional[datetime.datetime] = None, layout: Optional[List] = None,
        price_ceiling: Optional[str] = None
) -> List[Dict]:
    """Get available units matching preferences.

    Args:
        community_id: ID of community
        move_in_date: Move-in date to set or update to (if None, do not set)
        layout: List of preferred layout types (if None, do not set)
        price_ceiling: Budget (if None, do not set)

    Returns:
        List of dictionaries representing available apartments matching preferences

    """
    url = f'https://nestiolistings.com/api/virtualagent/search/{community_id}/listings/'

    params = {}
    if move_in_date:
        params['date_available_before'] = move_in_date.strftime('%Y-%m-%d')
    if price_ceiling:
        params['max_price'] = price_ceiling
    if layout:
        params['layout'] = layout

    response = requests.get(url, params=params, auth=(config.CHUCK_API_KEY, None))

    if not response.ok:
        return []

    return response.json().get('listings', [])

"""Utilities for converting structured community information into text that can be inserted into a prompt."""

import datetime
from typing import Dict
from typing import List


def community_dict_to_prompt(community_dict: Dict) -> str:
    """Convert community dictionary to prompt.

    Args:
        community_dict: Community information

    Returns:
        Prompt

    """
    prompt = f"Building name: {community_dict['building_name']}"

    # community address
    community_building_number = community_dict['building_number']
    community_street = community_dict['street']
    community_city = community_dict['city']
    community_state = community_dict['state']
    community_postal_code = community_dict['postal_code']

    prompt += (
        f"\nLocation: {community_building_number} {community_street}, {community_city}, {community_state} "
        f"{community_postal_code}"
    )

    office_hours = _get_office_hours(community_dict)
    if office_hours:
        prompt += f"\nOffice hours: {office_hours}"

    # parking
    parking_options = community_dict["parking_options"]
    if parking_options:
        prompt += "\nParking options:"
        for idx, option in enumerate(parking_options):
            prompt += f"\n  {idx + 1}. Parking type: {option['parking_type']}\n"
            prompt += f"     Parking fee: ${option['parking_fee']}\n"
            prompt += f"     Parking fee term: {option['parking_fee_term']}\n"
            prompt += f"     Parking notes: {option['parking_notes']}"
    else:
        prompt += "There are no parking options available."

    # pets
    pet_policy = community_dict['pets']
    prompt += f"\nHere is information about whether pets are allowed and how much it costs:"
    prompt += f"\n  Policy: {pet_policy['policy']}"
    if pet_policy['deposit']:
        prompt += f"\n  Extra deposit needed: {pet_policy['deposit']}"
    else:
        prompt += f"\n  Extra deposit for dogs: {pet_policy['deposit_dogs']}"
        prompt += f"\n  Extra deposit for cats: {pet_policy['deposit_cats']}"
    prompt += f"\n  Is deposit refundable?: {'Yes' if pet_policy['deposit_refundable'] else 'No'}"
    if pet_policy['fee']:
        prompt += f"\n  Extra fee needed: {pet_policy['fee']}"
    else:
        prompt += f"\n  Extra fee for dogs: {pet_policy['fee_dogs']}"
        prompt += f"\n  Extra fee for cats: {pet_policy['fee_cats']}"
    if pet_policy['extra_rent']:
        prompt += f"\n  Extra rent needed: {pet_policy['extra_rent']}"
    else:
        prompt += f"\n  Extra rent for dogs: {pet_policy['extra_rent_dogs']}"
        prompt += f"\n  Extra rent for cats: {pet_policy['extra_rent_cats']}"
    prompt += f"\n  Maximum number allowed: {pet_policy['max_allowed']}"
    prompt += f"\n  Maximum weight allowed: {pet_policy['max_weight']}"
    prompt += f"\n  Are there breed restrictions?: {'Yes' if pet_policy['breed_restriction'] else 'No'}"
    prompt += f"\n  Notes about restricted breeds: {', '.join(pet_policy['restrictions'].split())}"
    prompt += f"\n  Extra notes about pets: {pet_policy['notes']}"

    # special offers
    special_offers = community_dict['special_offers']
    if special_offers:
        prompt += f"\nSpecial offers: {special_offers}"

    # utilities
    utilities = community_dict['utilities']
    prompt += (
        "\nThe following is information on utility companies, whether the utility is paid by the tenant or community, "
        "and extra fees:"
    )
    for utility_name in ['electric', 'water', 'cable', 'internet', 'gas', 'trash']:
        utility_val = utilities[utility_name]
        who_pays = 'paid by property' if utility_val['paid_by_property'] else 'paid by tenant'
        prompt += f"\n  {utility_name.capitalize()}: Company is {utility_val['company']}, {who_pays}"
        if utility_val['fees']:
            prompt += f", fee of {utility_val['fees']}"

    # affordable housing
    if community_dict['affordable_housing_offered']:
        prompt += "\nAffordable housing is offered."
    else:
        prompt += "\nAffordable housing is not offered."
    if community_dict['affordable_housing_notes']:
        prompt += f"\nAdditional notes related to affordable housing: {community_dict['affordable_housing_notes']}"

    # application link
    prompt += f"\nThe link to submit an application is: {community_dict['application_url']}"

    # photo request
    prompt += f"\nYou can find photos or videos of the community here: {community_dict['media_page_url']}."

    # features
    prompt += f"\nOffered amenities: {', '.join(k for k, v in community_dict['amenities'].items() if v)}"
    prompt += f"\nUnoffered amenities: {', '.join(k for k, v in community_dict['amenities'].items() if not v)}"
    prompt += f"\nOther apartment features include: {', '.join(community_dict['apartment_features'])}"

    # leasing costs
    leasing_deposit = community_dict['leasing_deposit']
    if not leasing_deposit.startswith('$'):
        leasing_deposit = '$' + leasing_deposit
    leasing_application_fee = community_dict['leasing_application_fee']
    if not leasing_application_fee.startswith('$'):
        leasing_application_fee = '$' + leasing_application_fee
    leasing_administrative_fee = community_dict['leasing_administrative_fee']
    if not leasing_administrative_fee.startswith('$'):
        leasing_administrative_fee = '$' + leasing_administrative_fee

    prompt += "\nSome information about deposits and fees:"
    prompt += f"\n  Leasing deposit: {leasing_deposit}"
    prompt += f"\n  Leasing application fee: {leasing_application_fee}"
    prompt += f"\n  Leasing administrative fee: {leasing_administrative_fee}"

    # leasing terms
    prompt += (
        "\nThe following lease terms are offered, in months: "
        f"{', '.join(str(term) for term in community_dict['leasing_lease_term'])}"
    )

    # video tour
    prompt += f"\nA video of the community can be found here: {community_dict['video_tour_url']}"

    return prompt


def _get_office_hours(community_dict: Dict) -> str:
    """Get office hours message.

    Walks through Monday to Sunday, grouping any consecutive days with the same hours.
    Any days which are closed are included in the last sentence.

    The copy would then look something like this:

        The office is open Monday through Friday from 8 AM to 8 PM and Saturday from 9 AM to 8 PM.
        It is closed on Sunday.

    Args:
        community_dict: Community information
        
    Returns:
        string containing office hours message copy, or an empty string when copy cannot be produced correctly

    """
    consec_same_hours = []  # Current grouping of days with the same office hours
    closed_days = []        # Days which are closed
    office_hours_strs = []  # List of strings which will be built as we walk through groupings
    prev_open = None        # Opening time of previously considered day
    prev_close = None       # Closing time of previously considered day

    # Office hours schedule
    hours_by_day = community_dict.get('hours_of_operation', {})

    for day in hours_by_day:
        open_at = hours_by_day[day]['open_at']
        close_at = hours_by_day[day]['close_at']
        is_closed = hours_by_day[day]['is_closed']

        # Check if the running chain of consecutive days is broken by the current day under consideration
        if is_closed or open_at != prev_open or close_at != prev_close:
            # Form string for all the days in the current grouping
            days_str = _form_string_from_consec_day_grouping(consec_same_hours, prev_open, prev_close)
            if days_str:
                # Add to our list of strings to be added to copy
                office_hours_strs.append(days_str)

            if not is_closed:
                # If the current day is not closed, start our next grouping with this day
                consec_same_hours = [day.capitalize()]
            else:
                # Otherwise start an empty next grouping
                consec_same_hours = []
        else:
            # Current day continues the grouping of consecutive days w/ same hours; append
            consec_same_hours.append(day.capitalize())

        if is_closed:
            # Independently add closed days to their own list
            closed_days.append(day.capitalize())

        # Update prevs before continuing loop
        prev_open = open_at
        prev_close = close_at

    # We may have left some days hanging; create final string if necessary
    if consec_same_hours and not is_closed:
        days_str = _form_string_from_consec_day_grouping(consec_same_hours, prev_open, prev_close)
        if days_str:
            office_hours_strs.append(days_str)

    if not office_hours_strs:
        # No valid strings made; suppress office hours response
        return ''

    # Concatenate list into single string for open days
    message = combine_list_into_displayable_text(office_hours_strs)

    closed_days_msg = ''
    if closed_days:
        # Concatenate list into single string for closed days
        closed_days_str = combine_list_into_displayable_text(closed_days)
        closed_days_msg = f' It is closed on {closed_days_str}.'

    message = 'The office is open ' + message + '.' + closed_days_msg

    return message


def _form_string_from_consec_day_grouping(days: List[str], open_at: str, close_at: str) -> str:
    """Office hours helper function for forming strings from groupings of consecutive days.

    Args:
        days: list of consecutive days with same hours
        open_at: opening time for consecutive days
        close_at: closing time for consecutive days

    Returns:
        string containing office hours information for a consecutive grouping of days, or
            None if any of the parameters evaluate to False

    """
    if days and open_at and close_at:
        # Number of days in grouping determines how days are represented in message
        if len(days) == 1:
            days_str = days[0]
        elif len(days) == 2:
            days_str = days[0] + ' and ' + days[1]
        elif len(days) == 7:
            days_str = 'everyday'
        else:
            # Grouping length between 2 and 7 days
            days_str = days[0] + ' through ' + days[-1]

        # Format opening time to be more human readavble
        readable_open_hour = human_readable_hour(
            # Parse time from string
            datetime.datetime.strptime(open_at, '%H:%M:%S').time(),
            add_am_pm=True,
            add_timezone=True
        )
        # Format closing time to be more human readavble
        readable_close_hour = human_readable_hour(
            # Parse time from string
            datetime.datetime.strptime(close_at, '%H:%M:%S').time(),
            add_am_pm=True,
            add_timezone=True
        )
        return f'{days_str} from {readable_open_hour} to {readable_close_hour}'


def combine_list_into_displayable_text(lst: List, separator: str = 'and') -> str:
    """Combine list into displayable text.

    Args:
        lst: List like ['washer', 'modern cabinets']
        separator: Conjunction used to separate multiple terms (default = 'and')

    Returns:
        String like 'washer and modern cabinets'

    """
    if len(lst) == 0:
        return ''

    if len(lst) == 1:
        return lst[0]

    if len(lst) == 2:
        return f'{lst[0]} {separator} {lst[1]}'

    return f'{", ".join([str(l) for l in lst[:-1]])}, {separator} {lst[-1]}'


def human_readable_hour(datetime_obj: datetime, add_am_pm: bool = False, add_timezone: bool = False) -> str:
    """Get hour of datetime in human-readable format.

    Args:
        datetime_obj: Datetime to get hour for
        add_am_pm: Whether to add AM/PM after the time
        add_timezone: Add timezone abbreviation at end, if present in datetime object

    Returns:
        String of human-readable hour in HH:MM format

    """
    format_str = "%-I"

    if datetime_obj.minute != 0:
        # add the minute part
        format_str += ":%M"

    if add_am_pm:
        format_str += " %p"

    fmt_time = datetime_obj.strftime(format_str)

    if add_timezone:
        timezone = datetime_obj.tzname()
        if timezone:
            return f"{fmt_time} {timezone}"

    return fmt_time

"""Utilities for converting structured community information into text that can be inserted into a prompt."""

from typing import Dict


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

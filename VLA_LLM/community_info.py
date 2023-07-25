"""Utilities for converting structured community information into text that can be inserted into a prompt."""

from typing import Dict


EXAMPLE_COMMUNITY_DATA = {
    "parking_options": [
        {
            "parking_type": "Parking Available",
            "parking_fee": 100.0,
            "parking_fee_term": "Monthly",
            "parking_notes": "noties parking available"
        }
    ],
    "pets": {
        "fee": 50.0,
        "policy": "Pets Allowed"
    }
}


def community_dict_to_prompt(community_dict: Dict) -> str:
    """Convert community dictionary to prompt.

    Args:
        community_dict: Community information

    Returns:
        Prompt

    """
    prompt = ""

    # parking
    parking_options = community_dict["parking_options"]
    if parking_options:
        prompt += "Parking options:\n"
        for idx, option in enumerate(parking_options):
            prompt += f"  {idx + 1}. Parking option {idx + 1}\n"
            prompt += f"     Parking type: {option['parking_type']}\n"
            prompt += f"     Parking fee: ${option['parking_fee']}\n"
            prompt += f"     Parking fee term: {option['parking_fee_term']}\n"
            prompt += f"     Parking notes: {option['parking_notes']}\n"
    else:
        prompt += "There are no parking options available."

    # pets
    pet_policy = community_dict['pets']
    if prompt:
        prompt += "\n"
    prompt += f"Pet policy: {pet_policy['policy']}. Extra fee for pets: {pet_policy['fee']}"

    return prompt

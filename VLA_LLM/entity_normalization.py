"""Convert entities like budget and layout into standard form."""

import re
from typing import List
from typing import Optional


def normalize_layout(layouts: List[str]) -> List[str]:
    """Get list of layout types from extracted entities.

    Args:
        extracted_entities: List of Entity named tuples

    Returns:
        List of layout types that can be used with Nestio API

    """
    layout_map = {
        '1br': {"1", "one", "single"},
        '2br': {"2", "two"},
        '3br': {"3", "three"},
        '4+br': {"4", "four"},
        'studio': {"studio", "studios"},
    }
    layout_types = set()

    for layout in layouts:
        entity_lower = layout.lower()
        for layout_type, keywords in layout_map.items():
            if any(word in entity_lower for word in keywords) and layout_type not in layout_types:
                layout_types.add(layout_type)

    return list(layout_types)


def normalize_budget(budgets: List[str]) -> Optional[str]:
    """Get budget from extracted entities.

    Args:
        extracted_entities: List of Entity named tuples

    Returns:
        String corresponding to budget or None

    """
    if not budgets:
        return None

    # try to convert all budget entities
    budgets = [_parse_budget(budget) for budget in budgets]
    budgets = [budget for budget in budgets if budget is not None]

    if not budgets:
        return None
    
    return max(budgets)


def _parse_budget(budget: str) -> Optional[str]:
    """Parse given budget entity string into string containing just a number.

    Args:
        budget: Text of budget entity

    Returns:
        String corresponding to numeric part

    """
    # Check for abbreviated budgets with k, for ranges we want the max of the range
    match = re.findall(r"\$?(\d*\.?\d+)\s?k", budget.lower())
    if match:
        try:
            return str(int(float(match[-1]) * 1000))
        except ValueError:
            return None

    # return only first recognized budget with all non numeric characters stripped
    stripped_budget = re.sub(r"^(\D+)|(\D+)$", repl="", string=budget)
    general_match = re.findall(r"\$?(\d+,?\d+\.?\d+)", stripped_budget)
    if general_match:
        upper_limit = general_match[-1]
        return upper_limit.replace(",", "")

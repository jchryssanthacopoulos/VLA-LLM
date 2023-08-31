"""Tools related to retrieving listings."""

import datetime
from typing import Dict
from typing import Optional
from typing import Type

from langchain.tools import BaseTool
from pydantic import Field
from pydantic import BaseModel
import pytz

from VLA_LLM.api import get_available_units
from VLA_LLM.api import update_client
from VLA_LLM.dates import MoveInDateConverter
from VLA_LLM.entity_normalization import normalize_budget
from VLA_LLM.entity_normalization import normalize_layout
from VLA_LLM.utils import message as message_utils


class PreferencesSchema(BaseModel):
    budget: Optional[str] = Field(description="Prospect's desired budget like $1500, $3k, or 2.5k")
    layout: Optional[str] = Field(description="Prospect's desired layout like 2 bedroom, studio, or 3 bed")
    move_in_date: Optional[str] = Field(description="Prospect's desired move-in date like march 1, 9/1, or Oct 15")


class AvailableApartmentsTool(BaseTool):
    """Allows the agent to retrieve the available apartments matching the prospect's preferences."""

    name = "available_apartments"
    description = (
        "Used for retrieving available apartments based on the prospect's preferences on the guest card like budget, "
        "layout preference (e.g., 2 bedroom or studio), and move-in date (e.g., march 1, 9/1). These should be "
        "provided as the fields 'budget', 'layout', and 'move_in_date'. If multiple preferences are given, separate "
        "them by a comma, for example: layout=['studio', '2 bedroom']"
    )
    args_schema: Type[PreferencesSchema] = PreferencesSchema
    handle_tool_error = True

    # add new fields to be passed in when instantiating the class
    client_id: int
    community_id: int
    community_timezone: str

    def _run(
            self, budget: Optional[str] = None, layout: Optional[str] = None, move_in_date: Optional[str] = None
    ) -> str:
        """Retrieve available units given preferences.

        Args:
            budget: Desired budget
            layout: Desired layouts
            move_in_date: Desired move-in date

        Returns:
            Response back indicating available apartments

        """
        if layout:
            if isinstance(layout, str):
                layout = [layout]
            layout = normalize_layout(layout)
        if budget:
            if isinstance(budget, str):
                budget = [budget]
            budget = normalize_budget(budget)
        if move_in_date:
            if isinstance(move_in_date, str):
                move_in_date = [move_in_date]
            move_in_date = self._get_move_in_date(move_in_date)

        # update guest card
        update_client(self.client_id, price_ceiling=budget, layout=layout, move_in_date=move_in_date)

        units = get_available_units(self.community_id, move_in_date, layout, budget)
        if not units:
            return (
                "I'm sorry, but there are no available apartments matching your requirements."
            )

        display_dates = not bool(move_in_date)
        displayable_units = self._display_listings(units, display_dates)

        return (
            f"Here are some available apartments matching your requirements:\n{displayable_units}"
        )

    async def _arun(self, budget: str, layout: str, move_in_date: str) -> str:
        """Use the tool asynchronously."""
        return "Not implemented"

    def _get_move_in_date(self, move_in_date: str) -> Optional[datetime.datetime]:
        """Convert move-in date into standardized fornat."""
        message_timestamp = datetime.datetime.now(tz=pytz.UTC)
        move_in_date = MoveInDateConverter().transform_dates_to_date_time_info(
            move_in_date, message_timestamp=message_timestamp, community_timezone=self.community_timezone
        )

        if not move_in_date:
            return

        for d in move_in_date:
            # return first valid date
            if d.is_date():
                return d.datetime_min

    def _display_listings(self, units: Dict, display_dates: Optional[bool] = True) -> str:
        """Display listings in readable format.

        Args:
            units: Which units to display
            display_dates: Whether to display unit availability date
            display_community_name: Whether to display community name

        Returns:
            Formatted listings

        """
        listings = ""

        today_date = datetime.datetime.now().date()

        for idx, unit in enumerate(units):
            if idx:
                listings += "\n"
            if len(units) > 1:
                # only add bullets if there's more than one unit to display
                listings += "\u2022 "

            listings += f"Apartment {unit['unit_number']}: {unit['layout'].lower()}"

            # add floor plan and square footage
            if unit.get('floor_plan'):
                listings += f", {unit['floor_plan']} floor plan"
                if unit.get('sqft'):
                    listings += f" ({unit['sqft']} sq ft)"
            elif unit.get('sqft'):
                listings += f", {unit['sqft']} sq ft"

            if display_dates:
                if unit.get('date_available'):
                    # make sure date available is set
                    avail_date = datetime.datetime.strptime(unit['date_available'], '%Y-%m-%d').date()
                    if avail_date <= today_date:
                        listings += ", available now"
                    else:
                        listings += f", available starting {message_utils.human_readable_month(unit['date_available'])}"

            listings += f" - starts at ${message_utils.human_readable_cost(str(unit['price']))}"

        return listings

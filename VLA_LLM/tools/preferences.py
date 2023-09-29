"""Tools related to updating preferences."""

import json
import datetime
from typing import List
from typing import Optional
from typing import Type

from langchain.tools import BaseTool
from pydantic import Field
from pydantic import BaseModel
import pytz

from VLA_LLM.api import update_client
from VLA_LLM.dates import MoveInDateConverter
from VLA_LLM.entity_normalization import normalize_budget
from VLA_LLM.entity_normalization import normalize_layout
from VLA_LLM.state import State


class PreferencesSchema(BaseModel):
    preferences: str = Field(description="Dictionary with keys 'budget', 'layout', and 'move_in_date'")


class UpdatePreferencesTool(BaseTool):
    """Allows the agent to update client's preferences on the guest card."""

    name = "preference_updater"
    description = (
        "Used for updating the prospect's preferences on the guest card like budget, layout preference (e.g., 2 "
        "bedroom or studio), and move-in date (e.g., march 1, 9/1). These should be provided as a dictionary object "
        "with keys 'budget', 'layout', and 'move_in_date'. If multiple preferences are given, separate them by a "
        "comma, for example: {'layout': ['studio', '2 bedroom'], 'budget': ['2000', '3k']}"
    )
    args_schema: Type[PreferencesSchema] = PreferencesSchema
    handle_tool_error = True

    # add new fields to be passed in when instantiating the class
    community_id: int
    client_id: int
    community_timezone: str

    def _run(self, preferences: str) -> str:
        """Save preferences to the guest card.

        Args:
            preferences: String containing client preferences

        Returns:
            Response back from the tool

        """
        try:
            preferences = json.loads(preferences)
        except json.decoder.JSONDecodeError:
            return ""

        if not isinstance(preferences, dict):
            return ""

        budget = preferences.get('budget')
        layout = preferences.get('layout')
        move_in_date = preferences.get('move_in_date')

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

        update_client(self.client_id, price_ceiling=budget, layout=layout, move_in_date=move_in_date)

        # update agent state with action
        UpdatePreferencesTool.update_state_with_actions(
            self.community_id, self.client_id, price_ceiling=budget, layout=layout, move_in_date=move_in_date
        )

        return ""

    async def _arun(self, preferences: str) -> str:
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

    @classmethod
    def update_state_with_actions(
            cls, community_id: int, client_id: int, move_in_date: Optional[datetime.datetime] = None,
            layout: Optional[List] = None, price_ceiling: Optional[str] = None
    ):
        """Update agent state with guest card update action.

        Args:
            community_id: ID of community
            client_id: ID of client
            move_in_date: Desired move-in date
            layout: List of preferred layout types
            price_ceiling: Budget

        """
        preferences = ""

        if move_in_date:
            preferences += f"move-in date of {move_in_date.strftime('%Y-%m-%d')}"
        if layout:
            if preferences:
                preferences += ", "
            preferences += f"layout{'s' if len(layout) > 1 else ''} of {', '.join(layout)}"
        if price_ceiling:
            if preferences:
                preferences += ", "
            preferences += f"budget of {price_ceiling}"

        if not preferences:
            # if no preferences provided, do not update state
            return

        action_name = 'Guest card updated with {preferences}'.format(preferences=preferences)

        agent_state = State(community_id, client_id)
        agent_state.update_actions(action_name).save()

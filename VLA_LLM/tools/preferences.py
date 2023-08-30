"""Tools related to updating preferences."""

import datetime
from typing import Optional
from typing import Type

from langchain.callbacks.manager import AsyncCallbackManagerForToolRun
from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools import BaseTool
from langchain.tools.base import ToolException
from pydantic import Field
from pydantic import BaseModel

from VLA_LLM.api import update_client


class PreferencesSchema(BaseModel):
    budget: str = Field(description="The prospect's desired budget for their next apartment")


class UpdatePreferencesTool(BaseTool):
    """Allows the agent to update client's preferences on the guest card."""

    name = "preference_updater"
    description = (
        "Used for updating the prospect's preferences on the guest card."
    )
    args_schema: Type[PreferencesSchema] = PreferencesSchema
    handle_tool_error = True

    # add new fields to be passed in when instantiating the class
    client_id: int

    def _run(self, budget: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        update_client(self.client_id, price_ceiling=budget)

    async def _arun(self, appointment_time: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Use the tool asynchronously."""
        return "Not implemented"

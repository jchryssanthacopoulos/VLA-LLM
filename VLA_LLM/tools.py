"""Set of tools the agent has access to."""

import datetime
from typing import Optional
from typing import Type

from langchain.callbacks.manager import AsyncCallbackManagerForToolRun
from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools import BaseTool
from langchain.tools.base import ToolException
from pydantic import Field
from pydantic import BaseModel

from VLA_LLM import config
from VLA_LLM.api import available_appointment_times
from VLA_LLM.api import schedule_appointment


class AppointmentsSchema(BaseModel):
    appointment_time: str = Field(description="The prospect's desired appointment time in YYYY-MM-DD HH:MM:SS format")


class AppointmentDateSchema(BaseModel):
    appointment_date: str = Field(description="The prospect's desired appointment date in YYYY-MM-DD format")


class AppointmentsAndAvailabilitySchema(BaseModel):
    appointment_time: str = Field(description="The prospect's desired appointment time in YYYY-MM-DD HH:MM:SS format")


class AppointmentSchedulerTool(BaseTool):
    """Allows the agent to book an appointment."""

    name = "appointment_scheduler"
    description = (
        "Used for scheduling appointments for prospects. Use this instead of the availability tool if the prospect "
        "provides an exact appointment time, not just a date. Appointment time must be converted into YYYY-MM-DD "
        "HH:MM:SS format before using."
    )
    args_schema: Type[AppointmentsSchema] = AppointmentsSchema
    handle_tool_error = True

    # add new fields to be passed in when instantiating the class
    client_id: int
    group_id: int

    def _run(self, appointment_time: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        # check if time is in the correct format
        try:
            d = datetime.datetime.strptime(appointment_time, '%Y-%m-%d %H:%M:%S')
        except:
            raise ToolException(
                "Appointment time is not in the correct format. "
                "Provide the appointment time in YYYY-MM-DD HH:MM:SS format and try again."
            )

        was_scheduled_successfully = schedule_appointment(d, self.client_id, self.group_id)

        if not was_scheduled_successfully:
            return (
                "Appointment could not be booked because appointment time is unavailable."
            )

        return f"Scheduled successfully for {d.strftime('%H:%M:%S')} on {d.strftime('%Y-%m-%d')}!"

    async def _arun(self, appointment_time: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Use the tool asynchronously."""
        return "Not implemented"


class AppointmentAvailabilityTool(BaseTool):
    """Allows the agent to check appointment availability for a given date."""

    name = "appointment_availability"
    description = "Used for checking availability of appointments on prospect's desired appointment date"
    args_schema: Type[AppointmentDateSchema] = AppointmentDateSchema
    handle_tool_error = True

    # add new fields to be passed in when instantiating the class
    group_id: int
    api_key: str

    def _run(self, appointment_date: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Use the tool."""
        try:
            d = datetime.datetime.strptime(appointment_date, '%Y-%m-%d')
        except:
            raise ToolException(
                "Appointment date is not in the correct format. "
                "The agent should provide it in YYYY-MM-DD format, then run again."
            )

        appt_times = available_appointment_times(d, self.group_id, self.api_key)

        if not appt_times:
            return "There are no available times on the requested date."

        # limit to maximum that should be displayed
        appt_times = appt_times[:config.MAX_AVAILABLE_APPOINTMENT_TIMES_TO_SHOW]

        return f"The next available appointment times on that date are {', '.join(appt_times)}."

    async def _arun(self, appointment_date: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Use the tool asynchronously."""
        return "Not implemented"


class AppointmentSchedulerAndAvailabilityTool(BaseTool):
    """Allows the agent to book an appointment or check appointment availability."""

    name = "appointment_scheduler_availability"
    description = "Used for scheduling appointments for prospects or checking appointment availability."
    args_schema: Type[AppointmentsAndAvailabilitySchema] = AppointmentsAndAvailabilitySchema
    handle_tool_error = True

    # add new fields to be passed in when instantiating the class
    client_id: int
    group_id: int
    api_key: str

    def _run(self, appointment_time: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Try to schedule for provided time."""
        # check if time is in the correct format
        try:
            d = datetime.datetime.strptime(appointment_time, '%Y-%m-%d %H:%M:%S')
        except:
            try:
                d = datetime.datetime.strptime(appointment_time, '%A %Y-%m-%d %H:%M:%S')
            except:
                try:
                    d = datetime.datetime.strptime(appointment_time, '%Y-%m-%d')
                except:
                    raise ToolException(
                        "Appointment date is not in the correct format. "
                        "The agent should provide it in YYYY-MM-DD format, then run again."
                    )

                appt_times = available_appointment_times(d, self.group_id, self.api_key)

                if not appt_times:
                    return "There are no available times on the requested date."

                # limit to maximum that should be displayed
                appt_times = appt_times[:config.MAX_AVAILABLE_APPOINTMENT_TIMES_TO_SHOW]

                return f"The next available appointment times on that date are {', '.join(appt_times)}."

            return self._try_to_book_for_time(d)

        return self._try_to_book_for_time(d)

    async def _arun(self, appointment_time: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Use the tool asynchronously."""
        return "Not implemented"

    def _try_to_book_for_time(self, datetime_obj):
        was_scheduled_successfully = schedule_appointment(datetime_obj, self.client_id, self.group_id)

        if not was_scheduled_successfully:
            return "Appointment could not be booked because appointment time is unavailable."

        return f"Scheduled successfully for {datetime_obj.strftime('%H:%M:%S')} on {datetime_obj.strftime('%Y-%m-%d')}!"


class CurrentTimeTool(BaseTool):
    """Allows the agent to get the current time."""

    name = "get_current_time"
    description = (
        "Used for getting current time in 'day of week YYYY-MM-DD HH:MM:SS' format. Use this every time an "
        "appointment time is mentioned to get the context"
    )

    def _run(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Use the tool."""
        return datetime.datetime.now().strftime('%A %Y-%m-%d %H:%M:%S')

    async def _arun(self, query: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Use the tool asynchronously."""
        return "Not implemented"

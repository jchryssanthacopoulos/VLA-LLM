"""Set of tools the agent has access to."""

import datetime
from typing import Dict
from typing import Optional
from typing import Type

from langchain.callbacks.manager import AsyncCallbackManagerForToolRun
from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools import BaseTool
from langchain.tools.base import ToolException
from pydantic import Field
from pydantic import BaseModel
import pytz

from VLA_LLM import config
from VLA_LLM.dates import AppointmentDateConverter
from VLA_LLM.dates import DateTimeInformation
from VLA_LLM.api import available_appointment_times
from VLA_LLM.api import schedule_appointment


class AppointmentsSchema(BaseModel):
    appointment_time: str = Field(description="The prospect's desired appointment time in YYYY-MM-DD HH:MM:SS format")


class AppointmentDateSchema(BaseModel):
    appointment_date: str = Field(description="The prospect's desired appointment date in YYYY-MM-DD format")


class AppointmentsAndAvailabilitySchema(BaseModel):
    appointment_time: str = Field(description="The prospect's desired appointment time in YYYY-MM-DD HH:MM:SS format")


class BaseSchedulerTool:
    """Class for interacting with the Funnel API to get tour information and return a response back to the LLM."""

    AGENT_RESPONSE_PROBLEM_SCHEDULING = (
        "It looks like there was a problem booking your tour. I will speak to another agent and get back to you."
    )
    AGENT_RESPONSE_SUCCESSFULLY_SCHEDULED = "Scheduled successfully for {apt_time} on {apt_date}!"
    AGENT_RESPONSE_OUTSIDE_OF_OFFICE_HOURS = (
        "The time you requested is outside of office hours. Does another time work for you?"
    )
    AGENT_RESPONSE_TOUR_SAME_TIME = "It looks like you already have an appointment at that time."
    AGENT_RESPONSE_TIME_UNAVAILABLE = "Appointment could not be booked because appointment time is unavailable."
    AGENT_RESPONSE_NO_AVAILABLE_TIMES = "There are no available times on the requested date."
    AGENT_RESPONSE_NEXT_AVAILABLE_TIMES = "The next available appointment times on that date are {avail_times}."

    def try_to_book_for_time(self, datetime_obj: datetime.datetime, client_id: int, group_id: int) -> str:
        """Attempt to book for provided time, returning message about whether it was successful.

        Args:
            appt_time: Time to schedule for
            client_id: ID of client to schedule for
            group_id: ID of group

        Returns:
            Agent response back to the prospect

        """
        response = schedule_appointment(datetime_obj, client_id, group_id)

        errors = response.get("errors")

        if errors:
            return self._parse_scheduling_errors(errors)

        scheduled_appt = response.get("appointment", {}).get("start")

        if scheduled_appt:
            d = datetime.datetime.strptime(scheduled_appt, '%Y-%m-%dT%H:%M:%S')
            return self.AGENT_RESPONSE_SUCCESSFULLY_SCHEDULED.format(
                apt_time=d.strftime('%H:%M'), apt_date=d.strftime('%Y-%m-%d')
            )

        return self.AGENT_RESPONSE_PROBLEM_SCHEDULING

    def get_available_appointment_times(self, datetime_obj: datetime.datetime, group_id: int, api_key: str) -> str:
        """Get available appointment times on provided date.

        Args:
            datetime_obj: Date to get available times for
            group_id: ID of group
            api_key: API key to access times for given group ID

        Returns:
            Agent response back to the prospect

        """
        appt_times = available_appointment_times(datetime_obj, group_id, api_key)

        if not appt_times:
            return self.AGENT_RESPONSE_NO_AVAILABLE_TIMES

        # limit to maximum that should be displayed
        appt_times = appt_times[:config.MAX_AVAILABLE_APPOINTMENT_TIMES_TO_SHOW]

        return self.AGENT_RESPONSE_NEXT_AVAILABLE_TIMES.format(avail_times=', '.join(appt_times))

    def _parse_scheduling_errors(self, errors: Dict) -> str:
        """Parse scheduling error and return response.

        Args:
            errors: Dictionary of errors to parse

        Return:
            Agent response back to the prospect

        """
        error_type = errors.get("error")

        if error_type:
            if error_type == "Client should not be handled by virtual agent.":
                return self.AGENT_RESPONSE_PROBLEM_SCHEDULING

            # a place to handle other errors
            return ""

        error_type = errors.get("errors", {}).get("appointment", {}).get("start", [])

        if error_type:
            if error_type == ["No appointments available at the selected time."]:
                return self.AGENT_RESPONSE_TIME_UNAVAILABLE

            if error_type == ['Selected time is outside tour hours.']:
                return self.AGENT_RESPONSE_OUTSIDE_OF_OFFICE_HOURS

            if error_type == ['Prospect has a conflicting appointment at the same time.']:
                return self.AGENT_RESPONSE_TOUR_SAME_TIME

        # catch-all for all other errors
        return self.AGENT_RESPONSE_PROBLEM_SCHEDULING


class AppointmentSchedulerTool(BaseTool, BaseSchedulerTool):
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

        return self.try_to_book_for_time(d, self.client_id, self.group_id)

    async def _arun(self, appointment_time: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Use the tool asynchronously."""
        return "Not implemented"


class AppointmentAvailabilityTool(BaseTool, BaseSchedulerTool):
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

        return self.get_available_appointment_times(d, self.group_id, self.api_key)

    async def _arun(self, appointment_date: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Use the tool asynchronously."""
        return "Not implemented"


class AppointmentSchedulerAndAvailabilityTool(BaseTool, BaseSchedulerTool):
    """Allows the agent to book an appointment or check appointment availability."""

    name = "appointment_scheduler_availability"
    description = "Used for scheduling appointments for prospects or checking appointment availability."
    args_schema: Type[AppointmentsAndAvailabilitySchema] = AppointmentsAndAvailabilitySchema
    handle_tool_error = True

    # add new fields to be passed in when instantiating the class
    client_id: int
    group_id: int
    api_key: str
    community_timezone: str

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
                    # try to convert provided time into datetime object manually
                    date = self._convert_date(appointment_time)

                    if date.is_date():
                        d = date.datetime_min
                        return self.get_available_appointment_times(d, self.group_id, self.api_key)
                    elif date.is_exact_datetime():
                        d = date.datetime_min
                        return self.try_to_book_for_time(d, self.client_id, self.group_id)

                    raise ToolException(
                        "Appointment date is not in the correct format. "
                        "The agent should provide it in YYYY-MM-DD format, then run again."
                    )

                return self.get_available_appointment_times(d, self.group_id, self.api_key)

            return self.try_to_book_for_time(d, self.client_id, self.group_id)

        return self.try_to_book_for_time(d, self.client_id, self.group_id)

    async def _arun(self, appointment_time: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Use the tool asynchronously."""
        return "Not implemented"

    def _convert_date(self, appointment_time: str) -> Optional[DateTimeInformation]:
        appointment_time_converter = AppointmentDateConverter(am_to_pm_threshold=8)

        message_timestamp = datetime.datetime.now(tz=pytz.UTC)
        dates = appointment_time_converter.transform_dates_to_date_time_info(
            [appointment_time], message_timestamp=message_timestamp, community_timezone=self.community_timezone
        )

        if not dates:
            return

        # return first date
        return dates[0]


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

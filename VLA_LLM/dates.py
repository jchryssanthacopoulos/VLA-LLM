"""Classes to help parse strings into datetime objects."""

import calendar
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import time
from datetime import timedelta
from datetime import tzinfo
import re
from string import punctuation
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import dateparser
import pytz


# regex for hyphenated and early/mid/late month range
HYPHENATED_MONTH_PATTERN = (
    r"(?P<day_part_1>early|mid)?/?(?P<day_part_2>early|mid|late)-?\s*"
    r"(?P<month>Jan|jan|January|january|Feb|feb|February|february|"
    r"Mar|mar|March|march|Apr|apr|April|april|May|may|"
    r"Jun|jun|June|june|Jul|jul|July|july|Aug|aug|August|august|"
    r"Sep|sep|September|september|Oct|oct|October|october|Nov|nov|"
    r"November|november|Dec|dec|December|december)"
)

# mapping from month name or abbreviation to number
MONTH_NUMS_LOOKUP = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
MONTH_OR_ABBRV_RE_STRING = f"{'|'.join(list(MONTH_NUMS_LOOKUP.keys()))}"

APARTMENT_DATE_LIST_PATTERN = (
    rf"(?P<hour1>\d+)(?P<time_of_day>pm|am)[\s\-]*\d*(pm|am)?[\s\-]*(?P<month>{MONTH_OR_ABBRV_RE_STRING})\s*(?P<day>\d+)"
)

# some time constants
TIME_MIN = time(hour=0, minute=0, second=0)
TIME_MAX = time(hour=23, minute=59, second=59)
TIME_MORNING_END = time(hour=11, minute=59, second=59)
TIME_AFTERNOON_END = time(hour=16, minute=59, second=59)


@dataclass
class DateTimeInformation:
    """Datetime information encoded as min and max datetimes

    Wrapping single datetimes with a dataclass composed of min and max datetimes allows us to express more complex
     ideas than just a single date or time, such as open and closed ranges of times.

    Objects of this class are mutable - their setters directly modify the object itself.
    Although mutable, self is still returned by setter methods to allow for instantiation and setting in the same line:
        datetime_info = DateTimeInformation().set_as_date(dt.datetime.now())
    The setters can then be used as pseudo-constructors which are more explicit than an overloaded constructor method.

    Currently supported:
     If datetime_min and datetime_max are equivalent, the object expresses an exact datetime.
     If datetime_min and datetime_max are separated by a single day, the object expresses a day or date.
     If datetime_min is a valid datetime and datetime_max is None, the object expresses an after datetime range.
     If datetime_min is None and datetime_max is a valid datetime, the object expresses a before datetime range.
     If datetime_min and datetime_max are not None and do not meet the above criteria, the object expresses a between datetime range.

    """

    datetime_min: datetime = field(default=None)
    datetime_max: datetime = field(default=None)
    is_exact_date_range: bool = True

    def convert(self) -> Optional[Tuple[datetime]]:
        """Convert DateTimeInformation object to a datetime tuple.

        Returns:
            1-element datetime tuple if DateTimeInformation is a valid date, exact datetime, or after/before range, or
            2-element datetime tuple if DateTimeInformation is a valid between range, or
            None otherwise
        """
        converted = None
        if self.is_date():
            converted = (self.datetime_min,)
        elif self.is_exact_datetime():
            converted = (self.datetime_min,)
        elif self.is_after_datetime():
            converted = (self.datetime_min,)
        elif self.is_before_datetime():
            converted = (self.datetime_max,)
        elif self.is_between_datetime():
            converted = (self.datetime_min, self.datetime_max)
        return converted

    def set_as_date(self, date: datetime):
        """Set DateTimeInformation object as a date without a specific time, e.g. April 1 2022

        Accepts either a datetime.date or datetime.datetime - in the latter case the time component is ignored.
        datetime_min will be set to the date passed with the time component set to its minimum, i.e. 00:00:00.
        datetime_max will be set to the date passed with the time component set to its maximum, i.e. 23:59:59.
        The time range between the two will thus be the length of 1 day minus 1 second.

        Args:
            date: date or datetime object from which to extract the day

        Returns:
            DateTimeInformation encoded as a date
        """
        if date:
            self.datetime_min = datetime.combine(date=date, time=TIME_MIN)
            self.datetime_max = datetime.combine(date=date, time=TIME_MAX)
        return self

    def set_as_exact_datetime(self, datetime: datetime):
        """Set DateTimeInformation object to have an exact date and time, e.g. April 1 2022 at 08:15:00
        
        Both datetime_min and datetime_max will be set to the date and time passed.

        Args:
            datetime: datetime to which both min and max will be set

        Returns:
            DateTimeInformation encoded as an exact date and time
        """
        self.datetime_min = datetime
        self.datetime_max = datetime
        return self

    def set_as_after_datetime(self, datetime: datetime):
        """Set DateTimeInformation object to encode an after datetime range, e.g. 'after 3pm on 12/5'

        datetime_min will be set to the datetime while datetime_max will be set to None.

        Args:
            datetime: datetime to which min will be set

        Returns:
            DateTimeInformation encoded as an after datetime range
        """
        self.datetime_min = datetime
        self.datetime_max = None
        return self

    def set_as_before_datetime(self, datetime: datetime):
        """Set DateTimeInformation object to encode a before datetime range, e.g. 'before 3pm on 12/5'

        datetime_min will be set to None while datetime_max will be set to the datetime.

        Args:
            datetime: datetime to which max will be set

        Returns:
            DateTimeInformation encoded as a before datetime range
        """
        self.datetime_min = None
        self.datetime_max = datetime
        return self

    def set_as_between_datetime(
            self, datetime_start: datetime, datetime_end: datetime, is_exact_date_range: bool = True
    ):
        """Set DateTimeInformation object to encode a between datetime range, e.g. 'between 2pm and 5pm'

        datetime_min will be to set to the start of the range while datetime_max will be set to the end of the range.
        datetime_min must be before datetime_max, and the time components cannot be set respectively to TIME_MIN and
         TIME_MAX (because this is the encoding scheme for a single day).

        Args:
            datetime_start: beginning of datetime range
            datetime_end: end of datetime range

        Returns:
            DateTimeInformation encoded as a between datetime range
        """
        if datetime_start is not None and datetime_end is not None:
            if datetime_start < datetime_end and (datetime_start.time() != TIME_MIN or datetime_end.time() != TIME_MAX):
                self.datetime_min = datetime_start
                self.datetime_max = datetime_end
                self.is_exact_date_range = is_exact_date_range
        return self

    def set_as_morning_datetime(self, date: datetime):
        """Set DateTimeInformation object as a morning time range

        datetime_max will be set to the date passed with the time component set to the end of morning, i.e. 11:59:59.

        Args:
            date: date or datetime object from which to extract the day

        Returns:
            DateTimeInformation encoded as a morning

        """
        if date:
            self.datetime_min = datetime.combine(date=date, time=TIME_MIN)
            self.datetime_max = datetime.combine(date=date, time=TIME_MORNING_END)
            self.is_exact_date_range = False
        return self

    def set_as_afternoon_datetime(self, date: datetime):
        """Set DateTimeInformation object as a afternoon time range

        Args:
            date: date or datetime object from which to extract the day

        Returns:
            DateTimeInformation encoded as a morning

        """
        if date:
            self.datetime_min = datetime.combine(date=date, time=TIME_MORNING_END) + timedelta(0, 1)
            self.datetime_max = datetime.combine(date=date, time=TIME_AFTERNOON_END)
            self.is_exact_date_range = False
        return self

    def set_as_morning_afternoon_datetime(self, date: datetime):
        """Set DateTimeInformation object as a morning and afternoon time range

        datetime_max will be set to the date passed with the time component set to the end of afternoon, i.e. 3:59:59.

        Args:
            date: date or datetime object from which to extract the day

        Returns:
            DateTimeInformation encoded as a morning and afternoon

        """
        if date:
            self.datetime_min = datetime.combine(date=date, time=TIME_MIN)
            self.datetime_max = datetime.combine(date=date, time=TIME_AFTERNOON_END)
            self.is_exact_date_range = False
        return self

    def replace_timezone(self, tzinfo_val: tzinfo):
        """Replace the timezone information for both datetime_min and datetime_max

        If tzinfo_val is None, datetimes will be replaced with naive datetimes (timezone unaware).
        If tzinfo_val is not None, datetimes will not undergo any timezone conversion.

        Args:
            tzinfo_val: timezone information to displace current timezone data

        Returns:
            DateTimeInformation
        """
        if self.datetime_min:
            self.datetime_min = self.datetime_min.replace(tzinfo=tzinfo_val)
        if self.datetime_max:
            self.datetime_max = self.datetime_max.replace(tzinfo=tzinfo_val)

        return self

    def localize_to_timezone(self, tzinfo_val: tzinfo):
        """Localize to given timezone

        Args:
            tzinfo_val: timezone to localize to

        Returns:
            DateTimeInformation

        """
        if self.datetime_min and self.datetime_min.tzinfo is None:
            self.datetime_min = tzinfo_val.localize(self.datetime_min)
        if self.datetime_max and self.datetime_max.tzinfo is None:
            self.datetime_max = tzinfo_val.localize(self.datetime_max)

        return self

    def push_dates_above_threshold(self, hour_threshold: int):
        """Push times forward 12 hours if before given hour threshold.

        Args:
            hour_threshold: Hour to use as reference

        """
        if self.datetime_min and 1 <= self.datetime_min.hour < hour_threshold:
            # time probably refers to 12 hours later
            self.datetime_min += timedelta(hours=12)

        if self.datetime_max and 1 <= self.datetime_max.hour < hour_threshold:
            self.datetime_max += timedelta(hours=12)

    def push_to_next_day_if_before_time(self, reference_timestamp: datetime):
        """Push times to next day if before given timestamp.

        Args:
            reference_timestamp: Timestamp to use as reference to push times to next day

        """
        if self.is_between_datetime():
            if not self.is_exact_date_range:
                # don't push forward non-exact time ranges, since they can potentially include times
                # before the reference timestamp (e.g., when referring to "morning today")
                return
            if self.datetime_min < reference_timestamp:
                self.datetime_min += timedelta(days=1)
                self.datetime_max += timedelta(days=1)
            return

        if self.datetime_min and self.datetime_min < reference_timestamp:
            self.datetime_min += timedelta(days=1)

        if self.datetime_max and self.datetime_max < reference_timestamp:
            self.datetime_max += timedelta(days=1)

    def is_date(self):
        """Check if this DateTimeInformation object is a date (without a specific time).

        If the difference between the two datetimes is 1 day minus 1 second, this evaluates to True.

        Returns:
            True if date, otherwise False
        """
        if self.datetime_min and self.datetime_max:
            return self.datetime_min.time() == TIME_MIN and self.datetime_max.time() == TIME_MAX
        return False

    def is_exact_datetime(self):
        """Check if this DateTimeInformation object has an exact date and time.

        If the two datetimes are identical (and not None), this evaluates to True.

        Returns:
            True if exact_datetime, otherwise False
        """
        if self.datetime_min is None or self.datetime_max is None:
            return False
        return self.datetime_min == self.datetime_max

    def is_after_datetime(self):
        """Check if this DateTimeInformation object is an after range e.g. 'after 3pm on 12/5'.

        Returns:
            True if after datetime, otherwise False
        """
        return self.datetime_min is not None and self.datetime_max is None

    def is_before_datetime(self):
        """Check if this DateTimeInformation object is a before range e.g. 'before 3pm on 12/5'.

        Returns:
            True if before datetime, otherwise False
        """
        return self.datetime_min is None and self.datetime_max is not None

    def is_between_datetime(self):
        """Check if this DateTimeInformation object is a between range e.g. 'between 2pm and 5pm'.

        Returns:
            True if between datetime range, otherwise False
        """
        to_return = False
        if self.datetime_min is not None and self.datetime_max is not None and self.datetime_min < self.datetime_max:
            # Ensure the range would not also be interpreted as a single day DateTimeInformation
            to_return = self.datetime_min.time() != TIME_MIN or self.datetime_max.time() != TIME_MAX
        return to_return

    def __bool__(self):
        """Return truth-value of this object.

        Returns:
            True if at least one datetime is instantiated, otherwise False
        """
        return bool(self.datetime_min) or bool(self.datetime_max)


class DateConverter:
    """Used to define a base class with a lot of the functions to convert a date string into datetime object"""

    def __init__(
            self,
            clean_date: bool = True,
            clean_date_pattern: str = r"[\(,\)]",
            morning_start_hour: int = 5,
    ):
        """Initialize class with hyper paramters

        Args:
            clean_date: Whether to apply cleaning on string
            clean_date_pattern: Regex of tokens to replace with empty string
            morning_start_hour: The time prior to which "tomorrow" is defined to be the upcoming day

        """
        self.filter_sieve_order = list()
        self.clean_date = clean_date
        self.clean_date_pattern = clean_date_pattern
        self.morning_start_hour = morning_start_hour
        self.month_abbrvs = "jan|feb|mar|apr|may|june|july|aug|sep|oct|nov|dec"

    def transform_dates_to_date_time_info(
            self,
            dates: List[str],
            message_timestamp: datetime,
            community_timezone: str,
            date_context: Optional[datetime] = None
    ) -> List[DateTimeInformation]:
        """Convert date to the DatTimeInformation dataclass

        Args:
            dates: A list of extracted date to be converted to datetime object
            message_timestamp: Timestamp of message
            community_timezone: Timezone of message
            date_context: Date that establishes context for message

        Returns:
            A properly formatted datetime string

        """
        datetime_info_list = []
        for date in dates:
            if self.clean_date:
                date = self._clean_date(date)

            datetime_info = self.parse_date(date, message_timestamp, community_timezone, date_context)
            if datetime_info:
                datetime_info_list.append(datetime_info.replace_timezone(tzinfo_val=None))
        return datetime_info_list

    def parse_date(
            self,
            date: str,
            message_timestamp: datetime,
            community_timezone: str,
            date_context: Optional[datetime] = None
    ) -> Optional[DateTimeInformation]:
        """Used to specify the context to dateparse a given string and returns a datetime object

        Args:
            date: The extracted date to be converted to datetime object
            message_timestamp: Timestamp of message
            community_timezone: Timezone of community
            date_context: Date that establishes context for message

        Returns:
            A datetime object or None if the date was unable to be parsed

        """
        try:
            message_timezone = pytz.timezone(community_timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            timezone = "US/Eastern"
            message_timezone = pytz.timezone(timezone)

        # Get the day that the message was sent
        message_day = message_timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        if date_context is not None:
            relative_base = date_context
        else:
            relative_base = message_timestamp.replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)

        dateparser_settings = {
            "TIMEZONE": community_timezone,
            "RETURN_AS_TIMEZONE_AWARE": True,
            "RELATIVE_BASE": relative_base,
            "PREFER_DATES_FROM": "future",
        }
        kwarg_set = {
            "message_day": message_day,
            "message_timestamp": message_timestamp,
            "message_timezone": message_timezone,
            "dateparser_settings": dateparser_settings,
        }

        datetime_format_date = None

        for function in self.filter_sieve_order:
            if datetime_format_date is None:
                try:
                    datetime_format_date = function(date, **kwarg_set)
                except ValueError:
                    # check for general processing errors
                    continue
            else:
                break

        if datetime_format_date:
            datetime_format_date = self._postprocess_date(datetime_format_date, message_timestamp, message_timezone)

        return datetime_format_date

    def _postprocess_date(
            self, date: DateTimeInformation, message_timestamp: datetime, message_timezone: pytz.UTC
    ) -> Optional[DateTimeInformation]:
        """Perform various postprocessing steps on parsed date.

        Args:
            date: Parsed date
            message_timestamp: Timestamp of message
            message_timezone: Timezone of community

        Returns:
            Postprocessed date or None

        """
        return date

    def _clean_date(self, string: str) -> str:
        """Clean message by removing certain patterns.

        Args:
            string: The string to clean

        Returns:
            Cleaned message str

        """
        message = re.sub(self.clean_date_pattern, "", string)
        message = message.replace(" a.m.", "am").replace("a.m.", "am")
        message = message.replace(" p.m.", "pm").replace("p.m.", "pm")
        message = message.lower()
        return message

    def _weekend_converter(self, date: str, message_day: datetime = None, **kwargs) -> Optional[DateTimeInformation]:
        """Checks to see if weekend was specified and converts it to appropriate format

        Args:
            date: The identified date to convert
            message_day: The day that the message was sent

        Returns:
            DateTimeInformation object or None

        """
        # Check for required args
        if message_day is None:
            return None

        # We default this type of date to returning saturday
        # Unless it is sunday when we will return sunday
        if re.search(r"\bthis weekend\b", date.lower()):
            day_of_week = message_day.weekday()

            if day_of_week < 5:
                # Monday-Friday
                days_to_saturday = 5 - day_of_week
                return DateTimeInformation().set_as_date(message_day + timedelta(days_to_saturday))

            return DateTimeInformation().set_as_date(message_day)

    def _weekday_converter(self, date: str, message_day: datetime = None, **kwargs) -> Optional[DateTimeInformation]:
        """Checks to see if weekday was specified and converts it to appropriate format

        Args:
            date: The identified date to convert
            message_day: The day that the message was sent

         Returns:
            DateTimeInformation object or None

        """
        # Check for required args
        if message_day is None:
            return None

        # Return the next day or monday if the message was sent on fri,sat,sun
        if re.search(r"\bthis week\b", date):
            day_of_week = message_day.weekday()

            if day_of_week < 3:
                return DateTimeInformation().set_as_date(message_day + timedelta(1))

            return DateTimeInformation().set_as_date(message_day + timedelta(7 - day_of_week))

    def _early_mid_late_month(self, date: str, message_timestamp: datetime, **kwargs) -> Optional[DateTimeInformation]:
        """If early/mid/late month pattern return the appropriate datetime

        Args:
            date: The identified date to convert
            message_timestamp: The message timestamp

        Returns:
            DateTimeInformation object or None

        """
        # Check for required args
        if message_timestamp is None:
            return None

        for match in re.finditer(HYPHENATED_MONTH_PATTERN, date):
            results_dict = match.groupdict()
            month = results_dict["month"].strip().lower()

            if month in MONTH_NUMS_LOOKUP:
                month_int = MONTH_NUMS_LOOKUP[month]
                year = message_timestamp.year

                if month_int < message_timestamp.month:
                    year += 1

                month_days = {
                    "early": 1,
                    "mid": 15,
                    "late": calendar.monthrange(year, month_int)[1],
                }

                for day_field in ["day_part_1", "day_part_2"]:
                    if results_dict[day_field] in month_days:
                        parsed_date = datetime(year, month_int, month_days[results_dict[day_field]])

                        if message_timestamp.tzinfo:
                            parsed_date = message_timestamp.tzinfo.localize(parsed_date)

                        return DateTimeInformation().set_as_date(parsed_date)

    def _time_qualifier(self, date: str, dateparser_settings: Dict = None, **kwargs) -> Optional[DateTimeInformation]:
        """Currently dateparser can't parse 'next monday' so do this manually

        Args:
            date: The date string to convert
            dateparser_settings: The date parser settings

        Returns:
            DateTimeInformation object or None

        """
        # Check for required args
        if dateparser_settings is None:
            return None

        parsed_date = None

        if "next" in date:
            date = date.replace("next", "")
            date = date.strip()
            parsed_date = dateparser.parse(date, settings=dateparser_settings)
            if parsed_date:
                parsed_date += timedelta(days=7)
        elif "this" in date:
            date = date.replace("this", "")
            date = date.strip()
            parsed_date = dateparser.parse(date, settings=dateparser_settings)

        if parsed_date:
            if parsed_date.time() == time.min:
                return DateTimeInformation().set_as_date(parsed_date)
            return DateTimeInformation().set_as_exact_datetime(parsed_date)

    def _end_of_month(
            self,
            date: str,
            message_day: datetime = None,
            message_timezone: pytz.UTC = None,
            **kwargs,
    ) -> Optional[DateTimeInformation]:
        """Check for 'end of month' string in date return last day of the month

        Args:
            date: The date string to convert
            message_day: The day that the message was sent
            message_timezone: The timezone of the message

        Returns:
            DateTimeInformation object or None

        """
        # Check for required args
        if message_day is None or message_timezone is None:
            return None

        if "end of month" in date:
            year = message_day.year
            month = message_day.month
            parsed_date = datetime(year, month, day=calendar.monthrange(year, month)[1])
            parsed_date = message_timezone.localize(parsed_date)
            return DateTimeInformation().set_as_date(parsed_date)

    def _asap(self, date: str, message_timestamp: datetime = None, **kwargs) -> Optional[DateTimeInformation]:
        """Check for 'asap' string in date return the current day in datetime format

        Args:
            date: The date string to convert
            message_timestamp:  The timestamp of the message

        Returns:
            DateTimeInformation object or None

        """
        # Check for required args
        if message_timestamp is None:
            return None

        key_words = ["asap", "as soon as possible", "immediate", "immediately"]

        date = date.lower()

        if kwargs.get('exact_match') is True:
            matches_pattern = any(word == date for word in key_words)
        else:
            matches_pattern = any(word in date for word in key_words)

        if matches_pattern:
            return DateTimeInformation().set_as_date(
                message_timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            )

    def _qualifier_exact_month(
            self, date: str, message_day: datetime = None, **kwargs
    ) -> Optional[DateTimeInformation]:
        """Check for qualifiers like 'end of april' 'middle of may" date return appropriate date

        Args:
            date: The date string to convert
            message_day: The day that the message was sent

        Returns:
            DateTimeInformation object or None

        """
        # Check for required args
        if message_day is None:
            return None

        # Grab the message year
        year = message_day.year

        # Iterate through match objects
        beginning_month = re.match(rf"beginning of ({self.month_abbrvs})", date, re.IGNORECASE)
        if beginning_month:
            month = MONTH_NUMS_LOOKUP.get(beginning_month.group(1), None)
            if month:
                return DateTimeInformation().set_as_date(datetime(year, month, day=1))

        middle_month = re.match(rf"middle of ({self.month_abbrvs})", date, re.IGNORECASE)
        if middle_month:
            month = MONTH_NUMS_LOOKUP.get(middle_month.group(1), None)
            if month:
                return DateTimeInformation().set_as_date(datetime(year, month, day=15))

        end_month = re.match(rf"end of ({self.month_abbrvs})", date, re.IGNORECASE)
        if end_month:
            month = MONTH_NUMS_LOOKUP.get(end_month.group(1), None)
            if month:
                return DateTimeInformation().set_as_date(datetime(year, month, day=calendar.monthrange(year, month)[1]))

    def _space_delimted_month(self, date: str, message_day: datetime = None, **kwargs) -> Optional[DateTimeInformation]:
        """A lower precision filter to check if a month exists in the move-in-date entity

        Args:
            date: The date string to convert
            message_day: The day that the message was sent

        Returns:
            DateTimeInformation object or None

        """
        # Check for required args
        if message_day is None:
            return None

        # Grab the message year and month
        message_year = message_day.year
        message_month = message_day.month

        # Grab months with abbreviations and create a space separated lookup optionally grab day mentioned
        month_lookup_pattern = rf"\b({'|'.join(list(MONTH_NUMS_LOOKUP.keys()))}) *(\d*)(\b|th|rd|nd|st)"

        if kwargs.get('exact_match') is True:
            month_lookup_pattern = f"^{month_lookup_pattern}$"

        punctuation_removed_lower_date = date.lower()
        for char in punctuation:
            punctuation_removed_lower_date = punctuation_removed_lower_date.replace(char, " ")

        # Find all space separated months in string
        found_months = re.findall(month_lookup_pattern, punctuation_removed_lower_date)
        if found_months:
            converted_month_days = [
                (
                    MONTH_NUMS_LOOKUP[month[0]],
                    int(month[1]) if month[1] else 1,
                )
                for month in found_months
            ]
            # Take the min month
            extracted_month, extracted_day = min(converted_month_days)

            # Handle wrap around message in i.e. December asking about january
            if extracted_month < message_month:
                parsed_date = datetime(
                    year=message_year + 1,
                    month=extracted_month,
                    day=self._valid_day_for_month_year(message_year + 1, extracted_month, extracted_day),
                )
            else:
                parsed_date = datetime(
                    year=message_year,
                    month=extracted_month,
                    day=self._valid_day_for_month_year(message_year, extracted_month, extracted_day),
                )

            if "morning" in date and "afternoon" in date:
                return DateTimeInformation().set_as_morning_afternoon_datetime(parsed_date)
            elif "morning" in date:
                return DateTimeInformation().set_as_morning_datetime(parsed_date)
            elif "afternoon" in date:
                return DateTimeInformation().set_as_afternoon_datetime(parsed_date)
            else:
                return DateTimeInformation().set_as_date(parsed_date)

    def _exception_safe_date_parse(
            self, date: str, dateparser_settings: Dict = None, **kwargs
    ) -> Optional[DateTimeInformation]:
        """Wrap dateparsers parse to catch exception and return None

        Args:
            date: The date string to convert
            dateparser_settings: The date parser settings

        Returns:
            DateTimeInformation object or None

        """
        # Check for required args
        if dateparser_settings is None:
            return None

        # Dateparser produces false positives on numeric types without context
        if len(date) <= 2 and date.isdigit():
            return None

        try:
            datetime_format_date = dateparser.parse(date, settings=dateparser_settings)
        except IndexError:
            return None

        if not datetime_format_date:
            return None

        if datetime_format_date.time() == time.min:
            return DateTimeInformation().set_as_date(datetime_format_date)

        return DateTimeInformation().set_as_exact_datetime(datetime_format_date)

    def _valid_day_for_month_year(self, year: int, month: int, day: int) -> int:
        """Given a month and candidate day, return a valid day.

        Args:
            year: The year to validate for
            month: The month to validate for
            day: The Day to to validate for

        """
        num_days_in_month = calendar.monthrange(year, month)[1]
        return min(max(day, 1), num_days_in_month)


class AppointmentDateConverter(DateConverter):
    """Extend the Date converter for appointment time specific date conversions"""

    def __init__(self, am_to_pm_threshold: int = 9, **kwargs):
        """Call base class constructor and define the filtering order

        Args:
            am_to_pm_threshold: If the time of the day is before this threshold we push the time 12 hours (am -> pm)
            **kwargs: Any keyword arguments to override defaults of baseclass DateConverter

        """
        super().__init__(**kwargs)
        self.am_to_pm_threshold = am_to_pm_threshold
        self.filter_sieve_order = [
            self._weekday_converter,
            self._early_mid_late_month,
            self._time_qualifier,
            self._tomorrow_qualifier_time,
            self._today_qualifier_time,
            self._time_range_between,
            self._time_range,
            self._singular_digit,
            self._hour_range_month_date,
            self._exception_safe_date_parse,
            self._weekend_converter,
            self._end_of_month,
            self._qualifier_exact_month,
            self._asap,
            self._space_delimted_month,
            self._time_of_day
        ]

    def _postprocess_date(
            self, date: DateTimeInformation, message_timestamp: datetime, message_timezone: pytz.UTC
    ) -> Optional[DateTimeInformation]:
        """Perform various postprocessing steps on parsed date.

        Args:
            date: Parsed date
            message_timestamp: Timestamp of message
            message_timezone: Timezone of community

        Returns:
            Postprocessed date or None

        """
        date.localize_to_timezone(message_timezone)
        date.push_dates_above_threshold(self.am_to_pm_threshold)
        date.push_to_next_day_if_before_time(message_timestamp)
        return date

    def _time_range_between(self, date: str, message_day: datetime = None, **kwargs) -> Optional[DateTimeInformation]:
        """Used to match double-ended ranges of time

        e.g. 1pm to 3pm on Feb 3
             5pm - 6pm tomorrow
             8:00AM to 10:00AM

        Performs day conversion if date/day are specified

        Args:
            date: the date string to convert
            message_day: day that the message was sent

        Returns:
            DateTimeInformation object or None

        """
        if message_day is None:
            return
        
        # Between-range pattern
        re_pattern = (
            r"(?P<hour_minute_start>\d{1,2}:?\d{0,2})"
            "\s*(?P<time_of_day_start>am|pm)?"
            "\s*(to|-)\s*"
            r"(?P<hour_minute_end>\d{1,2}:?\d{0,2})"
            "\s*(?P<time_of_day_end>am|pm)?"
        )
        # Pattern to catch date specifier
        date_pattern = (
            rf"(?P<month>{MONTH_OR_ABBRV_RE_STRING})"
            "\s*(?P<day>\d{1,2})"
        )
        match = re.search(re_pattern, date, re.IGNORECASE)

        if not match:
            return

        # Parse the time components
        match_dict = match.groupdict()

        # Parse start and end times
        parsed_time_start = self._parse_hour_minute_str(match_dict["hour_minute_start"])
        if not parsed_time_start:
            return

        parsed_time_end = self._parse_hour_minute_str(match_dict["hour_minute_end"])
        if not parsed_time_end:
            return

        hour_start, minute_start = parsed_time_start
        hour_start = self._time_qualifier_to_int(hour_start, self.am_to_pm_threshold, match_dict['time_of_day_start'])

        hour_end, minute_end = parsed_time_end
        hour_end = self._time_qualifier_to_int(hour_end, self.am_to_pm_threshold, match_dict['time_of_day_end'])

        # Parse the day components
        date_match = re.search(date_pattern, date, re.IGNORECASE)

        # If date specified, we'll use that over a day specifier
        if date_match:
            date_match_dict = date_match.groupdict()
            month = date_match_dict['month'].lower()
            month_to_number = MONTH_NUMS_LOOKUP[month]
            day = int(date_match_dict['day'])
            message_day = message_day.replace(month=month_to_number, day=day)
        else:
            message_day_converted = self._match_and_convert_day_specifier(date, message_day)
            if message_day_converted:
                message_day = message_day_converted

        return DateTimeInformation().set_as_between_datetime(
            datetime_start=message_day.replace(hour=hour_start, minute=minute_start),
            datetime_end=message_day.replace(hour=hour_end, minute=minute_end)
        )

    def _time_range(self, date: str, message_day: datetime = None, **kwargs) -> Optional[DateTimeInformation]:
        """Used to match ranges of time

        e.g. today before 3pm
             after 5pm tomorrow
             7pm or later

        Args:
            date: the date string to convert
            message_day: day that the message was sent

        Returns:
            DateTimeInformation object or None

        """
        if message_day is None:
            return

        # Pattern to catch before or after specifier as well as the time
        re_pattern = (
            r"\s*(?P<prep_pre>before|after)?"
            "\s*(?P<hour_minute>\d{1,2}:?\d{0,2})"
            "\s*(?P<time_of_day>am|pm)?"
            "\s*(?P<prep_post>(or|and)\s*(later|earlier))?"
        )
        match = re.search(re_pattern, date, re.IGNORECASE)

        # Only parse as range if we captured before, after, etc.
        if not match or (not match['prep_pre'] and not match['prep_post']):
            return

        match_dict = match.groupdict()

        parsed_time = self._parse_hour_minute_str(match_dict["hour_minute"])
        if not parsed_time:
            return

        extracted_hour = self._time_qualifier_to_int(parsed_time[0], self.am_to_pm_threshold, match_dict['time_of_day'])

        message_day_converted = self._match_and_convert_day_specifier(date, message_day)
        if message_day_converted:
            message_day = message_day_converted

        # Add time component
        parsed_date = message_day.replace(hour=extracted_hour, minute=parsed_time[1])

        match_dict["prep_pre"] = match_dict["prep_pre"] or ""
        match_dict["prep_post"] = match_dict["prep_post"] or ""

        if match_dict['prep_pre'] == 'before' or 'earlier' in match_dict['prep_post']:
            return DateTimeInformation().set_as_before_datetime(parsed_date)

        if match_dict['prep_pre'] == 'after' or 'later' in match_dict['prep_post']:
            return DateTimeInformation().set_as_after_datetime(parsed_date)

    def _tomorrow_qualifier_time(
            self, date: str, message_day: datetime = None, **kwargs
    ) -> Optional[DateTimeInformation]:
        """Convert tomorrow at pattern (e.g. tomorrow at 3)

        Args:
            date: The date string to convert
            message_day: The day that the message was sent

        Returns:
            DateTimeInformation object or None

        """
        # Check for required args
        if message_day is None:
            return

        re_pattern = (
            r"(?P<pre>tomorrow\s*(at|around|@)?(\s*|~))?"
            "(?P<hour_minute>\d{1,2}:?\d{0,2})\s*(?P<time_of_day>am|pm)?"
            "(?P<post>tomorrow)?"
            "\s*(?P<prep_post>(or|and)\s*(later|earlier))?"
        )
        match = re.search(re_pattern, date, re.IGNORECASE)

        if not match or (not match['pre'] and not match['post']):
            return

        match_dict = match.groupdict()

        parsed_time = self._parse_hour_minute_str(match_dict["hour_minute"])
        if not parsed_time:
            return

        extracted_hour = self._time_qualifier_to_int(parsed_time[0], self.am_to_pm_threshold, match_dict["time_of_day"])

        tomorrow = message_day + timedelta(days=1)
        tomorrow = tomorrow.replace(hour=extracted_hour, minute=parsed_time[1])

        if match_dict["prep_post"]:
            if "later" in match_dict["prep_post"]:
                return DateTimeInformation().set_as_after_datetime(tomorrow)

            if "earlier" in match_dict["prep_post"]:
                return DateTimeInformation().set_as_before_datetime(tomorrow)

        return DateTimeInformation().set_as_exact_datetime(tomorrow)

    def _today_qualifier_time(self, date: str, message_day: datetime = None, **kwargs) -> Optional[DateTimeInformation]:
        """Convert today at pattern (e.g. today at 3)

        Args:
            date: The date string to convert
            message_day: The day that the message was sent

        Returns:
            DateTimeInformation object or None

        """
        # Check for required args
        if message_day is None:
            return

        re_pattern = (
            r"(?P<pre>today\s*(at|around|@)?(\s*|~))?"
            "(?P<hour_minute>\d{1,2}:?\d{0,2})\s*(?P<time_of_day>am|pm)?"
            "(?P<post>today)?"
            "\s*(?P<prep_post>(or|and)\s*(later|earlier))?"
        )
        match = re.search(re_pattern, date, re.IGNORECASE)

        if not match or (not match['pre'] and not match['post']):
            return

        match_dict = match.groupdict()

        extracted_time = self._parse_hour_minute_str(match_dict["hour_minute"])
        if not extracted_time:
            return

        extracted_hour = self._time_qualifier_to_int(extracted_time[0], self.am_to_pm_threshold, match_dict["time_of_day"])

        message_day = message_day.replace(hour=extracted_hour, minute=extracted_time[1])

        if match_dict["prep_post"]:
            if "later" in match_dict["prep_post"]:
                return DateTimeInformation().set_as_after_datetime(message_day)

            if "earlier" in match_dict["prep_post"]:
                return DateTimeInformation().set_as_before_datetime(message_day)

        return DateTimeInformation().set_as_exact_datetime(message_day)

    def _singular_digit(self, date: str, message_day: datetime = None, **kwargs) -> Optional[DateTimeInformation]:
        """Convert a singular digit ('1') to a time of day as opposed to a date which is dateparse default

        Args:
            date: The date string to convert
            message_day: The day that the message was sent

        Returns:
            DateTimeInformation object or None

        """
        # Check for required args
        if message_day is None:
            return

        if len(date) <= 2 and date.isdigit():
            hour = int(date)
            if 0 < hour < 23:
                return DateTimeInformation().set_as_exact_datetime(message_day.replace(hour=hour))

    def _hour_range_month_date(
            self, date: str, message_day: datetime = None, **kwargs
    ) -> Optional[DateTimeInformation]:
        """Used to match specific apartment list pattern i.e. '3pm -4pm - Sep 11'

        Args:
            date: The date string to convert
            message_day: The day that the message was sent

        Returns:
            DateTimeInformation object or None

        """
        # Check for required args
        if message_day is None:
            return

        match = re.search(APARTMENT_DATE_LIST_PATTERN, date, re.IGNORECASE)
        if match:
            match_dict = match.groupdict()
            extracted_hour = self._time_qualifier_to_int(
                int(match_dict["hour1"]),
                self.am_to_pm_threshold,
                match_dict["time_of_day"],
            )

            day = int(match_dict["day"])
            month = MONTH_NUMS_LOOKUP[match_dict["month"]]
            year = message_day.year

            try:
                return DateTimeInformation().set_as_exact_datetime(datetime(year, month, day, extracted_hour))
            except ValueError:
                # There is the potential for super edge casey year wrap around
                return

    def _time_of_day(self, date: str, message_day: datetime = None, **kwargs) -> Optional[DateTimeInformation]:
        """Used to match time of day ranges like "Tomorrow - morning or afternoon"

        Args:
            date: the date string to convert
            message_day: day that the message was sent

        Returns:
            DateTimeInformation object or None

        """
        if message_day is None:
            return

        re_pattern = (
            rf"(?P<day_pre>today|tomorrow|{{self.month_abbrvs}}\s*\d{0,2})?\s*-*\s*"
            "(?P<time_of_day1>morning|afternoon|evening)\s*(or)?\s*"
            "(?P<time_of_day2>morning|afternoon|evening)?"
            "(?P<day_post>today|tomorrow)?"
        )
        match = re.search(re_pattern, date, re.IGNORECASE)

        if not match or (not match["day_pre"] and not match["day_post"]):
            return

        match_dict = match.groupdict()

        times_of_day = []
        if match_dict["time_of_day1"]:
            times_of_day.append(match_dict["time_of_day1"])
        if match_dict["time_of_day2"]:
            times_of_day.append(match_dict["time_of_day2"])
        times_of_day = sorted(times_of_day)

        parsed_date = message_day
        if match_dict["day_pre"] == "tomorrow" or match_dict["day_post"] == "tomorrow":
            parsed_date += timedelta(days=1)

        if times_of_day == ["morning"]:
            return DateTimeInformation().set_as_morning_datetime(parsed_date)
        elif times_of_day == ["afternoon"]:
            return DateTimeInformation().set_as_afternoon_datetime(parsed_date)
        elif times_of_day == ["afternoon", "morning"]:
            return DateTimeInformation().set_as_morning_afternoon_datetime(parsed_date)

    def _time_qualifier(self, date: str, dateparser_settings: Dict = None, **kwargs) -> Optional[DateTimeInformation]:
        """Date parser can't handle times with 'around', so replace with 'at'.

        Args:
            date: The date string to convert
            dateparser_settings: The date parser settings

        Returns:
            DateTimeInformation object or None

        """
        parsed_date = super(AppointmentDateConverter, self)._time_qualifier(date, dateparser_settings)

        if parsed_date:
            return parsed_date

        if "around" in date:
            date = date.replace("around", "at")
            parsed_date = dateparser.parse(date, settings=dateparser_settings)

        if parsed_date:
            if parsed_date.time() == time.min:
                return DateTimeInformation().set_as_date(parsed_date)
            return DateTimeInformation().set_as_exact_datetime(parsed_date)

    def _parse_hour_minute_str(self, hour_minute: Optional[str]) -> Optional[Tuple[int, int]]:
        """Parse string containing hour and potentially minute, optionally separated by colon.

        Args:
            hour_minute: Time like '9', '130'

        Returns:
            Extracted hour and minute

        """
        if not hour_minute:
            return

        if ":" in hour_minute:
            hour, minute = hour_minute.split(":")
            return int(hour), int(minute)

        if len(hour_minute) < 3:
            # times like 9, 12
            return int(hour_minute), 0

        if len(hour_minute) == 3:
            # times like 130, 945
            return int(hour_minute[:1]), int(hour_minute[1:3])

        # times like 1130, 1045
        return int(hour_minute[:2]), int(hour_minute[2:4])

    def _time_qualifier_to_int(self, time: int, am_pm_threshold: int, qualifier: Optional[str]) -> int:
        """Convert a time to lie within the am pm threshold with optional qualifier: am, pm

        Args:
            time: The extracted time
            am_pm_threshold: Before this time push am to pm
            qualifier: am or pm qulaifier

        Returns:
            Converted time

        """
        if qualifier:
            if qualifier == "pm" and time < 12:
                return time + 12

        if time < am_pm_threshold:
            return time + 12

        return time

    def _match_and_convert_day_specifier(self, date: str, message_day: datetime) -> Optional[datetime]:
        """Match a day-specifier and convert it to a datetime relative to the message_day

        Args:
            date: string containing the day specifier
            message_day: day that the message was sent

        Returns:
            datetime of day specified or None

        """
        # Pattern to catch day specifier
        day_pattern = (
            r"(?P<day>today|tomorrow|mon(day)?|tue(s|sday)?|wed(nesday)?|thu(rs|rsday)?|fri(day)?|sat(urday)?|sun(day)?)"
        )
        day_match = re.search(day_pattern, date, re.IGNORECASE)

        if day_match:
            day_match_dict = day_match.groupdict()
            # Get number of day specified
            if day_match_dict['day'] == 'tomorrow':
                day_to_number = message_day.weekday() + 1
            elif day_match_dict['day'].startswith('mon'):
                day_to_number = 0
            elif day_match_dict['day'].startswith('tue'):
                day_to_number = 1
            elif day_match_dict['day'].startswith('wed'):
                day_to_number = 2
            elif day_match_dict['day'].startswith('thu'):
                day_to_number = 3
            elif day_match_dict['day'].startswith('fri'):
                day_to_number = 4
            elif day_match_dict['day'].startswith('sat'):
                day_to_number = 5
            elif day_match_dict['day'].startswith('sun'):
                day_to_number = 6
            else:
                # Default to today (day message sent)
                day_to_number = message_day.weekday()

            # Calculate days from today until specified day
            days_until = day_to_number - message_day.weekday()
            if days_until < 0:
                days_until = 7 + days_until

            # Add number of days
            message_day = message_day + timedelta(days=days_until)

            return message_day

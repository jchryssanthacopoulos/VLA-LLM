"""Functions for creating human-readable messages."""

from datetime import datetime


def human_readable_month(date: str) -> str:
    """Convert date in YYYY-MM-DD format to human-readable format.

    Args:
        date: Date in YYYY-MM-DD format

    Returns:
        Returns date like March 1st

    """
    datetime_obj = datetime.strptime(date, '%Y-%m-%d')
    return human_readable_month_from_datetime(datetime_obj)


def human_readable_month_from_datetime(datetime_obj: datetime) -> str:
    """Convert datetime object to human-readable format.

    Args:
        datetime_obj: Datetime object

    Returns:
        Returns date like March 1st

    """
    if not datetime_obj:
        return ""

    return datetime_obj.strftime('%B') + " " + add_number_suffix(datetime_obj.day)


def human_readable_cost(cost: str) -> str:
    """Convert string representing cost like '200.00' to format needed for display.

    Args:
        cost: String representing cost

    Returns:
        Formatted cost

    """
    cost_float = float(cost)

    if cost_float.is_integer():
        # format with commas every thousand
        return "{:,}".format(int(cost_float))

    # format with commas and two decimal places
    return "{:,.2f}".format(cost_float)


def add_number_suffix(n: int) -> str:
    """Format number to number with suffix.

    For example: 1 becomes 1st, 2 become 2nd, and so on

    Args:
        n: A number

    Returns:
        Number with suffix

    """
    return str(n) + 'tsnrhtdd'[n % 5 * (n % 100 ^ 15 > 4 > n % 10)::4]

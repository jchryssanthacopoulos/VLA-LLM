"""Place for configuration variables."""

import os

from dotenv import load_dotenv


# inject environment variables into the environment
load_dotenv()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


CHUCK_API_KEY = os.getenv("CHUCK_API_KEY", "")


MAX_AVAILABLE_APPOINTMENT_TIMES_TO_SHOW = 3

"""Main entry point into the server."""

from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from VLA_LLM import prompts
from VLA_LLM.agents import ChatConversationalVLAAgent
from VLA_LLM.api import cancel_appointment
from VLA_LLM.api import delete_client_preferences
from VLA_LLM.api import enable_vla
from VLA_LLM.api import get_client_appointments
from VLA_LLM.api import get_community_info
from VLA_LLM.community_info import community_dict_to_prompt
from VLA_LLM.tools import AppointmentSchedulerAndAvailabilityTool
from VLA_LLM.tools import CurrentTimeTool


app = FastAPI()

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryVLAInputs(BaseModel):
    client_id: int
    group_id: int
    community_id: int
    api_key: str
    message: str
    message_medium: Optional[str]


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/query-virtual-agent/")
async def query_virtual_agent(inputs: QueryVLAInputs):
    """Query the LLM-based VLA for a response for given client and group IDs.

    Args:
        inputs: VLA inputs like client ID, group ID, community ID, Chuck API key, and prospect message

    Returns:
        VLA response

    """
    # get community info prompt
    community_info = get_community_info(inputs.community_id)
    community_info_prompt = community_dict_to_prompt(community_info)

    # most deterministic results
    temperature = 0

    tools = [
        CurrentTimeTool(),
        AppointmentSchedulerAndAvailabilityTool(
            client_id=inputs.client_id, group_id=inputs.group_id, api_key=inputs.api_key
        )
    ]

    agent = ChatConversationalVLAAgent(temperature, tools)

    prompt_template = (
        f"{prompts.prompt_two_tool_explicit.format(community_info=community_info_prompt)}\n\n"
        "Here is the prospect message:\n\n{prospect_message}"
    )

    response = agent.agent_chain.run(input=prompt_template.format(prospect_message=inputs.message))

    return {
        'response': {
            'text': [response]
        }
    }


class ResetVLAInputs(BaseModel):
    client_id: int
    group_id: int
    api_key: str


@app.post("/reset-virtual-agent/client/")
async def reset_virtual_agent_client(inputs: ResetVLAInputs):
    """Reset virtual agent for client.

    Args:
        inputs: Inputs for resetting client

    Returns:
        VLA response

    """
    # clear preferences on client's guest card and enable VLA
    delete_client_preferences(inputs.client_id)
    enable_vla(inputs.client_id, inputs.group_id)

    # delete appointments
    appointments = get_client_appointments(inputs.client_id, inputs.api_key)
    for appt in appointments:
        cancel_appointment(appt['id'], inputs.api_key)

    return {
        'response': {
            'message': 'success.'
        }
    }

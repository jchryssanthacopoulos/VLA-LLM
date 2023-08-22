"""Main entry point into the server."""

import json
import re
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain.schema.messages import HumanMessage
from langchain.schema.messages import AIMessage
from langchain.schema.output_parser import OutputParserException
from pydantic import BaseModel
from redis_om import get_redis_connection
from redis_om import HashModel


from VLA_LLM import prompts
from VLA_LLM.agents import ChatConversationalVLAAgent
from VLA_LLM.api import cancel_appointment
from VLA_LLM.api import delete_client_preferences
from VLA_LLM.api import enable_vla
from VLA_LLM.api import get_client_appointments
from VLA_LLM.api import get_community_info
from VLA_LLM.community_info import community_dict_to_prompt
from VLA_LLM.tools import AppointmentCancelerTool
from VLA_LLM.tools import AppointmentSchedulerAndAvailabilityTool
from VLA_LLM.tools import CurrentTimeTool


app = FastAPI()

redis = get_redis_connection()


origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


class ClientConversationHistory(HashModel):
    client_id: int
    community_id: int
    conversation_history: str


class QueryVLAInputs(BaseModel):
    client_id: int
    group_id: int
    community_id: int
    api_key: str
    message: str
    message_medium: Optional[str]


@app.post("/query-virtual-agent/")
async def query_virtual_agent(inputs: QueryVLAInputs):
    """Query the LLM-based VLA for a response for given client and group IDs.

    Args:
        inputs: VLA inputs like client ID, group ID, community ID, Chuck API key, and prospect message

    Returns:
        VLA response

    """
    # make sure the VLA is enabled
    enable_vla(inputs.client_id, inputs.group_id)

    redis_key = f"{inputs.community_id}:{inputs.client_id}"
    redis_state = redis.get(redis_key)

    conversation_history = json.loads(redis_state) if redis_state else []

    # get community info prompt
    community_info = get_community_info(inputs.community_id)
    community_info_prompt = community_dict_to_prompt(community_info)

    tools = [
        CurrentTimeTool(),
        AppointmentSchedulerAndAvailabilityTool(
            client_id=inputs.client_id,
            group_id=inputs.group_id,
            api_key=inputs.api_key,
            community_timezone=community_info.get('timezone')
        ),
        AppointmentCancelerTool(
            client_id=inputs.client_id,
            api_key=inputs.api_key
        )
    ]

    # most deterministic results
    temperature = 0

    # create memory
    messages = []
    for interaction in conversation_history:
        messages.extend([
            HumanMessage(content=interaction['human_message']),
            AIMessage(content=interaction['ai_message'])
        ])

    prompt_template = prompts.prompt_two_tool_explicit.format(community_info=community_info_prompt)
    agent = ChatConversationalVLAAgent(temperature, tools, messages, prompt_template)

    try:
        response = agent.agent_chain.run(input=inputs.message)
    except OutputParserException as e:
        match = re.match("Could not parse LLM output: (?P<message>.*)", str(e))
        if match:
            response = match.groupdict()['message']
        else:
            # fall back to default
            response = "I'm sorry, but I couldn't quite understand that. Can you please repeat your question?"

    # update and save conversation history
    conversation_history.append({
        'human_message': inputs.message,
        'ai_message': response
    })
    redis.set(redis_key, json.dumps(conversation_history))

    return {
        'response': {
            'text': [response]
        }
    }


class ResetVLAInputs(BaseModel):
    client_id: int
    community_id: int
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

    # clear redis cache
    redis_key = f"{inputs.community_id}:{inputs.client_id}"
    redis.delete(redis_key)

    return {
        'response': {
            'message': 'success.'
        }
    }

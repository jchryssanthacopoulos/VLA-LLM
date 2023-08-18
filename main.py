"""Main entry point into the server."""

import json
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain.schema.messages import HumanMessage
from langchain.schema.messages import AIMessage
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
    redis_key = f"{inputs.community_id}:{inputs.client_id}"
    redis_state = redis.get(redis_key)

    conversation_history = json.loads(redis_state) if redis_state else []

    # get community info prompt
    community_info = get_community_info(inputs.community_id)
    community_info_prompt = community_dict_to_prompt(community_info)

    tools = [
        CurrentTimeTool(),
        AppointmentSchedulerAndAvailabilityTool(
            client_id=inputs.client_id, group_id=inputs.group_id, api_key=inputs.api_key
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

    agent = ChatConversationalVLAAgent(temperature, tools, messages)

    if not conversation_history:
        # if there is no conversation history, add community data and instructions to the prompt
        prompt_template = (
            f"{prompts.prompt_two_tool_explicit.format(community_info=community_info_prompt)}\n\n"
            "Here is the prospect message:\n\n{prospect_message}"
        )
        response = agent.agent_chain.run(input=prompt_template.format(prospect_message=inputs.message))
    else:
        response = agent.agent_chain.run(input=inputs.message)

    # update and save conversation history
    all_messages = agent.agent_chain.memory.chat_memory.messages
    conversation_history.append({
        'human_message': all_messages[-2].content,
        'ai_message': all_messages[-1].content
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
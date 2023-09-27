"""Main entry point into the server."""

from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from redis_om import get_redis_connection
from redis_om import HashModel


from VLA_LLM.agents import ChatConversationalVLAAgent
from VLA_LLM.api import cancel_appointment
from VLA_LLM.api import delete_client_preferences
from VLA_LLM.api import enable_vla
from VLA_LLM.api import get_client_appointments
from VLA_LLM.state import State


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
    debug: Optional[bool]


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

    # get conversation history
    messages = State(inputs.community_id, inputs.client_id).get_memory_of_messages()

    # create agent
    agent = ChatConversationalVLAAgent(
        inputs.client_id,
        inputs.group_id,
        inputs.community_id,
        inputs.api_key,
        messages,
        temperature=0  # most deterministic results
    )

    # check whether the agent should disable
    should_disable = agent.should_disable(inputs.message)
    response = agent.respond(inputs.message) if not should_disable else 'Disable VLA'

    # reload state (in case tools have updated it)
    agent_state = State(inputs.community_id, inputs.client_id)

    # add debug information
    response_with_debug = response
    if inputs.debug:
        actions = agent_state.get_current_actions()
        if actions:
            response_with_debug += f"\n\nACTIONS:\n\t{', '.join(actions)}"

    # save state with new conversation history
    agent_state.update_conversation_history(inputs.message, response).increment_message_count().save()

    return {
        'response': {
            'text': [response_with_debug],
            'disable': should_disable
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

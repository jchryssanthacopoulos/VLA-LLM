"""Main entry point into the server."""

from fastapi import FastAPI
from pydantic import BaseModel

from VLA_LLM import prompts
from VLA_LLM.agents import ChatConversationalVLAAgent
from VLA_LLM.api import get_community_info
from VLA_LLM.community_info import community_dict_to_prompt
from VLA_LLM.tools import AppointmentSchedulerAndAvailabilityTool
from VLA_LLM.tools import CurrentTimeTool


app = FastAPI()


class QueryVLAInputs(BaseModel):
    community_id: int
    api_key: str
    message: str


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/query-vla-llm/client_id/{client_id}/group_id/{group_id}")
async def query_vla_llm(client_id: int, group_id: int, inputs: QueryVLAInputs):
    """Query the LLM-based VLA for a response for given client and group IDs.

    Args:
        client_id: ID of client
        group_id: ID of group
        inputs: Other VLA inputs like community ID, Chuck API key, and prospect message

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
        AppointmentSchedulerAndAvailabilityTool(client_id=client_id, group_id=group_id, api_key=inputs.api_key)
    ]

    agent = ChatConversationalVLAAgent(temperature, tools)

    prompt_template = (
        f"{prompts.prompt_two_tool_explicit.format(community_info=community_info_prompt)}\n\n"
        "Here is the prospect message:\n\n{prospect_message}"
    )

    response = agent.agent_chain.run(input=prompt_template.format(prospect_message=inputs.message))

    return {
        'response': response
    }

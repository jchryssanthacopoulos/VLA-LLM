"""Classes for several types of agents."""

import re
from typing import List

from langchain import LLMChain
from langchain.agents import AgentType
from langchain.agents import AgentExecutor
from langchain.agents import initialize_agent
from langchain.agents import ZeroShotAgent
from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories.in_memory import ChatMessageHistory
from langchain.schema.output_parser import OutputParserException
from langchain.tools import BaseTool

from VLA_LLM import prompts
from VLA_LLM.api import get_community_info
from VLA_LLM.community_info import community_dict_to_prompt
from VLA_LLM.config import OPENAI_API_KEY
from VLA_LLM.tools.appointments import AppointmentCancelerTool
from VLA_LLM.tools.appointments import AppointmentSchedulerAndAvailabilityTool
from VLA_LLM.tools.appointments import CurrentTimeTool
from VLA_LLM.tools.listings import AvailableApartmentsTool
from VLA_LLM.tools.preferences import UpdatePreferencesTool


class ZeroShotVLAAgent:

    def __init__(self, temperature: float, prefix: str, tools: List[BaseTool]):
        """Create a zero-shot VLA agent.

        Args:
            temperature: Temperature to use in underlying LLM
            prefix: Prompt to use that includes instructions and templates for community information
            tools: List of tools the agent has access to

        """
        suffix = (
            "Chat history:\n\n"
            "{chat_history}\n\n"
            "Prospect question:\n\n"
            "{input}\n\n"
            "{agent_scratchpad}"
        )
        prompt = ZeroShotAgent.create_prompt(
            tools,
            prefix=prefix,
            suffix=suffix,
            input_variables=["input", "chat_history", "agent_scratchpad"]
        )

        llm = OpenAI(temperature=temperature, openai_api_key=OPENAI_API_KEY)

        llm_chain = LLMChain(llm=llm, prompt=prompt)
        agent = ZeroShotAgent(llm_chain=llm_chain, tools=tools, verbose=True)

        # ability for agent to keep track of conversation history
        memory = ConversationBufferMemory(memory_key="chat_history")

        self.agent_chain = AgentExecutor.from_agent_and_tools(agent=agent, tools=tools, verbose=True, memory=memory)


class ChatConversationalVLAAgent:

    FALLBACK_RESPONSE = "I'm sorry, but I couldn't quite understand that. Can you please repeat your question?"

    def __init__(
            self, client_id: int, group_id: int, community_id: int, api_key: str, message_hist: List, temperature: float
    ):
        """Create a chat conversational VLA agent.

        Args:
            client_id: ID of client
            group_id: ID of group
            community_id: ID of community
            api_key: Chuck API key to call the v2 API
            message_hist: List of past messages to seed the memory
            temperature: Temperature to use in underlying LLM

        """
        llm = ChatOpenAI(temperature=temperature, openai_api_key=OPENAI_API_KEY)

        # get community info prompt
        community_info = get_community_info(community_id)
        community_timezone = community_info.get('timezone')
        community_info_prompt = community_dict_to_prompt(community_info)

        prompt_template = prompts.prompt_tools_minimal.format(community_info=community_info_prompt)

        chat_tools = [
            AppointmentSchedulerAndAvailabilityTool(
                client_id=client_id,
                group_id=group_id,
                api_key=api_key,
                community_timezone=community_info.get('timezone')
            ),
            AppointmentCancelerTool(
                client_id=client_id,
                api_key=api_key
            ),
            AvailableApartmentsTool(
                client_id=client_id,
                community_id=community_id,
                community_timezone=community_timezone
            )
        ]

        memory = ConversationBufferMemory(
            memory_key="chat_history",
            chat_memory=ChatMessageHistory(messages=message_hist),
            return_messages=True
        )

        self.chat_agent = initialize_agent(
            agent='chat-conversational-react-description',
            tools=[], llm=llm, verbose=True, memory=memory, max_iterations=3
        )

        new_prompt = self.chat_agent.agent.create_prompt(
            system_message=prompt_template,
            tools=chat_tools
        )

        self.chat_agent.agent.llm_chain.prompt = new_prompt
        self.chat_agent.tools = chat_tools

        # create function calling agent
        func_tools = [
            UpdatePreferencesTool(client_id=client_id, community_timezone=community_info.get('timezone'))
        ]

        self.function_agent = initialize_agent(
            func_tools, llm, agent=AgentType.OPENAI_FUNCTIONS, verbose=True, max_iterations=3
        )

    def respond(self, message: str) -> str:
        """Respond to given inquiry.

        Args:
            message: Prospect message

        Returns:
            Agent response

        """
        try:
            response = self.chat_agent.run(input=message)
        except OutputParserException as e:
            match = re.match("Could not parse LLM output: (?P<message>(.|\n)*)", str(e))
            if match:
                message = match.groupdict().get('message')
                response = message if message else self.FALLBACK_RESPONSE
            else:
                # fall back to default
                response = self.FALLBACK_RESPONSE

        if response == 'Agent stopped due to iteration limit or time limit.':
            response = self.FALLBACK_RESPONSE

        # call function agent
        self.function_agent.run(input=message)

        return response

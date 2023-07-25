"""Classes for several types of agents."""

from typing import List

from langchain import LLMChain
from langchain.agents import AgentType
from langchain.agents import AgentExecutor
from langchain.agents import initialize_agent
from langchain.agents import ZeroShotAgent
from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
from langchain.memory import ConversationBufferMemory
from langchain.tools import BaseTool

from VLA_LLM.config import OPENAI_API_KEY


class ZeroShotVLAAgent:

    def __init__(self, temperature: float, prefix: str, community_info: str, tools: List[BaseTool]):
        """Create a zero-shot VLA agent.

        Args:
            temperature: Temperature to use in underlying LLM
            prefix: Prompt to use that includes instructions and templates for community information
            tools: List of tools the agent has access to

        """
        prefix = prefix.format(community_info=community_info)

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

    def __init__(self, temperature: float, tools: List[BaseTool]):
        llm = ChatOpenAI(temperature=temperature, openai_api_key=OPENAI_API_KEY)

        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

        self.agent_chain = initialize_agent(
            tools, llm, agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION, verbose=True, memory=memory
        )

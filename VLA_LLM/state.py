"""Methods for getting, updating, and setting state."""

from copy import deepcopy
import json
from typing import List

from langchain.schema.messages import AIMessage
from langchain.schema.messages import HumanMessage
from redis_om import get_redis_connection


class State:
    """Class for representing the VLA state."""

    NUM_PROSPECT_MESSAGES = 'num_prospect_messages'
    CONVERSATION_HISTORY = 'conversation_history'
    ACTIONS = 'actions'

    DEFAULT_STATE = {
        NUM_PROSPECT_MESSAGES: 0,
        CONVERSATION_HISTORY: [],
        ACTIONS: {}
    }

    def __init__(self, community_id: int, client_id: int):
        """Get state for given community and client ID.

        Args:
            community_id: ID of community
            client_id: ID of client

        """
        self.redis = get_redis_connection()
        self.redis_key = f"{community_id}:{client_id}"

        redis_state = self.redis.get(self.redis_key)

        self.agent_state = json.loads(redis_state) if redis_state else deepcopy(self.DEFAULT_STATE)

    def get_current_actions(self) -> List:
        """Get set of actions for current prospect message."""
        num_prospect_messages = str(self.agent_state[self.NUM_PROSPECT_MESSAGES])
        return self.agent_state[self.ACTIONS].get(num_prospect_messages)

    def get_memory_of_messages(self) -> List:
        """Get memory of human and AI messages."""
        messages = []

        for interaction in self.agent_state[self.CONVERSATION_HISTORY]:
            messages.extend([
                HumanMessage(content=interaction['human_message']),
                AIMessage(content=interaction['ai_message'])
            ])

        return messages

    def set_current_actions(self, actions: List):
        """Set the actions for the current message to given actions.

        Args:
            actions: Actions to set

        """
        num_prospect_messages = str(self.agent_state[self.NUM_PROSPECT_MESSAGES])
        self.agent_state[self.ACTIONS][num_prospect_messages] = actions

    def update_actions(self, action: str):
        """Update state with given action.

        Args:
            action: Action to update state with

        """
        current_actions = self.get_current_actions()

        if current_actions:
            if action not in current_actions:
                # check for repeated action
                current_actions.append(action)
        else:
            current_actions = [action]

        self.set_current_actions(current_actions)

        return self

    def update_conversation_history(self, prospect_message: str, ai_response: str):
        """Update conversation history with prospect and AI message.

        Args:
            prospect_message: Latest message from prospect
            ai_response: Latest response from AI

        """
        self.agent_state[self.CONVERSATION_HISTORY].append({
            'human_message': prospect_message,
            'ai_message': ai_response
        })
        return self

    def increment_message_count(self):
        """Increment the prospect message count by one."""
        self.agent_state[self.NUM_PROSPECT_MESSAGES] += 1
        return self

    def save(self):
        """Save state back to cache."""
        self.redis.set(self.redis_key, json.dumps(self.agent_state))

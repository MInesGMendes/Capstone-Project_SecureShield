# Import necessary classes and modules for chatbot functionality
import sys
sys.path.append('SecureShield/secure_shield.db')
# Connect to the SQLite database
#con = sqlite3.connect("SecureShield/secure_shield.db")
#cursor = con.cursor()
from typing import Callable, Dict, Optional

from .memory import MemoryManager

from ..Chains.Prompt_Injection_Tolerance import IsPromptInjection

from Chains.Get_Claim_Info import GetClaimInfoChain
from Chains.Get_Policy_Info import GetPolicyInfoChain
from Chains.Update_Claim_Status import UpdateClaimStatusChain
#from chatbot.chains.router import RouterChain
from router.loader import load_intention_classifier
from Chains.Chitchat import ChitChatResponseChain, ChitChatClassifierChain
from rag import RagChain

from langchain_core.runnables.history import RunnableWithMessageHistory


class MainChatbot:
    """A bot that handles customer service interactions by processing user inputs and
    routing them through configured reasoning and response chains.
    """

    def __init__(self):
        """Initialize the bot with session and language model configurations."""
        # Initialize the memory manager to manage session history
        self.memory = MemoryManager()

        # Map intent names to their corresponding reasoning and response chains
        self.chain_map = {
            "Update_Claim_Status": self.add_memory_to_runnable(UpdateClaimStatusChain()),
            "Get_Claim_Info": self.add_memory_to_runnable(GetClaimInfoChain()),
            "Get_Policy_Info": self.add_memory_to_runnable(GetPolicyInfoChain()),
            "chitchat": self.add_memory_to_runnable(ChitChatResponseChain()),
            "chitchat_class": ChitChatClassifierChain()
        }
        

        # Map of intentions to their corresponding handlers
        self.intent_handlers: Dict[Optional[str], Callable[[Dict[str, str]], str]] = {
            "Update_Claim_Status": self.handle_update_claim_info,
            "Get_Claim_Info": self.handle_get_claim_info,
            "Get_Policy_Info": self.handle_get_policy_info,
            "Chitchat": self.handle_chitchat_intent
        }

        # Load the intention classifier to determine user intents
        self.intention_classifier = load_intention_classifier()

    def user_login(self, username: str, conversation_id: str) -> None:
        """Log in a user by setting the user and conversation identifiers.

        Args:
            username: Identifier for the user.
            conversation_id: Identifier for the conversation.
        """
        self.username = username
        self.conversation_id = conversation_id
        self.memory_config = {
            "configurable": {
                "conversation_id": self.conversation_id,
                "user_id": self.username,
            }
        }

    def add_memory_to_runnable(self, original_runnable):
        """Wrap a runnable with session history functionality.

        Args:
            original_runnable: The runnable instance to which session history will be added.

        Returns:
            An instance of RunnableWithMessageHistory that incorporates session history.
        """
        return RunnableWithMessageHistory(
            original_runnable,
            self.memory.get_session_history,  # Retrieve session history
            input_messages_key="user_input",  # Key for user inputs
            history_messages_key="chat_history",  # Key for chat history
            history_factory_config=self.memory.get_history_factory_config(),  # Config for history factory
        ).with_config(
            {
                "run_name": original_runnable.__class__.__name__
            }  # Add runnable name for tracking
        )

    def get_chain(self, intent: str):
        """Retrieve the reasoning and response chains based on user intent.

        Args:
            intent: The identified intent of the user input.

        Returns:
            A tuple containing the reasoning and response chain instances for the intent.
        """
        return self.chain_map[intent]
    

    def get_user_intent(self, user_input: Dict):
        """Classify the user intent based on the input text.

        Args:
            user_input: The input text from the user.

        Returns:
            The classified intent of the user input.
        """
        # Retrieve possible routes for the user's input using the classifier
        intent_routes = self.intention_classifier.retrieve_multiple_routes(
            user_input["customer_input"]
        )

        # Handle cases where no intent is identified
        if len(intent_routes) == 0:
            return None
        else:
            intention = intent_routes[0].name  # Use the first matched intent

        # Validate the retrieved intention and handle unexpected types
        if intention is None:
            return None
        elif isinstance(intention, str):
            return intention
        else:
            # Log the intention type for unexpected cases
            intention_type = type(intention).__name__
            print(
                f"I'm sorry, I didn't understand that. The intention type is {intention_type}."
            )
            return None
        

    def handle_update_claim_info(self, user_input: Dict[str, str]) -> str:
        """Handle the update profile info intent by processing user input and providing a response.

        Args:
            user_input: The input text from the user.

        Returns:
            The content of the response after processing through the chains.
        """
        # Retrieve reasoning and response chains
        chain = self.get_chain("Update_Claim_Status")
        user_input['chat_history'] = self.memory.get_session_history(
            self.username, self.conversation_id
        )
        # Generate a response using the output of the reasoning chain
        response = chain.invoke(user_input, config=self.memory_config)

        return response

    def handle_get_claim_info(self, user_input: Dict[str, str]) -> str:
        """Handle the insert new fav author/genre intent by processing user input and providing a response.

        Args:
            user_input: The input text from the user.

        Returns:
            The content of the response after processing through the chains.
        """
        # Retrieve reasoning and response chains for the insert new fav author/genre intent
        chain = self.get_chain("Get_Claim_Info")
        user_input['chat_history'] = self.memory.get_session_history(
            self.username, self.conversation_id
        )
        # Generate a response using the output of the reasoning chain
        response = chain.invoke(user_input, config=self.memory_config)

        return response

    def handle_rag(self, user_input: Dict[str, str]) -> str:
        """Handle the RAG intent by processing user input and providing a response.

        Args:
            user_input: The input text from the user.

        Returns:
            The content of the response after processing through the chains.
        """
        # Retrieve reasoning and response chains for the RAG intent
        rag = RagChain(username=self.username)
        
        # Generate a response using the output of the reasoning chain
        response = rag.run_chain(question=user_input['user_input'])

        return response

    def handle_chitchat_intent(self, user_input: Dict[str, str]) -> str:
        """Handle chitchat intents

        Args:
            user_input: The input text from the user.

        Returns:
            The content of the response after processing through the new chain.
        """
        # Retrieve reasoning and response chains for the chitchat intent
        chain = self.get_chain("Chitchat")

        # Generate a response using the output of the reasoning chain
        response = chain.invoke(user_input, config=self.memory_config)

        return response
    
    def handle_unknown_intent(self, user_input: Dict[str, str]) -> str:
        """Handle unknown intents by providing a chitchat response.

        Args:
            user_input: The input text from the user.

        Returns:
            The content of the response after processing through the new chain.
        """
        possible_intention = [
            "Product Information",
            "Create Order",
            "Order Status",
            "Support Information",
            "Chitchat",
        ]

        chitchat_reasoning_chain, _ = self.get_chain("chitchat")

        input_message = {}

        input_message["customer_input"] = user_input["customer_input"]
        input_message["possible_intentions"] = possible_intention
        input_message["chat_history"] = self.memory.get_session_history(
            self.user_id, self.conversation_id
        )

        reasoning_output1 = chitchat_reasoning_chain.invoke(input_message)

        if reasoning_output1.chitchat:
            print("Chitchat")
            return self.handle_chitchat_intent(user_input)
        else:
            router_reasoning_chain2, _ = self.get_chain("router")
            reasoning_output2 = router_reasoning_chain2.invoke(input_message)
            new_intention = reasoning_output2.intent
            print("New Intention:", new_intention)
            new_handler = self.intent_handlers.get(new_intention)
            return new_handler(user_input)
        
    def save_memory(self) -> None:
        """Save the current memory state of the bot."""
        self.memory.save_session_history(self.username, self.conversation_id)

    def process_user_input(self, user_input: Dict[str, str]) -> str:
        """Process user input by routing through the appropriate intention pipeline.

        Args:
            user_input: The input text from the user.

        Returns:
            The content of the response after processing through the chains.
        """
        # Detect if there are dangers of prompt injection in the user input
        prompt_injection_chain = IsPromptInjection()
        result = prompt_injection_chain.invoke(user_input).is_prompt_injection

        if not result:
            # Classify the user's intent based on their input
            intention = self.get_user_intent(user_input)

            # Route the input based on the identified intention
            handler = self.intent_handlers.get(intention, self.handle_unknown_intent)
            return handler(user_input)
        else:
            return "It was detected prompt injection risks or malicious content in your input."

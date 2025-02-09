from langchain.output_parsers import PydanticOutputParser
from langchain.schema.runnable.base import Runnable
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field

from Chains.Base import PromptTemplate, generate_prompt_templates


class ChitChatResponseChain(Runnable):
    def __init__(self, llm, memory=True):
        super().__init__()

        self.llm = llm
        prompt_template = PromptTemplate(
            system_template=""" 
            As an AI language model engaging in friendly chitchat for SecureShield, your main objectives are to maintain a conversational tone.
            Limit you answer to a maximum of 30 words.
            Here's how you should approach these interactions:

            1. **Tone and Engagement:**
            - Use a warm, friendly, and conversational tone.
            - Keep the conversation light and welcoming.

            2. **Personalization:**
            - Leverage previous conversation history to personalize your responses and build rapport.
            - Show genuine interest in the user's interactions by recalling past preferences or inquiries related to SecureShield.

            3. **Focus on SecureShield's Core Areas:**
            - Gently steer the conversation towards topics relevant to SecureShield whenever appropriate, such as by sharing interesting facts about insurance trends.

            4. **Handling Irrelevant Questions:**
            - Politely redirect general or unrelated questions back to SecureShield's focus. 
            - For example, if asked, 'What is the capital of Portugal?', you might respond with, 
              'As an insurance related chatbot i don't have that information.'

            5. **Building Rapport:**
            - Foster a sense of community and trust, making users feel appreciated within the SecureShield environment.

            Your ultimate goal is to support user engagement with SecureShield using your friendly 
            demeanor and strategic conversational techniques.
            
            Here is the user input:
            {customer_input}
            """,
            human_template="Customer Query: {customer_input}",
        )

        self.prompt = generate_prompt_templates(prompt_template, memory)
        self.output_parser = StrOutputParser()

        self.chain = self.prompt | self.llm | self.output_parser

    def invoke(self, input, config=None, **kwargs):
        return self.chain.invoke(input, config=config)


class ChitChatClassifier(BaseModel):

    chitchat: bool = Field(
        description="""Chitchat is defined as:
        - Conversations that are informal, social, or casual in nature.
        - Topics that do not directly relate to insurance, update claims status or obtaining information about claims or policies.
        - Examples include greetings, jokes, small talk, or personal inquiries unrelated to claims or policies.
        If the user message falls under this category, set 'chitchat' to True.""",
    )


class ChitChatClassifierChain(Runnable):
    def __init__(self, llm, memory=False):
        super().__init__()

        self.llm = llm
        prompt_template = PromptTemplate(
            system_template=""" 
            You are specialized in distinguishing between chitchat and insurance-related user messages.
            Your task is to analyze each incoming user message and determine if it falls under 'chitchat'. 
            Consider the Context:
            - Analyze the user's message in the context of the entire chat history.

            Here is the user input:
            {customer_input}

            Here is the chat history:
            {chat_history}

            Output Output your results clearly on the following format:  
            {format_instructions}
            """,
            human_template="Customer Query: {customer_input}",
        )

        self.prompt = generate_prompt_templates(prompt_template, memory=memory)

        self.output_parser = PydanticOutputParser(pydantic_object=ChitChatClassifier)
        self.format_instructions = self.output_parser.get_format_instructions()
        self.chain = (self.prompt | self.llm | self.output_parser).with_config(
            {"run_name": self.__class__.__name__}
        )  # Add a run name to the chain on LangSmith

        self.chain = self.prompt | self.llm | self.output_parser

    def invoke(self, input, config=None, **kwargs) -> ChitChatClassifier:
        result = self.chain.invoke(
            {
                "customer_input": input["customer_input"],
                "chat_history": input["chat_history"],
                "format_instructions": self.format_instructions,
            },
        )
        return result

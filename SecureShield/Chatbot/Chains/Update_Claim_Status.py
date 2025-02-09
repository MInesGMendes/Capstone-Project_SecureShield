from Chains.Base import PromptTemplate, generate_prompt_templates
from pydantic import BaseModel
from langchain import callbacks
from langchain.tools import BaseTool
from langchain.schema.runnable.base import Runnable
from langchain.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from typing import Type
import sqlite3
from dotenv import load_dotenv

load_dotenv()

# Define data models for the claim information
class ClaimUpdate(BaseModel):
    claim_id: int
    status: str

# Define a class to extract claim ID and status from the user input
class ExtractClaimToUpdate(Runnable):
    def __init__(self, llm, memory=False):
        super().__init__()
        self.llm = llm

        prompt_template = PromptTemplate(
            system_template=""" 
            You are a part of the database manager team for a insurance company platform. 
            Given the user input, your task is to identify the claim id of the claim that the employee wants to update,\
            and which status they want update to.
            Return the claim id and the status.

            The system will search for the claim id in the database based on your extraction from the user input. 
            Ensure you extract the claim ID and the status as accurately as possible.
            You can also take into consideration the chat history between you and the user.
            
            Here is the user input:
            {user_input}

            Chat History:
            {chat_history}
            
            {format_instructions}
            """,
            human_template="user input: {user_input}",
        )

        self.prompt = generate_prompt_templates(prompt_template, memory=memory)
        self.output_parser = PydanticOutputParser(pydantic_object=ClaimUpdate)
        self.format_instructions = self.output_parser.get_format_instructions()

        self.chain = self.prompt | self.llm | self.output_parser

    def invoke(self, inputs):
        result = self.chain.invoke(
            {
                "user_input": inputs["user_input"],
                "chat_history": inputs["chat_history"],
                "format_instructions": self.format_instructions,
            }
        )
        return result

# Define the class to perform the claim status update operation
class UpdateClaimStatusOutput(BaseModel):
    output: str

class UpdateClaimStatusChain(Runnable):
    def __init__(self, memory: bool = True) -> str:
        self.llm = ChatOpenAI(model="gpt-4", temperature=0)
        self.extract_chain = ExtractClaimToUpdate(self.llm)
        
        prompt_bot_return = PromptTemplate( 
            system_template = """
            You are a part of the database manager team for insurance company called SecureShield. 
            The employee asked for an update in a claim status. 

            There are 3 possible outcomes:
            - The claim status was successfully updated ('success').
            - The claim was not found ('not_found').
            - There was an error updating the claim status ('error').

            Given the employee input, the chat history and the operation status, your task is to return to the employee a message stating the result of the operation in a friendly way.
            Do not greet the user in the beggining of the message as this is already in the middle of the conversation.
            
            Here is the user input:
            {user_input}

            Chat History:
            {chat_history}

            Status of the operation:
            {status}

            {format_instructions}
            """,
            human_template="user input: {user_input}",
        )

        self.prompt = generate_prompt_templates(prompt_bot_return, memory=memory)
        self.output_parser = PydanticOutputParser(pydantic_object=UpdateClaimStatusOutput)
        self.format_instructions = self.output_parser.get_format_instructions()
        self.chain = (self.prompt | self.llm | self.output_parser).with_config({"run_name": self.__class__.__name__})

    def invoke(self, user_input, config):
        claim_info = self.extract_chain.invoke(user_input)
        claim_id = claim_info.claim_id
        status = claim_info.status

        # Update claim status in the database
        con = sqlite3.connect("SecureShield/secure_shield.db")
        cursor = con.cursor()

        cursor.execute(f"SELECT claim_id FROM Claims WHERE claim_id = ?", (claim_id,))
        query_results = cursor.fetchone()

        if not query_results: 
            self.status = 'not_found'
        else:
            try:
                cursor.execute(
                    "UPDATE Claims SET status = ? WHERE claim_id = ?",
                    (status, claim_id)
                )
                con.commit()
                self.status = 'success'
            except sqlite3.OperationalError as e:
                print(f"Error: {e}")
                self.status = 'error'
            finally:
                cursor.close()
                con.close()

        #Generate response based on status
        response = self.chain.invoke({
            "user_input": user_input['user_input'],
            'chat_history': user_input['chat_history'], 
            "status": self.status,
            "format_instructions": self.format_instructions
        })

        return response.output


#config = {"configurable": {
  #              "conversation_id": 67,
   #             "user_id": 3468}}
#search_input = UpdateClaimStatusChain()
#user_input = {
 #   'user_input': "update claim 2 to approved",
  #  'chat_history': []#"Previous context of the conversation"
#}
#response = search_input.invoke(user_input=user_input, config=config)
#print(response)
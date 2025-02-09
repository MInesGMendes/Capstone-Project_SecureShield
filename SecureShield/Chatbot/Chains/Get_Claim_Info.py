import sqlite3
from Chains.Base import PromptTemplate, generate_prompt_templates
from langchain.schema.runnable.base import Runnable
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel
from typing import Type
from langchain_community.tools import BaseTool
from dotenv import load_dotenv

load_dotenv()

class ClaimQueryType(BaseModel):
    query_type: str
    value: str
    num_results: int = 5  # Default to 5 results if not specified

class ExtractClaimQuery(Runnable):
    def __init__(self, llm, memory=False):
        super().__init__()
        self.llm = llm
        prompt_template = PromptTemplate(
            system_template=""" 
            You are part of a database management team for SecureShield Insurance.
            Your task is to identify the type of claim-related query the user is asking and return the required data.
            For the following types of queries:
            - 'claim_status': Return the status of the claim by its ID.
            - 'claims_by_client': Return all claims associated with a particular client by client_id.
            - 'claims_by_policy': Return all claims associated with a specific policy by policy_id.
            - 'claim_details': Return full details of a claim by its claim_id.

            The system will look for the specific data and format in the user input.

            Here is the user input:
            {user_input}

            Chat History:
            {chat_history}

            {format_instructions}
            """, 
            human_template="user input: {user_input}",
        )

        self.prompt = generate_prompt_templates(prompt_template, memory=memory)
        self.output_parser = PydanticOutputParser(pydantic_object=ClaimQueryType)
        self.format_instructions = self.output_parser.get_format_instructions()

        self.chain = self.prompt | self.llm | self.output_parser

    def invoke(self, inputs):
        result = self.chain.invoke({
            "user_input": inputs["user_input"],
            "chat_history": inputs["chat_history"],
            "format_instructions": self.format_instructions,
        })
        return result
    
class GetClaimInfoOutput(BaseModel):
    output: str

class GetClaimInfoChain(Runnable):
    name: str = "GetClaimInfoChain"
    description: str = "Handles claim queries and responses related to the claims database."
    args_schema: Type[BaseModel] = ClaimQueryType
    return_direct: bool = True

    def __init__(self, memory=True):
        # Initialize LLM and extract claim query information
        self.llm = ChatOpenAI(model="gpt-4", temperature=0)
        self.extract_chain = ExtractClaimQuery(self.llm)

        prompt_bot_return = PromptTemplate(
            system_template="""
            You are part of the database manager team for SecureShield Insurance. 
            The user wants information about claims. You need to query the database for claim-related information based on the query type.
            
            There are possible queries:
            - For claim status: 'claim_status'
            - For claims by a client: 'claims_by_client'
            - For claims by a policy: 'claims_by_policy'
            - For claim details by claim_id: 'claim_details'

            Based on the results from the query, return a friendly response with the information.
            Do not greet the user at the beginning of the message, as this is in the middle of the conversation.

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
        self.output_parser = PydanticOutputParser(pydantic_object=GetClaimInfoOutput)
        self.format_instructions = self.output_parser.get_format_instructions()

        self.chain = self.prompt | self.llm | self.output_parser

    def invoke(self, user_input, config):
        # Connect to the claims database
        con = sqlite3.connect("SecureShield/secure_shield.db")
        cursor = con.cursor()

        try:
            query_info = self.extract_chain.invoke(user_input)
            num_results = query_info.num_results
            query_type = query_info.query_type
            value = query_info.value

            if query_type == 'claim_status':
                # Get claim status by claim_id
                cursor.execute("SELECT status FROM Claims WHERE claim_id = ?", (value,))
                result = cursor.fetchone()
                if result:
                    self.status = f"The status of claim {value} is: {result[0]}"
                else:
                    self.status = f"Claim {value} not found in the database."

            elif query_type == 'claims_by_client':
                # Get claims for a client (either by name or client_id)
                cursor.execute("SELECT claim_id, claim_type, status FROM Claims WHERE user_id = (SELECT client_id FROM Clients WHERE name = ? OR client_id = ?)", (value, value))
                results = cursor.fetchall()
                if results:
                    self.status = f"Claims for client '{value}': {results}"
                else:
                    self.status = f"No claims found for client '{value}'."

            elif query_type == 'claims_by_policy':
                # Get claims for a policy (by policy_id)
                cursor.execute("SELECT claim_id, claim_type, status FROM Claims WHERE policy_id = ?", (value,))
                results = cursor.fetchall()
                if results:
                    self.status = f"Claims for policy {value}: {results}"
                else:
                    self.status = f"No claims found for policy {value}."

            elif query_type == 'claim_details':
                # Get full details of a specific claim
                cursor.execute("SELECT * FROM Claims WHERE claim_id = ?", (value,))
                result = cursor.fetchone()
                if result:
                    self.status = f"Claim details for claim_id {value}: {result}"
                else:
                    self.status = f"No details found for claim {value}."

            else:
                self.status = "Invalid query type."

        except Exception as e:
            self.status = f"Error: {e}"

        # Generate the final response
        response = self.chain.invoke({
            "user_input": user_input['user_input'],
            'chat_history': user_input['chat_history'],
            "status": self.status,
            "format_instructions": self.format_instructions
        })

        return response.output

#config = {"configurable": {
                #"conversation_id": 67,
                #"user_id": 3468}}
#search_input = GetClaimInfoChain()
#user_input = {
 #   'user_input': "What is the status of claim 5?",
  #  'chat_history': []
#}

#response = search_input.invoke(user_input=user_input, config=config)
#print(response)  # Will return the claim status or related information

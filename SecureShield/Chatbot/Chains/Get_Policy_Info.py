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

class PolicyQueryType(BaseModel):
    query_type: str
    value: str
    num_results: int = 5  # Default to 5 results if not specified

class ExtractPolicyQuery(Runnable):
    def __init__(self, llm, memory=False):
        super().__init__()
        self.llm = llm
        prompt_template = PromptTemplate(
            system_template=""" 
            You are part of the database management team for a insurance company platform called SecureShield Insurance.
            Your task is to identify the type of policy-related query the user is asking and return the required data.
            For the following types of queries:
            - 'policy_details': Return full details of a policy by its policy_id.
            - 'policies_by_client': Return all policies associated with a particular client by client_id.
            - 'policies_by_type': Return all policies associated with a specific policy type (House, Health or Car).

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
        self.output_parser = PydanticOutputParser(pydantic_object=PolicyQueryType)
        self.format_instructions = self.output_parser.get_format_instructions()

        self.chain = self.prompt | self.llm | self.output_parser

    def invoke(self, inputs):
        result = self.chain.invoke({
            "user_input": inputs["user_input"],
            "chat_history": inputs["chat_history"],
            "format_instructions": self.format_instructions,
        })
        return result
    
class GetPolicyInfoOutput(BaseModel):
    output: str

class GetPolicyInfoChain(Runnable):
    name: str = "GetPolicyInfoChain"
    description: str = "Handles policy queries and responses related to the policies database."
    args_schema: Type[BaseModel] = PolicyQueryType
    return_direct: bool = True

    def __init__(self, memory=True):
        # Initialize LLM and extract policy query information
        self.llm = ChatOpenAI(model="gpt-4", temperature=0)
        self.extract_chain = ExtractPolicyQuery(self.llm)

        prompt_bot_return = PromptTemplate(
            system_template="""
            You are part of the database management team for a insurance company platform called SecureShield Insurance.
            The user wants information about policies. You need to query the database for policy-related information based on the query type.
            
            There are possible queries:
            - For policy details: 'policy_details'
            - For policies by client: 'policies_by_client'
            - For policies by type: 'policies_by_type'

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
        self.output_parser = PydanticOutputParser(pydantic_object=GetPolicyInfoOutput)
        self.format_instructions = self.output_parser.get_format_instructions()

        self.chain = self.prompt | self.llm | self.output_parser

    def invoke(self, user_input, config):
        # Connect to the policies database
        con = sqlite3.connect("SecureShield/secure_shield.db")
        cursor = con.cursor()

        try:
            query_info = self.extract_chain.invoke(user_input)
            num_results = query_info.num_results
            query_type = query_info.query_type
            value = query_info.value

            if query_type == 'policy_details':
                # Get full details of a specific policy
                cursor.execute("SELECT * FROM Policies WHERE policy_id = ?", (value,))
                result = cursor.fetchone()
                if result:
                    self.status = f"Policy details for policy_id {value}: {result}"
                else:
                    self.status = f"No details found for policy {value}."

            elif query_type == 'policies_by_client':
                # Get policies for a client (either by name or client_id)
                cursor.execute("SELECT policy_id, policy_type, policy_level FROM Policies WHERE user_id = (SELECT client_id FROM Clients WHERE name = ? OR client_id = ?)", (value, value))
                results = cursor.fetchall()
                if results:
                    self.status = f"Policies for client '{value}': {results}"
                else:
                    self.status = f"No policies found for client '{value}'."

            elif query_type == 'policies_by_type':
                # Get policies by type (e.g., Health, Car)
                cursor.execute("SELECT policy_id, user_id, policy_level FROM Policies WHERE policy_type = ?", (value,))
                results = cursor.fetchall()
                if results:
                    self.status = f"Policies of type '{value}': {results}"
                else:
                    self.status = f"No policies found for type '{value}'."

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
 #               "conversation_id": 67,
  #              "user_id": 3468}}

#policy_input = GetPolicyInfoChain()
#user_input = {
 #   'user_input': "Who are the clients that have car policies?",
  #  'chat_history': []
#}

#response = policy_input.invoke(user_input=user_input, config=config)
#print(response)  # Will return the policy status or related information


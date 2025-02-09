# Standard Library Imports
import os
from typing import List

# Third-Party Libraries
from pinecone import Index, Pinecone

# LangChain Libraries
from langchain_openai import OpenAIEmbeddings
from langchain_community.chat_models import ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from Chains.Base import PromptTemplate, generate_prompt_templates
import sqlite3

class RagChain:

    def __init__(self, username):
        
        def format_docs(documents):
            return "\n\n".join(doc.page_content for doc in documents)
        
        pc = Pinecone()
        index: Index = pc.Index("documents")
        vector_store = PineconeVectorStore(index=index, embedding=OpenAIEmbeddings(model="text-embedding-ada-002"))
        retriever = vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 2, "score_threshold": 0.5})
        
        self.llm = ChatOpenAI(model='gpt-4o-mini', temperature=0.2)

        con = sqlite3.connect("secure_shield.db")
        cursor = con.cursor()
        
        self.prompt_template = PromptTemplate(
            system_template="""
            You are the SecureShield chatbot, a platform with the objective of interact 
            with the company's employees, provide access to claims and relevant details both 
            about the insurance policies and the claims to streamline decision-making processes.
            Your task is to answer questions about the insurance policies benefits and tiers 
            and provide claims details.  
            
            Use the following pieces of context to answer the question at the end.
            If you don't know the answer, just say that you don't know, don't try to make up an answer.
            Use three sentences maximum and keep the answer as concise as possible.
            You have acess to the previous conversation history to personalize the conversation.

            {context}

            Question: {employee_input}

            Helpful Answer:""",
            human_template="Employee Query: {employee_input}",)


        self.custom_rag_prompt = generate_prompt_templates(self.template, memory=False)

        self.rag_chain = (
            {"context": retriever | format_docs, 
            "employee_input": RunnablePassthrough()
            }
            | self.custom_rag_prompt
            | self.llm
            | StrOutputParser()
        )

    def run_chain(self, question) -> str:
        return self.rag_chain.invoke(question)

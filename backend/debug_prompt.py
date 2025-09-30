#!/usr/bin/env python3
"""
Debug the LLM prompt directly
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.schema import SystemMessage, HumanMessage

load_dotenv()

def test_prompt():
    """Test the prompt directly"""
    
    # Initialize LLM
    llm = ChatGroq(
        model="deepseek-r1-distill-llama-70b",
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0
    )
    
    # Simple, direct prompt
    prompt = """You are a data analyst. Answer this question with a SQL query and insights.

Question: What are our top selling products?

Respond with JSON:
{
    "intent": "query",
    "sql_query": "SELECT ProductName, SUM(Sales) as TotalSales FROM products GROUP BY ProductName ORDER BY TotalSales DESC LIMIT 5",
    "visualization": "text",
    "response_guidance": "Analysis of top selling products",
    "response_type": "text"
}"""
    
    print("Testing simple prompt...")
    print(f"Prompt: {prompt}")
    
    try:
        response = llm.invoke(prompt)
        print(f"\nResponse: {response.content}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_prompt()

#!/usr/bin/env python3
"""
Test the LLM with a very simple prompt
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

def test_simple():
    """Test with the simplest possible prompt"""
    
    # Initialize LLM
    llm = ChatGroq(
        model="deepseek-r1-distill-llama-70b",
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0
    )
    
    # Test 1: Very simple question
    print("=== TEST 1: Simple Question ===")
    simple_prompt = "What is 2+2?"
    print(f"Prompt: {simple_prompt}")
    
    try:
        response = llm.invoke(simple_prompt)
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Direct instruction
    print("=== TEST 2: Direct Instruction ===")
    direct_prompt = "Answer this question: What are our top selling products?"
    print(f"Prompt: {direct_prompt}")
    
    try:
        response = llm.invoke(direct_prompt)
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: JSON format request
    print("=== TEST 3: JSON Format Request ===")
    json_prompt = """Generate a JSON response for this question: "What are our top selling products?"

Format:
{
    "answer": "your answer here",
    "sql": "SELECT statement here"
}"""
    print(f"Prompt: {json_prompt}")
    
    try:
        response = llm.invoke(json_prompt)
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_simple()

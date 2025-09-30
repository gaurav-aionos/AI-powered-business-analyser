#!/usr/bin/env python3
"""
Test different Groq models to find one that works
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

def test_models():
    """Test different models"""
    
    # List of models to try
    models = [
        "llama3-70b-8192",
        "mixtral-8x7b-32768", 
        "gemma2-9b-it",
        "llama3-8b-8192",
        "deepseek-r1-distill-llama-70b"
    ]
    
    test_prompt = "What is 2+2? Answer with just the number."
    
    for model in models:
        print(f"\n{'='*60}")
        print(f"Testing model: {model}")
        print(f"{'='*60}")
        
        try:
            llm = ChatGroq(
                model=model,
                groq_api_key=os.getenv("GROQ_API_KEY"),
                temperature=0
            )
            
            response = llm.invoke(test_prompt)
            print(f"Prompt: {test_prompt}")
            print(f"Response: {response.content}")
            
            # Check if response makes sense
            if "4" in response.content or "four" in response.content.lower():
                print("✅ SUCCESS: Model understood the question!")
            else:
                print("❌ FAILED: Model didn't understand the question")
                
        except Exception as e:
            print(f"❌ ERROR with model {model}: {e}")
        
        print()

if __name__ == "__main__":
    test_models()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
import os
from dotenv import load_dotenv
import asyncio
import json

from database.northwind_db import NorthwindDB
from app.agents.sql_forecast_agent import SQLForecastAgent
from utils.forecasting import SalesForecaster
from utils.chart_generator import ChartGenerator

load_dotenv()

app = FastAPI(title="Northwind Chatbot API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
db = NorthwindDB("northwind.db")
schema_info = db.get_schema_info()
table_mappings = db.detect_table_mappings()

print("Detected table mappings:", table_mappings)  # Debug output

forecaster = SalesForecaster()
chart_gen = ChartGenerator()

# Initialize agent with all dependencies
agent = SQLForecastAgent(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    schema_info=schema_info,
    db_conn=db,
    forecaster=forecaster,
    chart_gen=chart_gen,
    table_mappings=table_mappings
)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    data: Dict[str, Any]
    visualization_type: str
    has_forecast: bool = False

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        print(f"Processing query: {request.message}")
        result = await agent.process_query(request.message)
        print(f"Result: {result}")
        
        # Determine if this is a text response
        is_text_response = result.get("visualization") == "text"
        
        return ChatResponse(
            response=result.get("text", "Response generated"),
            data=result,
            visualization_type=result.get("visualization", "text"),
            has_forecast="forecast" in result
        )
            
    except Exception as e:
        import traceback
        print(f"Error in chat endpoint: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected"}

@app.get("/tables")
async def get_tables():
    """Endpoint to see detected table mappings"""
    return {
        "table_names": db.get_table_names(),
        "mappings": db.detect_table_mappings(),
        "schema_info": schema_info
    }

@app.post("/test-intent")
async def test_intent_detection(request: ChatRequest):
    """Test endpoint to debug intent detection"""
    try:
        # Test the intent detection directly
        response = agent.llm.invoke(agent.master_prompt.format(question=request.message))
        
        # Try to parse the response
        try:
            intent_data = json.loads(response.content)
        except:
            intent_data = {"sql_query": "Could not parse", "visualization": "table", "response_guidance": "Error parsing response"}
        
        # Test visualization detection
        detected_visualization = agent.detect_visualization_type(request.message, intent_data.get("sql_query", ""))
        
        return {
            "user_query": request.message,
            "generated_sql": intent_data.get("sql_query", ""),
            "llm_visualization": intent_data.get("visualization", "table"),
            "detected_visualization": detected_visualization,
            "response_guidance": intent_data.get("response_guidance", ""),
            "raw_response": response.content
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
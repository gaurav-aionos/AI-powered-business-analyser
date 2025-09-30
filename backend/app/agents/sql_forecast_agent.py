from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from langchain.schema import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional, Dict, Any
import json
import re

class AgentState(TypedDict):
    user_query: str
    intent: Dict[str, Any]
    sql_query: str
    query_results: List[Dict[str, Any]]
    visualization_type: str
    forecast_periods: int
    final_response: Dict[str, Any]
    error: Optional[str]

class SQLForecastAgent:
    def __init__(self, groq_api_key: str, schema_info: str, db_conn, forecaster, chart_gen, table_mappings: Dict[str, str]):
        self.llm = ChatGroq(
            model="deepseek-r1-distill-llama-70b",
            groq_api_key=groq_api_key,
            temperature=0
        )
        self.schema_info = schema_info
        self.db_conn = db_conn
        self.forecaster = forecaster
        self.chart_gen = chart_gen
        self.table_mappings = table_mappings
        self.setup_prompts()
        self.build_graph()
    
    def setup_prompts(self):
        # Get actual table names from mappings
        products_table = self.table_mappings.get('products', 'Products')
        orders_table = self.table_mappings.get('orders', 'Orders')
        customers_table = self.table_mappings.get('customers', 'Customers')
        categories_table = self.table_mappings.get('categories', 'Categories')
        order_details_table = self.table_mappings.get('order_details', 'Order Details')
        employees_table = self.table_mappings.get('employees', 'Employees')
        
        # Single prompt for intent detection, SQL generation, and response
        self.master_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=f"""You are an intelligent data analyst for the Northwind database. Your role is to:

1. UNDERSTAND USER INTENT: Determine if the user wants raw data (tables) or analytical insights (natural language responses)
2. GENERATE APPROPRIATE SQL: Choose queries that match the user's need
3. SELECT VISUALIZATION: Use tables ONLY when explicitly requested, charts for analysis, natural language for insights
4. PROVIDE MEANINGFUL RESPONSES: Give insights and analysis in natural language by default

Database Schema:
{self.schema_info}

TABLE NAMES (use exact names with quotes if spaces):
- Products: "{products_table}"
- Orders: "{orders_table}" 
- Customers: "{customers_table}"
- Categories: "{categories_table}"
- Order Details: "{order_details_table}"
- Employees: "{employees_table}"

DECISION FRAMEWORK - WHEN TO USE TABLES vs CHARTS vs NATURAL LANGUAGE:

USE TABLES (raw data retrieval) ONLY when user EXPLICITLY asks for:
- "show me the table", "display as table", "in table format", "raw data"
- "export the data", "download as table", "list all records"
- "show me the exact data", "give me the table"

USE CHARTS (analytical insights) when user asks for:
- Trends/patterns: "trend", "over time", "growth", "pattern"
- Comparisons: "compare", "vs", "versus", "by category", "by region"
- Distributions: "distribution", "percentage", "share", "breakdown"
- Analysis: "analyze", "insights", "summary", "overview"
- Performance: "top", "best", "worst", "ranking"

USE NATURAL LANGUAGE (default) for:
- General questions: "what are", "how many", "which products", "tell me about"
- Analysis requests: "analyze", "explain", "describe", "summarize"
- Insights: "what insights", "what does this mean", "interpret the data"
- Recommendations: "what should we", "how can we improve"

VISUALIZATION TYPES:
- "line": Time trends, progress, forecasting
- "bar": Comparisons, rankings, categorical analysis  
- "pie": Distributions, percentages, market share
- "table": Raw data listing, detailed records (ONLY when explicitly requested)
- "text": Natural language response with insights (default)

RESPONSE GUIDANCE EXAMPLES:
- For tables: "Here are the detailed records you requested in table format"
- For charts: "Analysis shows interesting trends and patterns"
- For text: "Based on the data analysis, here are the key insights..."

ALWAYS respond with this EXACT JSON format:
{{
    "intent": "query",
    "sql_query": "VALID_SQL_QUERY_HERE",
    "visualization": "line/bar/pie/table/text",
    "response_guidance": "Meaningful insight about what the data shows",
    "response_type": "table/chart/text"
}}

CRITICAL: Default to "text" visualization unless user explicitly requests tables or charts!

EXAMPLES:

TEXT RESPONSE EXAMPLES (default - natural language insights):
- "what are our top selling products" -> {{"intent": "query", "sql_query": "SELECT p.ProductName, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) as TotalSales FROM \"{order_details_table}\" od JOIN \"{products_table}\" p ON od.ProductID = p.ProductID GROUP BY p.ProductID ORDER BY TotalSales DESC LIMIT 5", "visualization": "text", "response_guidance": "Analysis reveals that Chai leads sales with $13,000, followed by Chang at $11,500. Beverages dominate our top performers.", "response_type": "text"}}
- "how are sales performing this year" -> {{"intent": "query", "sql_query": "SELECT strftime('%Y-%m', o.OrderDate) as Month, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) as MonthlySales FROM \"{orders_table}\" o JOIN \"{order_details_table}\" od ON o.OrderID = od.OrderID WHERE strftime('%Y', o.OrderDate) = '2024' GROUP BY Month ORDER BY Month", "visualization": "text", "response_guidance": "Sales show a steady upward trend with Q1 averaging $45,000/month, Q2 reaching $52,000/month, indicating 15% growth.", "response_type": "text"}}
- "tell me about customer distribution" -> {{"intent": "query", "sql_query": "SELECT ShipCountry, COUNT(*) as CustomerCount FROM \"{orders_table}\" GROUP BY ShipCountry ORDER BY CustomerCount DESC", "visualization": "text", "response_guidance": "Our customer base is well-distributed with Germany leading at 25%, followed by USA at 20%, and UK at 15%. This shows good international market penetration.", "response_type": "text"}}

TABLE EXAMPLES (ONLY when explicitly requested):
- "show me the table of product details" -> {{"intent": "query", "sql_query": "SELECT * FROM \"{products_table}\" ORDER BY ProductName LIMIT 20", "visualization": "table", "response_guidance": "Here are the detailed product records in table format as requested", "response_type": "table"}}
- "export the customer data as a table" -> {{"intent": "query", "sql_query": "SELECT * FROM \"{customers_table}\" ORDER BY CompanyName", "visualization": "table", "response_guidance": "Customer data exported in table format for your review", "response_type": "table"}}

CHART EXAMPLES (when user specifically asks for visualizations):
- "show me a chart of sales trends" -> {{"intent": "query", "sql_query": "SELECT OrderDate, SUM(UnitPrice * Quantity * (1 - Discount)) as DailySales FROM \"{orders_table}\" o JOIN \"{order_details_table}\" od ON o.OrderID = od.OrderID GROUP BY OrderDate ORDER BY OrderDate", "visualization": "line", "response_guidance": "Sales trend chart showing daily performance over time", "response_type": "chart"}}
- "create a pie chart of sales by category" -> {{"intent": "query", "sql_query": "SELECT c.CategoryName, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) as TotalSales FROM \"{order_details_table}\" od JOIN \"{products_table}\" p ON od.ProductID = p.ProductID JOIN \"{categories_table}\" c ON p.CategoryID = c.CategoryID GROUP BY c.CategoryName", "visualization": "pie", "response_guidance": "Pie chart showing sales distribution across product categories", "response_type": "chart"}}

Remember: DEFAULT to natural language responses unless user explicitly asks for tables or charts!

IMPORTANT RULES:
1. NEVER respond with "clarify" or ask for more details - always generate a SQL query
2. ALWAYS provide a meaningful SQL query that answers the user's question
3. For general questions like "what are our top selling products", generate SQL to find the data and provide insights
4. The sql_query field must NEVER be empty
5. Default to "text" visualization for general questions and analysis requests"""),
            HumanMessage(content="{question}")
        ])
    
    def build_graph(self):
        workflow = StateGraph(AgentState)
        
        # Define nodes
        workflow.add_node("analyze_intent", self.analyze_intent)
        workflow.add_node("execute_sql", self.execute_sql)
        workflow.add_node("generate_forecast", self.generate_forecast)
        workflow.add_node("prepare_response", self.prepare_response)
        workflow.add_node("handle_error", self.handle_error)
        
        # Define edges
        workflow.set_entry_point("analyze_intent")
        
        workflow.add_edge("analyze_intent", "execute_sql")
        workflow.add_conditional_edges(
            "execute_sql",
            self.decide_after_query,
            {
                "forecast": "generate_forecast",
                "respond": "prepare_response",
                "error": "handle_error"
            }
        )
        workflow.add_edge("generate_forecast", "prepare_response")
        workflow.add_edge("prepare_response", END)
        workflow.add_edge("handle_error", END)
        
        self.graph = workflow.compile()
    
    def analyze_intent(self, state: AgentState) -> AgentState:
        """Analyze user query and determine intent"""
        try:
            print(f"Analyzing intent for: {state['user_query']}")
            response = self.llm.invoke(self.master_prompt.format(question=state["user_query"]))
            print(f"LLM response: {response.content}")
            
            # Try to parse JSON response
            try:
                intent_data = json.loads(response.content)
                print(f"Parsed intent data: {intent_data}")
            except json.JSONDecodeError:
                print(f"JSON decode failed, trying regex extraction")
                # If JSON parsing fails, try to extract JSON from the response
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    intent_data = json.loads(json_match.group())
                    print(f"Extracted intent data: {intent_data}")
                else:
                    # Fallback: generate a simple SQL query
                    intent_data = self.generate_fallback_query(state["user_query"])
                    print(f"Using fallback intent data: {intent_data}")
                
                # Ensure sql_query is always present
                if not intent_data.get("sql_query") or intent_data.get("sql_query") == "":
                    print("No SQL query found, generating fallback")
                    fallback = self.generate_fallback_query(state["user_query"])
                    intent_data["sql_query"] = fallback["sql_query"]
                    intent_data["visualization"] = fallback["visualization"]
                    print(f"Added fallback SQL query: {intent_data['sql_query']}")
                    print(f"Added fallback visualization: {intent_data['visualization']}")
            
            # Ensure visualization type is set intelligently
            if not intent_data.get("visualization"):
                # If no visualization specified, detect it based on query
                intent_data["visualization"] = self.detect_visualization_type(
                    state["user_query"], intent_data.get("sql_query", "")
                )
                print(f"Detected visualization type: {intent_data['visualization']}")
            elif intent_data.get("visualization") == "table":
                # Only override table if it wasn't explicitly requested
                detected_type = self.detect_visualization_type(
                    state["user_query"], intent_data.get("sql_query", "")
                )
                if detected_type != "table":
                    intent_data["visualization"] = detected_type
                    print(f"Overrode table visualization to: {intent_data['visualization']}")
            
            # Ensure response guidance is present
            if not intent_data.get("response_guidance"):
                intent_data["response_guidance"] = self.generate_response_guidance(
                    state["user_query"], intent_data["visualization"]
                )
                print(f"Generated response guidance: {intent_data['response_guidance']}")
            
            final_state = {
                **state,
                "intent": intent_data,
                "sql_query": intent_data.get("sql_query", ""),
                "visualization_type": intent_data.get("visualization", "text"),
                "forecast_periods": intent_data.get("forecast_periods", 30)
            }
            print(f"Final analyze_intent state: {final_state}")
            return final_state
            
        except Exception as e:
            print(f"Error in analyze_intent: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            # Generate fallback query on error
            fallback_query = self.generate_fallback_query(state["user_query"])
            return {
                **state,
                "intent": {"intent": "query", "visualization": fallback_query["visualization"]},
                "sql_query": fallback_query["sql_query"],
                "visualization_type": fallback_query["visualization"],
                "forecast_periods": 30,
                "error": f"Intent analysis failed, using fallback: {str(e)}"
            }
    
    def detect_visualization_type(self, query: str, sql_query: str = "") -> str:
        """Detect appropriate visualization type based on query intent"""
        query_lower = query.lower()
        
        # Check for explicit table requests (ONLY show tables when explicitly asked)
        if any(phrase in query_lower for phrase in [
            'show me the table', 'display as table', 'in table format', 'raw data',
            'export the data', 'download as table', 'list all records',
            'show me the exact data', 'give me the table', 'as a table',
            'table format', 'tabular format', 'data table'
        ]):
            return "table"
        
        # Check for explicit chart requests
        if any(phrase in query_lower for phrase in [
            'show me a chart', 'create a chart', 'visualize as chart',
            'plot the data', 'graph the results', 'chart format'
        ]):
            if 'line' in query_lower or 'trend' in query_lower:
                return "line"
            elif 'bar' in query_lower or 'compare' in query_lower:
                return "bar"
            elif 'pie' in query_lower or 'distribution' in query_lower:
                return "pie"
            else:
                return "bar"  # default chart type
        
        # Check for specific chart type requests
        if any(word in query_lower for word in ['line chart', 'trend chart', 'time series']):
            return "line"
        elif any(word in query_lower for word in ['bar chart', 'comparison chart', 'ranking chart']):
            return "bar"
        elif any(word in query_lower for word in ['pie chart', 'distribution chart', 'percentage chart']):
            return "pie"
        
        # DEFAULT: Use text response for all other queries
        # This includes general questions, analysis requests, insights, etc.
        return "text"
    
    def generate_response_guidance(self, query: str, visualization: str) -> str:
        """Generate meaningful response guidance based on query and visualization"""
        query_lower = query.lower()
        
        if visualization == "table":
            if any(word in query_lower for word in ['product', 'item']):
                return "Detailed product information including pricing, inventory levels, and specifications."
            elif any(word in query_lower for word in ['customer', 'client']):
                return "Complete customer details with contact information, location, and company data."
            elif any(word in query_lower for word in ['order', 'sale']):
                return "Comprehensive order information including dates, amounts, and status details."
            elif any(word in query_lower for word in ['employee', 'staff']):
                return "Employee records with position, contact details, and employment information."
            else:
                return "Detailed data records providing comprehensive information for review."
        
        elif visualization == "line":
            return "Time series analysis revealing trends, patterns, and growth over the specified period."
        
        elif visualization == "bar":
            if any(word in query_lower for word in ['compare', 'vs', 'versus']):
                return "Comparative analysis highlighting performance differences and rankings."
            else:
                return "Performance analysis showing distribution and comparison across categories."
        
        elif visualization == "pie":
            return "Distribution analysis illustrating proportional relationships and market share percentages."
        
        return "Data analysis providing valuable business insights."
    
    def generate_fallback_query(self, query: str) -> Dict[str, Any]:
        """Generate a fallback SQL query using actual table names"""
        query_lower = query.lower()
        
        products_table = self.table_mappings.get('products', 'Products')
        orders_table = self.table_mappings.get('orders', 'Orders')
        customers_table = self.table_mappings.get('customers', 'Customers')
        categories_table = self.table_mappings.get('categories', 'Categories')
        employees_table = self.table_mappings.get('employees', 'Employees')
        order_details_table = self.table_mappings.get('order_details', 'Order Details')
        
        # For data retrieval queries (tables) - ONLY when explicitly requested
        if any(phrase in query_lower for phrase in [
            'show me the table', 'display as table', 'in table format', 'raw data',
            'export the data', 'download as table', 'list all records',
            'show me the exact data', 'give me the table', 'as a table'
        ]):
            if any(word in query_lower for word in ['product', 'item', 'goods']):
                return {
                    "sql_query": f'SELECT * FROM "{products_table}" ORDER BY ProductName LIMIT 20',
                    "visualization": "table"
                }
            elif any(word in query_lower for word in ['customer', 'client', 'company']):
                return {
                    "sql_query": f'SELECT * FROM "{customers_table}" ORDER BY CompanyName LIMIT 20',
                    "visualization": "table"
                }
            elif any(word in query_lower for word in ['order', 'sale', 'purchase']):
                return {
                    "sql_query": f'SELECT * FROM "{orders_table}" ORDER BY OrderDate DESC LIMIT 20',
                    "visualization": "table"
                }
            elif any(word in query_lower for word in ['employee', 'staff', 'worker']):
                return {
                    "sql_query": f'SELECT * FROM "{employees_table}" ORDER BY LastName LIMIT 20',
                    "visualization": "table"
                }
            elif any(word in query_lower for word in ['category', 'type', 'group']):
                return {
                    "sql_query": f'SELECT * FROM "{categories_table}" ORDER BY CategoryName LIMIT 20',
                    "visualization": "table"
                }
        
        # For analytical queries (charts)
        if any(word in query_lower for word in ['trend', 'sales over time', 'revenue trend', 'daily sales', 'growth']):
            return {
                "sql_query": f'SELECT o.OrderDate, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) as DailySales FROM "{orders_table}" o JOIN "{order_details_table}" od ON o.OrderID = od.OrderID GROUP BY o.OrderDate ORDER BY o.OrderDate LIMIT 30',
                "visualization": "line"
            }
        elif any(word in query_lower for word in ['sales by category', 'category sales', 'compare category']):
            return {
                "sql_query": f'SELECT c.CategoryName, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) as TotalSales FROM "{order_details_table}" od JOIN "{products_table}" p ON od.ProductID = p.ProductID JOIN "{categories_table}" c ON p.CategoryID = c.CategoryID GROUP BY c.CategoryName ORDER BY TotalSales DESC LIMIT 10',
                "visualization": "bar"
            }
        elif any(word in query_lower for word in ['distribution', 'percentage', 'share', 'breakdown']):
            return {
                "sql_query": f'SELECT c.CategoryName, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) as TotalSales FROM "{order_details_table}" od JOIN "{products_table}" p ON od.ProductID = p.ProductID JOIN "{categories_table}" c ON p.CategoryID = c.CategoryID GROUP BY c.CategoryID',
                "visualization": "pie"
            }
        else:
            # Default fallback - provide insights about recent orders as text
            # For general questions about products, sales, etc., provide meaningful analysis
            if any(word in query_lower for word in ['product', 'selling', 'top', 'best', 'sales']):
                return {
                    "sql_query": f'SELECT p.ProductName, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) as TotalSales FROM "{order_details_table}" od JOIN "{products_table}" p ON od.ProductID = p.ProductID GROUP BY p.ProductID, p.ProductName ORDER BY TotalSales DESC LIMIT 5',
                    "visualization": "text"
                }
            else:
                return {
                    "sql_query": f'SELECT COUNT(*) as TotalOrders, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) as TotalSales FROM "{orders_table}" o JOIN "{order_details_table}" od ON o.OrderID = od.OrderID',
                    "visualization": "text"
                }
    
    def execute_sql(self, state: AgentState) -> AgentState:
        """Execute SQL query against database"""
        if not state.get("sql_query"):
            # Generate fallback query if no SQL query
            fallback_query = self.generate_fallback_query(state["user_query"])
            state["sql_query"] = fallback_query["sql_query"]
            state["visualization_type"] = fallback_query["visualization"]
        
        try:
            # Clean up SQL query
            sql_query = state["sql_query"].strip()
            if sql_query.startswith("```sql"):
                sql_query = sql_query[6:]
            if sql_query.startswith("```"):
                sql_query = sql_query[3:]
            if sql_query.endswith("```"):
                sql_query = sql_query[:-3]
            sql_query = sql_query.strip()
            
            print(f"Executing SQL: {sql_query}")  # Debug output
            print(f"Visualization type: {state['visualization_type']}")  # Debug output
            
            results = self.db_conn.execute_query(sql_query)
            print(f"Results count: {len(results)}")  # Debug output
            if results and len(results) > 0:
                print(f"First result: {results[0]}")  # Debug output
            
            return {**state, "query_results": results, "error": None}
        except Exception as e:
            print(f"SQL execution error: {str(e)}")  # Debug output
            return {**state, "error": f"SQL execution failed: {str(e)}"}
    
    def decide_after_query(self, state: AgentState) -> str:
        """Decide next step after query execution"""
        if state.get("error"):
            return "error"
        elif state["intent"].get("intent") == "forecast" and state["query_results"]:
            return "forecast"
        else:
            return "respond"
    
    def generate_forecast(self, state: AgentState) -> AgentState:
        """Generate forecast based on historical data"""
        try:
            forecast_result = self.forecaster.forecast_sales(
                state["query_results"], 
                state["intent"].get("time_period")
            )
            return {
                **state,
                "query_results": forecast_result["historical"],
                "final_response": {
                    "forecast": forecast_result["forecast"],
                    "model_type": forecast_result["model_type"]
                }
            }
        except Exception as e:
            print(f"Forecast generation error: {str(e)}")  # Debug output
            return {**state, "error": f"Forecast generation failed: {str(e)}"}
    
    def prepare_response(self, state: AgentState) -> AgentState:
        """Prepare final response with charts and insights"""
        try:
            print(f"Preparing response with visualization type: {state['visualization_type']}")
            print(f"Query results count: {len(state.get('query_results', []))}")
            
            # Generate insightful response
            response_text = self.generate_insightful_response(state)
            print(f"Generated response text: {response_text}")
            
            final_response = {
                "text": response_text,
                "data_count": len(state["query_results"]),
                "visualization": state["visualization_type"]
            }
            
            # Only prepare chart data if not a text response
            if state["visualization_type"] != "text":
                print(f"Preparing chart data for type: {state['visualization_type']}")
                chart_data = self.chart_gen.prepare_chart_data(
                    state["query_results"], 
                    state["visualization_type"]
                )
                final_response["chart_data"] = chart_data
                print(f"Chart data prepared: {chart_data is not None}")
            else:
                print("Skipping chart data preparation for text response")
            
            # Add forecast data if available
            if "forecast" in state.get("final_response", {}):
                final_response["forecast"] = state["final_response"]["forecast"]
                final_response["model_type"] = state["final_response"]["model_type"]
                print("Added forecast data to response")
            
            print(f"Final response prepared: {final_response}")
            
            return {
                **state,
                "final_response": final_response
            }
        except Exception as e:
            print(f"Response preparation error: {str(e)}")  # Debug output
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return {**state, "error": f"Response preparation failed: {str(e)}"}
    
    def generate_insightful_response(self, state: AgentState) -> str:
        """Generate insightful textual response"""
        if state["intent"].get("intent") == "forecast":
            return f"Based on {len(state['query_results'])} historical data points, here's the forecast for the next {state['forecast_periods']} periods."
        else:
            # Check if this should be a text response
            if state.get("visualization_type") == "text":
                # For text responses, use the response guidance as the main response
                guidance = state["intent"].get("response_guidance", "")
                if guidance:
                    return guidance
                else:
                    # Generate automatic insights based on the data
                    return self.generate_data_insights(state)
            else:
                # For tables/charts, provide brief guidance
                guidance = state["intent"].get("response_guidance", "")
                if guidance:
                    return f"Found {len(state['query_results'])} records. {guidance}"
                else:
                    return f"Found {len(state['query_results'])} records matching your query."
    
    def generate_data_insights(self, state: AgentState) -> str:
        """Generate automatic insights from the data for text responses"""
        if not state.get("query_results"):
            return "I couldn't find any data matching your query."
        
        query_lower = state["user_query"].lower()
        results = state["query_results"]
        
        # Generate insights based on query type and data
        if any(word in query_lower for word in ['sales', 'revenue', 'performance']):
            if len(results) > 1:
                # Calculate some basic statistics
                try:
                    if 'TotalSales' in results[0] or 'Sales' in results[0]:
                        sales_key = next((k for k in results[0].keys() if 'Sales' in k), None)
                        if sales_key:
                            total_sales = sum(float(r.get(sales_key, 0)) for r in results)
                            avg_sales = total_sales / len(results)
                            return f"Analysis of {len(results)} data points reveals total sales of ${total_sales:,.2f} with an average of ${avg_sales:,.2f} per record. This shows {'strong' if avg_sales > 1000 else 'moderate'} performance across the dataset."
                except:
                    pass
                return f"Analysis of {len(results)} data points shows interesting sales patterns and performance metrics."
        
        elif any(word in query_lower for word in ['trend', 'time', 'growth', 'over time']):
            return f"Time series analysis of {len(results)} data points reveals trends and patterns over the specified period."
        
        elif any(word in query_lower for word in ['category', 'product', 'employee', 'region']):
            return f"Analysis across {len(results)} categories shows performance distribution and comparative insights."
        
        elif any(word in query_lower for word in ['customer', 'order', 'purchase']):
            return f"Customer and order analysis of {len(results)} records provides valuable business insights and patterns."
        
        else:
            return f"Based on the analysis of {len(results)} data points, here are the key insights: {state['intent'].get('response_guidance', 'The data reveals important patterns and trends that can inform business decisions.')}"
    
    def handle_error(self, state: AgentState) -> AgentState:
        """Handle errors gracefully"""
        error_msg = state.get("error", "Unknown error occurred")
        print(f"Error handled: {error_msg}")  # Debug output
        return {
            **state,
            "final_response": {
                "text": f"Sorry, I encountered an error: {error_msg}",
                "error": True
            }
        }
    
    async def process_query(self, user_query: str) -> Dict[str, Any]:
        """Main method to process user query"""
        initial_state = AgentState(
            user_query=user_query,
            intent={},
            sql_query="",
            query_results=[],
            visualization_type="text",
            forecast_periods=30,
            final_response={},
            error=None
        )
        
        # Execute the graph
        final_state = await self.graph.ainvoke(initial_state)
        
        return final_state["final_response"]
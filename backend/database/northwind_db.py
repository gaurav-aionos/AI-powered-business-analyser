import sqlite3
import pandas as pd
from typing import List, Dict, Any
import json

class NorthwindDB:
    def __init__(self, db_path: str = "C:\\oFFICE\\Northwind_langgraph\\northwind.db"):
        self.db_path = db_path
        self.conn = None    
        self.table_names = []
        
    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        return self.conn
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        try:
            self.connect()
            df = pd.read_sql_query(query, self.conn)
            return df.to_dict('records')
        except Exception as e:
            raise Exception(f"Query execution failed: {str(e)}")
        finally:
            self.close()
    
    def get_table_names(self) -> List[str]:
        """Get all table names in the database"""
        if self.table_names:
            return self.table_names
            
        try:
            self.connect()
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            self.table_names = [table[0] for table in tables]
            return self.table_names
        except Exception as e:
            print(f"Error getting table names: {e}")
            return []
        finally:
            self.close()
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column information for a specific table"""
        try:
            self.connect()
            cursor = self.conn.cursor()
            # Properly quote table names that contain spaces
            if ' ' in table_name:
                cursor.execute(f'PRAGMA table_info("{table_name}")')
            else:
                cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            return [{"name": col[1], "type": col[2], "nullable": col[3]} for col in columns]
        except Exception as e:
            print(f"Error getting table info for {table_name}: {e}")
            return []
        finally:
            self.close()
    
    def get_schema_info(self) -> str:
        """Get complete database schema information"""
        schema_info = []
        table_names = self.get_table_names()
        
        for table_name in table_names:
            columns = self.get_table_info(table_name)
            column_info = [f"{col['name']} ({col['type']})" for col in columns]
            schema_info.append(f"Table: {table_name}\nColumns: {', '.join(column_info)}")
        
        return "\n\n".join(schema_info)
    
    def detect_table_mappings(self) -> Dict[str, str]:
        """Detect which tables correspond to common entities"""
        table_names = self.get_table_names()
        mappings = {}
        
        # Common table patterns
        patterns = {
            'products': ['product', 'item', 'goods'],
            'orders': ['order', 'sale', 'purchase'],
            'customers': ['customer', 'client', 'company'],
            'employees': ['employee', 'staff', 'worker'],
            'categories': ['category', 'type', 'group'],
            'order_details': ['detail', 'line', 'item'],
            'suppliers': ['supplier', 'vendor']
        }
        
        for table_name in table_names:
            table_lower = table_name.lower()
            for entity, keywords in patterns.items():
                if any(keyword in table_lower for keyword in keywords):
                    mappings[entity] = table_name
                    break
        
        return mappings
import pandas as pd
from typing import List, Dict, Any
import random

class ChartGenerator:
    def __init__(self):
        self.color_palette = [
            'rgba(255, 99, 132, 0.8)',    # pink
            'rgba(54, 162, 235, 0.8)',    # blue
            'rgba(255, 206, 86, 0.8)',    # yellow
            'rgba(75, 192, 192, 0.8)',    # teal
            'rgba(153, 102, 255, 0.8)',   # purple
            'rgba(255, 159, 64, 0.8)',    # orange
            'rgba(199, 199, 199, 0.8)',   # gray
            'rgba(83, 102, 255, 0.8)',    # indigo
            'rgba(40, 159, 64, 0.8)',     # green
            'rgba(210, 105, 30, 0.8)'     # chocolate
        ]
    
    def prepare_chart_data(self, data: List[Dict[str, Any]], chart_type: str) -> Dict[str, Any]:
        """Prepare data for different chart types in Chart.js format"""
        if not data:
            return self._prepare_table_data([])
        
        df = pd.DataFrame(data)
        
        if chart_type == "bar" and self._can_create_bar_chart(df):
            return self._prepare_bar_chart_data(df)
        elif chart_type == "line" and self._can_create_line_chart(df):
            return self._prepare_line_chart_data(df)
        elif chart_type == "pie" and self._can_create_pie_chart(df):
            return self._prepare_pie_chart_data(df)
        else:
            return self._prepare_table_data(df)
    
    def _can_create_bar_chart(self, df: pd.DataFrame) -> bool:
        """Check if we can create a bar chart from the data"""
        if len(df) < 2:
            return False
        numeric_cols = df.select_dtypes(include=['number']).columns
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        return len(numeric_cols) > 0 and len(categorical_cols) > 0
    
    def _can_create_line_chart(self, df: pd.DataFrame) -> bool:
        """Check if we can create a line chart from the data"""
        if len(df) < 3:
            return False
        date_cols = [col for col in df.columns if any(keyword in col.lower() for keyword in ['date', 'time'])]
        numeric_cols = df.select_dtypes(include=['number']).columns
        return len(date_cols) > 0 and len(numeric_cols) > 0
    
    def _can_create_pie_chart(self, df: pd.DataFrame) -> bool:
        """Check if we can create a pie chart from the data"""
        if len(df) < 2:
            return False
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        return len(categorical_cols) > 0 and len(numeric_cols) > 0
    
    def _prepare_bar_chart_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Prepare data for bar chart in Chart.js format"""
        numeric_cols = df.select_dtypes(include=['number']).columns
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        
        x_col = categorical_cols[0] if len(categorical_cols) > 0 else df.columns[0]
        y_col = numeric_cols[0] if len(numeric_cols) > 0 else df.columns[1]
        
        chart_data = {
            "type": "bar",
            "data": {
                "labels": df[x_col].astype(str).tolist(),
                "datasets": [{
                    "label": y_col,
                    "data": df[y_col].tolist(),
                    "backgroundColor": self.color_palette[:len(df)],
                    "borderColor": self.color_palette[:len(df)],
                    "borderWidth": 1
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"{y_col} by {x_col}"
                    }
                }
            }
        }
        
        return chart_data
    
    def _prepare_line_chart_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Prepare data for line chart in Chart.js format"""
        date_cols = [col for col in df.columns if any(keyword in col.lower() for keyword in ['date', 'time'])]
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        x_col = date_cols[0] if len(date_cols) > 0 else df.columns[0]
        y_col = numeric_cols[0] if len(numeric_cols) > 0 else df.columns[1]
        
        # Sort by x column if it's date or numeric
        try:
            if pd.api.types.is_datetime64_any_dtype(df[x_col]):
                df = df.sort_values(x_col)
                labels = df[x_col].dt.strftime('%Y-%m-%d').tolist()
            elif pd.api.types.is_numeric_dtype(df[x_col]):
                df = df.sort_values(x_col)
                labels = df[x_col].astype(str).tolist()
            else:
                # Try to convert to datetime
                df[x_col] = pd.to_datetime(df[x_col], errors='coerce')
                if not df[x_col].isna().all():
                    df = df.sort_values(x_col)
                    labels = df[x_col].dt.strftime('%Y-%m-%d').tolist()
                else:
                    labels = df[x_col].astype(str).tolist()
        except:
            labels = df[x_col].astype(str).tolist()
        
        chart_data = {
            "type": "line",
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": y_col,
                    "data": df[y_col].tolist(),
                    "borderColor": self.color_palette[0],
                    "backgroundColor": f"{self.color_palette[0]}20",
                    "fill": True,
                    "tension": 0.1
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"{y_col} Trend"
                    }
                },
                "scales": {
                    "x": {
                        "title": {
                            "display": True,
                            "text": x_col
                        }
                    },
                    "y": {
                        "title": {
                            "display": True,
                            "text": y_col
                        }
                    }
                }
            }
        }
        
        return chart_data
    
    def _prepare_pie_chart_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Prepare data for pie chart in Chart.js format"""
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        x_col = categorical_cols[0] if len(categorical_cols) > 0 else df.columns[0]
        y_col = numeric_cols[0] if len(numeric_cols) > 0 else df.columns[1]
        
        chart_data = {
            "type": "pie",
            "data": {
                "labels": df[x_col].astype(str).tolist(),
                "datasets": [{
                    "data": df[y_col].tolist(),
                    "backgroundColor": self.color_palette[:len(df)],
                    "borderColor": "#ffffff",
                    "borderWidth": 2
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"Distribution of {y_col} by {x_col}"
                    }
                }
            }
        }
        
        return chart_data
    
    def _prepare_table_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Prepare data for table display"""
        if isinstance(df, list):
            df = pd.DataFrame(df)
        
        return {
            "type": "table",
            "data": df.to_dict('records'),
            "columns": [{"field": col, "headerName": col} for col in df.columns]
        }
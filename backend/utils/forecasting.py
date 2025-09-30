import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import Pipeline

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SalesForecaster:
    def __init__(self):
        self.model = None
    
    def detect_date_column(self, df: pd.DataFrame) -> Optional[str]:
        """Automatically detect date columns in the dataframe"""
        date_columns = []
        for col in df.columns:
            col_lower = col.lower()
            # Check for common date column names
            if any(keyword in col_lower for keyword in ['date', 'time', 'day', 'month', 'year', 'period']):
                date_columns.append(col)
            # Check if column contains date-like values
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                date_columns.append(col)
        
        return date_columns[0] if date_columns else None
    
    def detect_value_column(self, df: pd.DataFrame) -> Optional[str]:
        """Automatically detect numeric value columns"""
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        # Prefer columns with common sales/value names
        value_keywords = ['sales', 'revenue', 'amount', 'total', 'price', 'quantity', 'value']
        for col in numeric_columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in value_keywords):
                return col
        
        return numeric_columns[0] if numeric_columns else None
    
    def prepare_forecasting_data(self, historical_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Prepare data for forecasting with automatic column detection"""
        if not historical_data:
            raise ValueError("No historical data provided for forecasting")
        
        df = pd.DataFrame(historical_data)
        
        # Auto-detect date and value columns
        date_col = self.detect_date_column(df)
        value_col = self.detect_value_column(df)
        
        if not date_col or not value_col:
            raise ValueError("Could not automatically detect date and value columns for forecasting")
        
        logger.info(f"Using date column: {date_col}, value column: {value_col}")
        
        # Prepare dataframe
        forecast_df = df[[date_col, value_col]].copy()
        forecast_df.columns = ['ds', 'y']
        
        # Convert to datetime and ensure numeric values
        forecast_df['ds'] = pd.to_datetime(forecast_df['ds'], errors='coerce')
        forecast_df['y'] = pd.to_numeric(forecast_df['y'], errors='coerce')
        
        # Drop rows with invalid data
        forecast_df = forecast_df.dropna()
        
        if len(forecast_df) < 3:
            raise ValueError("Insufficient data points for forecasting (minimum 3 required)")
        
        return forecast_df.sort_values('ds')
    
    def calculate_forecast_periods(self, time_period: Optional[str] = None) -> int:
        """Calculate appropriate number of periods based on time period string"""
        if not time_period:
            return 30  # Default: 30 days
        
        time_period = time_period.lower()
        
        if 'day' in time_period:
            return 30
        elif 'week' in time_period:
            return 4
        elif 'month' in time_period:
            return 3
        elif 'quarter' in time_period:
            return 2
        elif 'year' in time_period:
            return 1
        else:
            return 30  # Default
    
    def forecast_sales(self, historical_data: List[Dict[str, Any]], 
                      time_period: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate sales forecast using statistical methods
        
        Args:
            historical_data: List of dictionaries with historical data
            time_period: String describing the forecast period
            
        Returns:
            Dictionary with forecast results
        """
        try:
            # Prepare data
            df = self.prepare_forecasting_data(historical_data)
            periods = self.calculate_forecast_periods(time_period)
            
            return self._forecast_with_linear_regression(df, periods)
                
        except Exception as e:
            logger.error(f"Forecasting failed: {e}")
            # Return empty forecast with error information
            return {
                'historical': historical_data,
                'forecast': [],
                'model_type': 'error',
                'error_message': str(e),
                'periods': 0
            }
    
    def _forecast_with_linear_regression(self, df: pd.DataFrame, periods: int) -> Dict[str, Any]:
        """Generate forecast using linear regression"""
        if len(df) < 3:
            return {
                'historical': df.to_dict('records'),
                'forecast': [],
                'model_type': 'simple',
                'periods': 0,
                'warning': 'Insufficient data for forecasting'
            }
        
        # Convert dates to numeric values (days since first date)
        df = df.copy()
        df['days'] = (df['ds'] - df['ds'].min()).dt.days
        
        # Prepare data for regression
        X = df['days'].values.reshape(-1, 1)
        y = df['y'].values
        
        # Use polynomial regression for better curve fitting
        degree = 2 if len(df) > 5 else 1
        model = Pipeline([
            ('poly', PolynomialFeatures(degree=degree)),
            ('linear', LinearRegression())
        ])
        
        model.fit(X, y)
        
        # Generate forecast dates
        last_date = df['ds'].max()
        forecast_dates = [last_date + timedelta(days=i) for i in range(1, periods + 1)]
        forecast_days = [(date - df['ds'].min()).days for date in forecast_dates]
        
        # Predict future values
        X_future = np.array(forecast_days).reshape(-1, 1)
        y_pred = model.predict(X_future)
        
        # Calculate confidence intervals (simple approach)
        y_std = np.std(y) * 0.5  # 50% of standard deviation as confidence interval
        
        forecast_data = []
        for i, (date, pred_value) in enumerate(zip(forecast_dates, y_pred)):
            forecast_data.append({
                'ds': date.strftime('%Y-%m-%d'),
                'yhat': float(pred_value),
                'yhat_lower': float(max(0, pred_value - y_std)),
                'yhat_upper': float(pred_value + y_std)
            })
        
        return {
            'historical': df[['ds', 'y']].rename(columns={'y': 'actual'}).to_dict('records'),
            'forecast': forecast_data,
            'model_type': f'polynomial_degree_{degree}',
            'periods': periods,
            'confidence_intervals': True
        }
    
    def generate_forecast_insights(self, forecast_results: Dict[str, Any]) -> str:
        """Generate human-readable insights from forecast results"""
        if not forecast_results.get('forecast'):
            return "Insufficient data to generate a meaningful forecast."
        
        historical = forecast_results['historical']
        forecast = forecast_results['forecast']
        
        if not historical or not forecast:
            return "Could not generate forecast due to data limitations."
        
        # Calculate basic statistics
        last_actual = historical[-1]['actual'] if historical else 0
        first_forecast = forecast[0]['yhat'] if forecast else 0
        last_forecast = forecast[-1]['yhat'] if forecast else 0
        
        # Generate insights
        insights = []
        
        if last_actual > 0 and first_forecast > 0:
            immediate_change = ((first_forecast - last_actual) / last_actual) * 100
            trend = "increasing" if immediate_change > 0 else "decreasing"
            insights.append(f"Immediate {trend} trend: {abs(immediate_change):.1f}% change")
        
        if len(forecast) > 1:
            total_change = ((last_forecast - first_forecast) / first_forecast) * 100
            if abs(total_change) > 1:  # Only mention if significant
                long_term_trend = "growth" if total_change > 0 else "decline"
                insights.append(f"Projected {long_term_trend}: {abs(total_change):.1f}% over the forecast period")
        
        if insights:
            return "Forecast insights: " + "; ".join(insights) + "."
        else:
            return "Forecast generated successfully. Review the chart for detailed trends."
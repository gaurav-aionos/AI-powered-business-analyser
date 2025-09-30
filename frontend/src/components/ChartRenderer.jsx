import React from 'react';
import {
  Paper,
  Typography,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow
} from '@mui/material';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line, Bar, Pie } from 'react-chartjs-2';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const ChartRenderer = ({ data, visualizationType, hasForecast }) => {
  if (!data) return null;

  // Check if we have chart data in the expected format
  const hasChartData = data.chart_data && data.chart_data.data && 
                      data.chart_data.data.labels && 
                      data.chart_data.data.datasets;

  const renderChart = () => {
    // If no proper chart data, render table for table visualization, error for others
    if (!hasChartData) {
      if (visualizationType === 'table') {
        return renderTable();
      } else {
        return (
          <Typography variant="body2" color="textSecondary" sx={{ textAlign: 'center', mt: 4 }}>
            Unable to generate chart. Please try a different query or request the data in table format.
          </Typography>
        );
      }
    }

    switch (visualizationType) {
      case 'line':
        return renderLineChart();
      case 'bar':
        return renderBarChart();
      case 'pie':
        return renderPieChart();
      case 'table':
        return renderTable();
      default:
        return renderTable();
    }
  };

  const renderLineChart = () => {
    const chartData = {
      labels: data.chart_data.data.labels,
      datasets: data.chart_data.data.datasets
    };

    const options = {
      responsive: true,
      plugins: {
        legend: {
          position: 'top',
        },
        title: {
          display: true,
          text: data.chart_data.options?.plugins?.title?.text || 'Trend Analysis'
        },
      },
    };

    return <Line data={chartData} options={options} />;
  };

  const renderBarChart = () => {
    const chartData = {
      labels: data.chart_data.data.labels,
      datasets: data.chart_data.data.datasets
    };

    const options = {
      responsive: true,
      plugins: {
        legend: {
          position: 'top',
        },
        title: {
          display: true,
          text: data.chart_data.options?.plugins?.title?.text || 'Comparison'
        },
      },
    };

    return <Bar data={chartData} options={options} />;
  };

  const renderPieChart = () => {
    const chartData = {
      labels: data.chart_data.data.labels,
      datasets: data.chart_data.data.datasets
    };

    const options = {
      responsive: true,
      plugins: {
        legend: {
          position: 'top',
        },
        title: {
          display: true,
          text: data.chart_data.options?.plugins?.title?.text || 'Distribution'
        },
      },
    };

    return <Pie data={chartData} options={options} />;
  };

  const renderTable = () => {
    // Use the table data from chart_data if available, otherwise use the main data
    const tableData = data.chart_data?.data || data.data || [];
    
    if (!tableData || tableData.length === 0) {
      return (
        <Typography variant="body2" color="textSecondary">
          No data available for display
        </Typography>
      );
    }

    // Get columns from chart_data or infer from first data item
    const columns = data.chart_data?.columns || 
                   (tableData.length > 0 ? Object.keys(tableData[0]) : []);
    
    return (
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              {columns.map((column) => (
                <TableCell key={column.field || column} sx={{ fontWeight: 'bold' }}>
                  {column.headerName || column}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {tableData.slice(0, 10).map((row, index) => (
              <TableRow key={index}>
                {columns.map((column) => {
                  const columnKey = column.field || column;
                  const value = row[columnKey];
                  return (
                    <TableCell key={columnKey}>
                      {typeof value === 'object' && value !== null 
                        ? JSON.stringify(value) 
                        : value != null ? value.toString() : ''
                      }
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {tableData.length > 10 && (
          <Box sx={{ p: 1, textAlign: 'center' }}>
            <Typography variant="caption" color="textSecondary">
              Showing 10 of {tableData.length} records
            </Typography>
          </Box>
        )}
      </TableContainer>
    );
  };

  return (
    <Paper elevation={2} sx={{ p: 2, mt: 1 }}>
      <Typography variant="h6" gutterBottom>
        {hasForecast ? 'Forecast Results' : 'Data Visualization'}
      </Typography>
      <Box sx={{ height: 300 }}>
        {renderChart()}
      </Box>
      {hasForecast && data.forecast && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="body2" color="textSecondary">
            Forecast period: {data.periods || 30} days
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

export default ChartRenderer;
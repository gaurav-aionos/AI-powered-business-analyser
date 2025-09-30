import React, { useState } from 'react';
import { Container, Paper, Typography } from '@mui/material';
import ChatInterface from './components/ChatInterface';
import './App.css';

function App() {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Paper elevation={3} sx={{ p: 3 }}>
        <Typography variant="h3" component="h1" gutterBottom align="center">
          Northwind Sales Chatbot
        </Typography>
        <Typography variant="subtitle1" align="center" color="textSecondary" gutterBottom>
          Ask questions about sales data and get visual insights
        </Typography>
        
        <ChatInterface />
      </Paper>
    </Container>
  );
}

export default App;
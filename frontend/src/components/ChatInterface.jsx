import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  TextField,
  Button,
  Paper,
  Typography,
  CircularProgress,
  List,
  ListItem,
  Chip
} from '@mui/material';
import { Send as SendIcon } from '@mui/icons-material';
import axios from 'axios';
import ChartRenderer from './ChartRenderer';
import MessageBubble from './MessageBubble';

const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      type: 'user',
      content: inputMessage,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await axios.post('http://localhost:8000/chat', {
        message: inputMessage
      });
      console.log("response----->",response.data);

      const botMessage = {
        type: 'bot',
        content: response.data.response,
        data: response.data.data,
        visualization: response.data.visualization_type,
        hasForecast: response.data.has_forecast,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      const errorMessage = {
        type: 'bot',
        content: 'Sorry, I encountered an error processing your request.',
        isError: true,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const exampleQueries = [
    "What are our top selling products?",
    "How are sales performing this year?",
    "Tell me about customer distribution",
    "Show me a chart of sales trends",
    "Show me the table of product details"
  ];

  return (
    <Box sx={{ height: '70vh', display: 'flex', flexDirection: 'column' }}>
      {/* Messages Area */}
      <Paper 
        variant="outlined" 
        sx={{ 
          flex: 1, 
          p: 2, 
          mb: 2, 
          overflow: 'auto',
          backgroundColor: '#fafafa'
        }}
      >
        {messages.length === 0 ? (
          <Box sx={{ textAlign: 'center', mt: 4 }}>
            <Typography variant="h6" color="textSecondary" gutterBottom>
              Welcome to Northwind Sales Chatbot
            </Typography>
            <Typography variant="body2" color="textSecondary" gutterBottom>
              Ask me questions about sales data, trends, and forecasts. I'll provide insights in natural language by default, or show tables/charts when you specifically request them.
            </Typography>
            
            <Box sx={{ mt: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                Try asking:
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'center' }}>
                {exampleQueries.map((query, index) => (
                  <Chip
                    key={index}
                    label={query}
                    onClick={() => setInputMessage(query)}
                    variant="outlined"
                    sx={{ cursor: 'pointer' }}
                  />
                ))}
              </Box>
            </Box>
          </Box>
        ) : (
          <List>
            {messages.map((message, index) => (
              <ListItem key={index} sx={{ display: 'block', mb: 2 }}>
                <MessageBubble message={message} />
                {message.type === 'bot' && message.data && message.visualization !== 'text' && (
                  <Box sx={{ mt: 2, ml: 4 }}>
                    <ChartRenderer 
                      data={message.data} 
                      visualizationType={message.visualization}
                      hasForecast={message.hasForecast}
                    />
                  </Box>
                )}
              </ListItem>
            ))}
            {isLoading && (
              <ListItem sx={{ display: 'flex', justifyContent: 'center' }}>
                <CircularProgress size={24} />
              </ListItem>
            )}
          </List>
        )}
        <div ref={messagesEndRef} />
      </Paper>

      {/* Input Area */}
      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Ask about sales data..."
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={isLoading}
          multiline
          maxRows={3}
        />
        <Button
          variant="contained"
          onClick={handleSendMessage}
          disabled={isLoading || !inputMessage.trim()}
          sx={{ minWidth: 'auto' }}
        >
          <SendIcon />
        </Button>
      </Box>
    </Box>
  );
};

export default ChatInterface;
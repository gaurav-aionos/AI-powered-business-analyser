import React from 'react';
import { Paper, Typography, Box } from '@mui/material';
import { format } from 'date-fns';

const MessageBubble = ({ message }) => {
  const isUser = message.type === 'user';
  
  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        mb: 1
      }}
    >
      <Paper
        elevation={1}
        sx={{
          p: 2,
          maxWidth: '70%',
          backgroundColor: isUser ? '#1976d2' : '#f5f5f5',
          color: isUser ? 'white' : 'text.primary',
          borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px'
        }}
      >
        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
          {message.content}
        </Typography>
        <Typography
          variant="caption"
          sx={{
            display: 'block',
            mt: 1,
            opacity: 0.7,
            color: isUser ? 'rgba(255,255,255,0.7)' : 'text.secondary'
          }}
        >
          {format(new Date(message.timestamp), 'HH:mm')}
        </Typography>
      </Paper>
    </Box>
  );
};

export default MessageBubble;
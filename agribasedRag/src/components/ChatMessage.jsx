import React from 'react';

const ChatMessage = ({ message }) => {
  const { role, content } = message;
  const isAi = role === 'assistant';

  return (
    <div className={`message-row ${isAi ? 'ai' : 'user'}`}>
      <div className="message-content">
        <div className={`avatar ${isAi ? 'ai' : 'user'}`}>
          {isAi ? 'AI' : 'U'}
        </div>
        <div className="text-content">
          {content}
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;

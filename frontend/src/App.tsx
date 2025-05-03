import React from 'react';
import ChatInterface from './components/ChatInterface';
import './App.css';

const App: React.FC = () => {
  return (
    <div className="app">
      <header className="app-header">
        <h1>Kirk AI - Voice Assistant</h1>
      </header>
      <main className="app-main">
        <ChatInterface />
      </main>
    </div>
  );
};

export default App; 
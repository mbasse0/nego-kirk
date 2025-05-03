import React, { useState } from 'react';
import AudioRecorder from './AudioRecorder';
import './ChatInterface.css';

const BACKEND_URL = 'http://localhost:8000';

const ChatInterface: React.FC = () => {
  const [text, setText] = useState('');
  const [audioURL, setAudioURL] = useState<string | null>(null);
  const [kirkResponse, setKirkResponse] = useState<string | null>(null);

  const handleTranscription = (transcribedText: string) => {
    setText(transcribedText);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;

    try {
      const response = await fetch(`${BACKEND_URL}/generate-speech`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text }),
      });

      if (response.ok) {
        const data = await response.json();
        setAudioURL(`${BACKEND_URL}${data.audio_url}`);
        setKirkResponse(data.text);
      }
    } catch (error) {
      console.error('Error generating speech:', error);
    }
  };

  return (
    <div className="chat-interface">
      <form onSubmit={handleSubmit} className="chat-form">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Type your message or use voice input..."
          className="chat-input"
        />
        <div className="chat-controls">
          <AudioRecorder onTranscription={handleTranscription} />
          <button type="submit" className="submit-button">
            Send
          </button>
        </div>
      </form>
      {kirkResponse && (
        <div className="kirk-response">
          <p>{kirkResponse}</p>
        </div>
      )}
      {audioURL && (
        <div className="audio-player-container">
          <audio src={audioURL} controls className="audio-player" />
        </div>
      )}
    </div>
  );
};

export default ChatInterface; 
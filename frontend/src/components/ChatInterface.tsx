import React, { useState } from 'react';
import AudioRecorder from './AudioRecorder';
import './ChatInterface.css';

const BACKEND_URL = 'http://localhost:8000';

const ChatInterface: React.FC = () => {
  const [text, setText] = useState('');
  const [audioURL, setAudioURL] = useState<string | null>(null);
  const [videoURL, setVideoURL] = useState<string | null>(null);
  const [kirkResponse, setKirkResponse] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [useVideo, setUseVideo] = useState(true);

  const handleTranscription = (transcribedText: string) => {
    setText(transcribedText);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    
    setIsLoading(true);
    setAudioURL(null);
    setVideoURL(null);

    try {
      // Choose endpoint based on video toggle
      const endpoint = useVideo ? '/generate-video' : '/generate-speech';
      
      console.log(`Sending request to ${endpoint}`);
      const response = await fetch(`${BACKEND_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text }),
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Response data:', data);
        
        setKirkResponse(data.text);
        
        if (data.audio_url) {
          setAudioURL(`${BACKEND_URL}${data.audio_url}`);
        }
        
        if (data.video_url) {
          setVideoURL(`${BACKEND_URL}${data.video_url}`);
        }
      }
    } catch (error) {
      console.error('Error generating response:', error);
    } finally {
      setIsLoading(false);
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
          disabled={isLoading}
        />
        <div className="chat-controls">
          <AudioRecorder onTranscription={handleTranscription} />
          <button type="submit" className="submit-button" disabled={isLoading || !text.trim()}>
            {isLoading ? 'Processing...' : 'Send'}
          </button>
        </div>
        <div className="toggle-container">
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={useVideo}
              onChange={() => setUseVideo(!useVideo)}
              className="toggle-input"
            />
            <span className="toggle-text">Use Video Response</span>
          </label>
        </div>
      </form>
      
      {kirkResponse && (
        <div className="kirk-response">
          <p>{kirkResponse}</p>
        </div>
      )}
      
      {videoURL && (
        <div className="video-player-container">
          <video src={videoURL} controls autoPlay className="video-player" />
        </div>
      )}
      
      {!videoURL && audioURL && (
        <div className="audio-player-container">
          <audio src={audioURL} controls autoPlay className="audio-player" />
        </div>
      )}
    </div>
  );
};

export default ChatInterface; 
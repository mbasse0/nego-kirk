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
  const [error, setError] = useState<string | null>(null);
  const [useVideo, setUseVideo] = useState(true);

  const handleTranscription = (transcribedText: string) => {
    setText(transcribedText);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;

    setIsLoading(true);
    setError(null);
    
    try {
      const endpoint = useVideo ? '/generate-video' : '/generate-speech';
      const response = await fetch(`${BACKEND_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text }),
      });

      if (response.ok) {
        const data = await response.json();
        setKirkResponse(data.text);
        setAudioURL(data.audio_url ? `${BACKEND_URL}${data.audio_url}` : null);
        setVideoURL(data.video_url ? `${BACKEND_URL}${data.video_url}` : null);
        
        if (data.error) {
          setError(data.error);
          console.error('Video generation error:', data.error);
        }
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to generate response');
        console.error('Error:', errorData);
      }
    } catch (error) {
      console.error('Error generating response:', error);
      setError('Failed to connect to the server');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAvatarUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${BACKEND_URL}/upload-avatar`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        alert('Avatar uploaded successfully!');
      } else {
        const errorData = await response.json();
        alert(`Error uploading avatar: ${errorData.detail}`);
      }
    } catch (error) {
      console.error('Error uploading avatar:', error);
      alert('Failed to upload avatar');
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
        <div className="option-controls">
          <label className="video-toggle">
            <input
              type="checkbox"
              checked={useVideo}
              onChange={() => setUseVideo(!useVideo)}
            />
            Use Video Response
          </label>
          <div className="avatar-upload">
            <label htmlFor="avatar-file" className="avatar-upload-label">
              Upload Avatar Image
            </label>
            <input
              type="file"
              id="avatar-file"
              accept="image/*"
              onChange={handleAvatarUpload}
              className="avatar-upload-input"
            />
          </div>
        </div>
      </form>
      
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}
      
      {kirkResponse && (
        <div className="kirk-response">
          <p>{kirkResponse}</p>
        </div>
      )}
      
      {videoURL && (
        <div className="video-player-container">
          <video src={videoURL} controls className="video-player" autoPlay />
        </div>
      )}
      
      {!videoURL && audioURL && (
        <div className="audio-player-container">
          <audio src={audioURL} controls className="audio-player" autoPlay />
        </div>
      )}
    </div>
  );
};

export default ChatInterface; 
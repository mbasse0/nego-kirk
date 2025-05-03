import React, { useState, useRef, useEffect } from 'react';
import AudioRecorder from './AudioRecorder';
import './ChatInterface.css';

const BACKEND_URL = 'http://localhost:8000';

const ChatInterface: React.FC = () => {
  const [text, setText] = useState('');
  const [audioURL, setAudioURL] = useState<string | null>(null);
  const [kirkResponse, setKirkResponse] = useState<string | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [bookInsight, setBookInsight] = useState<string | null>(null);
  const [videoURL] = useState<string | null>(`${BACKEND_URL}/video/output.mp4`);

  const audioRef = useRef<HTMLAudioElement | null>(null);

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
        setSummary(data.summary);
        setBookInsight(data.book_insight);
      }
    } catch (error) {
      console.error('Error generating speech:', error);
    }
  };

  useEffect(() => {
    if (audioURL && audioRef.current) {
      const tryPlay = async () => {
        try {
          await audioRef.current!.play();
        } catch (err) {
          console.warn('Autoplay failed:', err);
        }
      };
      tryPlay();
    }
  }, [audioURL]);

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

      <div className="chat-main">
        <div className="chat-left">
          {kirkResponse && (
            <div className="kirk-response">
              <p>{kirkResponse}</p>
            </div>
          )}
          {audioURL && (
            <div className="audio-player-container">
              <audio
                ref={audioRef}
                src={audioURL}
                controls
                className="audio-player"
              />
            </div>
          )}
          {videoURL && (
            <div className="video-player-container">
              <video
                src={videoURL}
                controls
                loop
                autoPlay
                muted
                className="video-player"
              />
            </div>
          )}
        </div>

        <div className="chat-right-panel">
          {summary && (
            <div className="summary-panel">
              <h4>🧭 Summary</h4>
              <p>{summary}</p>
            </div>
          )}
          {bookInsight && (
            <div className="book-panel">
              <h4>📘 Book Insight</h4>
              <p>{bookInsight}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;

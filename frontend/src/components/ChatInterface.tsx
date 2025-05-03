import React, { useState, useRef, useEffect } from 'react';
import AudioRecorder from './AudioRecorder';
import './ChatInterface.css';

const BACKEND_URL = 'http://localhost:8000';
const IDLE_VIDEO_URL = `${BACKEND_URL}/video/idle_video.mp4`; // Path to idle video

const ChatInterface: React.FC = () => {
  const [text, setText] = useState('');
  const [audioURL, setAudioURL] = useState<string | null>(null);
  const [videoURL, setVideoURL] = useState<string | null>(null);
  const [kirkResponse, setKirkResponse] = useState<string | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [bookInsight, setBookInsight] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isPlayingResponseVideo, setIsPlayingResponseVideo] = useState(false);
  const [isVideoLoaded, setIsVideoLoaded] = useState(false);
  const [isAudioOnly, setIsAudioOnly] = useState(false);
  
  // Always use video responses
  const useVideo = true;
  const autoSubmit = true;

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const idleVideoRef = useRef<HTMLVideoElement | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

  const handleTranscription = (transcribedText: string) => {
    setText(transcribedText);
  };

  // Function to trigger form submission programmatically
  const submitForm = () => {
    if (formRef.current && text.trim()) {
      formRef.current.dispatchEvent(
        new Event('submit', { cancelable: true, bubbles: true })
      );
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    
    setIsLoading(true);
    setAudioURL(null);
    setVideoURL(null);
    setKirkResponse(null);
    setSummary(null);
    setBookInsight(null);
    setIsVideoLoaded(false);
    setIsAudioOnly(false);

    try {
      // Always use generate-video endpoint
      const endpoint = '/generate-video';
      
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
        setSummary(data.summary);
        setBookInsight(data.book_insight);
        
        if (data.audio_url) {
          setAudioURL(`${BACKEND_URL}${data.audio_url}`);
        }
        
        if (data.video_url) {
          setVideoURL(`${BACKEND_URL}${data.video_url}`);
          setIsPlayingResponseVideo(true);
        } else if (data.audio_url) {
          // If we only have audio but no video
          setIsAudioOnly(true);
        }
      }
    } catch (error) {
      console.error('Error generating response:', error);
    } finally {
      setIsLoading(false);
      setText(''); // Clear input after sending
    }
  };

  // Handle video loaded event
  const handleVideoLoaded = () => {
    setIsVideoLoaded(true);
  };

  // Handle audio ending event
  const handleAudioEnded = () => {
    setIsAudioOnly(false);
    
    // Resume idle video
    if (idleVideoRef.current) {
      idleVideoRef.current.play().catch(e => console.warn('Could not play idle video:', e));
    }
  };

  // Handle auto-play of audio if no video is available
  useEffect(() => {
    if (audioURL && audioRef.current && !videoURL) {
      const tryPlay = async () => {
        try {
          await audioRef.current!.play();
        } catch (err) {
          console.warn('Autoplay failed:', err);
        }
      };
      tryPlay();
    }
  }, [audioURL, videoURL]);

  // Handle switching between idle and response videos
  useEffect(() => {
    // Function to handle when response video ends
    const handleVideoEnd = () => {
      console.log('Response video ended');
      setIsPlayingResponseVideo(false);
      setIsVideoLoaded(false);
      
      // Reset video URL after a delay to allow for transition
      setTimeout(() => {
        if (idleVideoRef.current) {
          idleVideoRef.current.play().catch(e => console.warn('Could not play idle video:', e));
        }
      }, 500); // Longer delay for smoother transition
    };

    // Set up and clean up event listeners
    if (videoRef.current) {
      if (isPlayingResponseVideo) {
        videoRef.current.addEventListener('ended', handleVideoEnd);
        videoRef.current.addEventListener('loadeddata', handleVideoLoaded);
      }
      
      return () => {
        if (videoRef.current) {
          videoRef.current.removeEventListener('ended', handleVideoEnd);
          videoRef.current.removeEventListener('loadeddata', handleVideoLoaded);
        }
      };
    }
  }, [isPlayingResponseVideo, videoRef]);

  // Handle audio player events
  useEffect(() => {
    if (audioRef.current && isAudioOnly) {
      audioRef.current.addEventListener('ended', handleAudioEnded);
      
      return () => {
        if (audioRef.current) {
          audioRef.current.removeEventListener('ended', handleAudioEnded);
        }
      };
    }
  }, [isAudioOnly, audioRef]);

  // Initial setup for idle video
  useEffect(() => {
    if (idleVideoRef.current) {
      // Make sure the video is ready to play
      const setupIdleVideo = () => {
        if (idleVideoRef.current) {
          idleVideoRef.current.play().catch(e => {
            console.warn('Could not play idle video:', e);
            // Try again after a short delay
            setTimeout(setupIdleVideo, 1000);
          });
          
          // Loop the idle video
          idleVideoRef.current.loop = true;
        }
      };
      
      setupIdleVideo();
    }
  }, []);

  return (
    <div className="chat-interface-minimal">
      <div className="avatar-container">
        {/* Idle video - always present but hidden when response video is playing */}
        <video 
          ref={idleVideoRef}
          src={IDLE_VIDEO_URL}
          className={`avatar-video idle-video ${(isPlayingResponseVideo || isAudioOnly) ? 'hidden' : 'visible'}`}
          muted
          playsInline
        />
        
        {/* Loading spinner - shown while video is loading */}
        {isPlayingResponseVideo && !isVideoLoaded && (
          <div className="loading-spinner"></div>
        )}
        
        {/* Response video - only visible when a response is playing */}
        {videoURL && (
          <video
            ref={videoRef}
            src={videoURL}
            className={`avatar-video response-video ${isPlayingResponseVideo && isVideoLoaded ? 'visible' : 'hidden'}`}
            autoPlay
            playsInline
          />
        )}
        
        {/* Audio player for fallback or audio-only responses */}
        {!videoURL && audioURL && (
          <audio
            ref={audioRef}
            src={audioURL}
            className="audio-hidden"
            controls={false}
            onEnded={handleAudioEnded}
          />
        )}
        
        {/* Audio-only indicator */}
        {isAudioOnly && (
          <div className="audio-only-indicator">
            <div className="audio-wave">
              <span></span>
              <span></span>
              <span></span>
              <span></span>
              <span></span>
            </div>
            <p>Audio response playing...</p>
          </div>
        )}
      </div>
      
      <div className="input-container">
        <form ref={formRef} onSubmit={handleSubmit} className="minimal-form">
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Ask Kirk a question..."
            className="minimal-input"
            disabled={isLoading}
          />
          <div className="minimal-controls">
            <AudioRecorder 
              onTranscription={handleTranscription} 
              onTranscriptionComplete={submitForm}
            />
            <button 
              type="submit" 
              className="minimal-button"
              disabled={isLoading || !text.trim()}
            >
              {isLoading ? '...' : 'Send'}
            </button>
          </div>
        </form>
      </div>
      
      <div className="info-panel">
        {(summary || bookInsight) && (
          <>
            {summary && (
              <div className="info-card">
                <h4>✧ Wisdom Summary ✧</h4>
                <p>{summary}</p>
              </div>
            )}
            {bookInsight && (
              <div className="info-card">
                <h4>✧ Tome of Knowledge ✧</h4>
                <p>{bookInsight}</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default ChatInterface;

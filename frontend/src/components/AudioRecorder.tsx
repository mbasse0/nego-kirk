import React, { useState, useRef } from 'react';
import './AudioRecorder.css';

interface AudioRecorderProps {
  onTranscription: (text: string) => void;
  onTranscriptionComplete?: () => void;
}

const AudioRecorder: React.FC<AudioRecorderProps> = ({ onTranscription, onTranscriptionComplete }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioURL, setAudioURL] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        setIsProcessing(true);
        try {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
          const audioUrl = URL.createObjectURL(audioBlob);
          setAudioURL(audioUrl);

          // Send audio to backend for transcription
          const formData = new FormData();
          formData.append('file', audioBlob, 'recording.wav');

          const response = await fetch('http://localhost:8000/transcribe', {
            method: 'POST',
            body: formData,
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Transcription failed');
          }

          const data = await response.json();
          onTranscription(data.text);
          
          // Automatically trigger form submission after transcription is complete
          if (onTranscriptionComplete && data.text.trim()) {
            // Add a small delay to ensure the text state is updated
            setTimeout(() => {
              onTranscriptionComplete();
            }, 300);
          }
        } catch (error) {
          console.error('Error during transcription:', error);
          setError(error instanceof Error ? error.message : 'Failed to transcribe audio');
        } finally {
          setIsProcessing(false);
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Error accessing microphone:', error);
      setError('Failed to access microphone. Please check your permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      setIsRecording(false);
    }
  };

  return (
    <div className="audio-recorder-minimal">
      <button
        className={`mic-button ${isRecording ? 'recording' : ''} ${isProcessing ? 'processing' : ''}`}
        onClick={isRecording ? stopRecording : startRecording}
        disabled={isProcessing}
        aria-label={isRecording ? 'Stop recording' : 'Start recording'}
        title={isRecording ? 'Stop recording' : 'Start recording'}
      >
        <span className="mic-icon">{isRecording ? '◼' : '🎤'}</span>
        {isProcessing && <span className="processing-indicator"></span>}
      </button>
      {error && <div className="recorder-error-tooltip">{error}</div>}
    </div>
  );
};

export default AudioRecorder; 
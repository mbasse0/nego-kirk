# Nego-Kirk: AI Negotiation Coach

Nego-Kirk is an AI-powered negotiation coach that provides real-time voice interaction and guidance. The application features a voice interface where users can speak to Kirk, an AI negotiation coach, and receive both text and voice responses.

## Features

- Real-time voice recording and transcription
- AI-powered negotiation coaching
- Voice response generation using ElevenLabs
- Interactive chat interface
- Modern, responsive UI

## Tech Stack

- Frontend: React, TypeScript, Webpack
- Backend: FastAPI, Python
- AI Services: OpenAI (Whisper, GPT), ElevenLabs

## Installation

### Prerequisites

- Node.js (v14 or higher)
- Python (v3.8 or higher)
- npm or yarn
- pip

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the backend directory with your API keys:
```env
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID=5ERbh3mpIEzi6sfFHo7H
```

5. Start the backend server:
```bash
uvicorn main:app --reload
```

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install Node.js dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

## Usage

1. Open your browser and navigate to `http://localhost:3000`
2. Click the "Start Recording" button to begin speaking
3. Click "Stop Recording" when finished
4. Kirk will process your message and respond with both text and voice

## Project Structure

```
nego-kirk/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AudioRecorder.tsx
│   │   │   ├── ChatInterface.tsx
│   │   │   └── App.tsx
│   │   ├── styles/
│   │   └── index.tsx
│   ├── package.json
│   └── webpack.config.js
└── README.md
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
# Simplified Kirk AI Backend

This is a simplified version of the Kirk AI backend that uses a more direct approach to generate lip-synced videos.

## Files

- `simplified_main.py` - Simplified FastAPI server with minimal code
- `super_simple_wav2lip.py` - Standalone script to test Wav2Lip without the server
- `run_simplified_server.sh` - Script to start the FastAPI server
- `run_super_simple.sh` - Script to test Wav2Lip on a test audio file

## How to Run

### Testing Wav2Lip Directly

To test if Wav2Lip works on your system:

```
./run_super_simple.sh
```

This will generate a lip-synced video in the `results` directory.

### Running the Web Server

To start the web server:

```
./run_simplified_server.sh
```

The server will start on http://localhost:8000 and can be accessed by the frontend.

### API Endpoints

- `/generate-speech` - Generate audio response only
- `/generate-video` - Generate lip-synced video response
- `/upload-avatar` - Upload a custom avatar image
- `/test-video` - Test endpoint to verify video generation
- `/audio/{filename}` - Serve audio files
- `/video/{filename}` - Serve video files

## Troubleshooting

If you encounter issues:

1. Check that the Wav2Lip directory exists and has the right case (wav2lip or Wav2Lip)
2. Ensure the avatar image exists in the library directory (as avatar.jpeg or avatar.png)
3. Make sure the conda environment is properly set up with required dependencies
4. Check that API keys for OpenAI and ElevenLabs are correctly set 
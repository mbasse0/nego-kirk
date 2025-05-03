import os
import subprocess
import sys
import cv2
import hashlib
from pathlib import Path
import logging
import shutil
import time
import numpy as np
import soundfile as sf
from pydub import AudioSegment

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("video_generator")

# Add Wav2Lip directory to path if it exists
wav2lip_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wav2lip')
if os.path.exists(wav2lip_dir):
    sys.path.append(wav2lip_dir)
    logger.debug(f"Added Wav2Lip directory to Python path: {wav2lip_dir}")
else:
    logger.warning(f"Wav2Lip directory not found at {wav2lip_dir}")

def ensure_directories():
    """Create necessary directories if they don't exist"""
    logger.debug("Creating directories...")
    dirs = ['temp', 'library', 'temp/cache', 'audio', 'output']
    for dir in dirs:
        if not os.path.exists(dir):
            os.makedirs(dir)
    logger.debug("Directories created")

def optimize_image_resolution(image_path, target_width=256):
    """Optimize image resolution for Wav2Lip processing"""
    logger.debug(f"Optimizing image: {image_path}")
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")
    
    # Calculate new dimensions while maintaining aspect ratio
    height, width = img.shape[:2]
    aspect_ratio = width / height
    new_height = int(target_width / aspect_ratio)
    
    # Resize image
    resized = cv2.resize(img, (target_width, new_height))
    
    # Save optimized image - Use JPEG extension to match combined_pipeline.py
    optimized_path = os.path.join('temp', 'optimized_avatar.jpeg')
    cv2.imwrite(optimized_path, resized)
    logger.debug(f"Optimized image saved to: {optimized_path}")
    return optimized_path

def get_cache_key(audio_path, image_path):
    """Generate a unique cache key based on input files"""
    # Get file modification times
    audio_mtime = os.path.getmtime(audio_path)
    image_mtime = os.path.getmtime(image_path) if os.path.exists(image_path) else 0
    
    # Create a unique key
    key = f"{audio_path}_{image_path}_{audio_mtime}_{image_mtime}"
    return hashlib.md5(key.encode()).hexdigest()

def check_cache(cache_key):
    """Check if we have a cached result"""
    cache_dir = Path('temp/cache')
    cache_dir.mkdir(exist_ok=True)
    
    cache_file = cache_dir / f"{cache_key}.mp4"
    if cache_file.exists():
        return str(cache_file)
    return None

def save_to_cache(cache_key, video_path):
    """Save the generated video to cache"""
    cache_dir = Path('temp/cache')
    cache_dir.mkdir(exist_ok=True)
    
    cache_file = cache_dir / f"{cache_key}.mp4"
    if os.path.exists(video_path):
        # Copy instead of rename to preserve original
        shutil.copy2(video_path, str(cache_file))
        return str(cache_file)
    return None

def run_wav2lip(image_path, audio_path, output_path):
    """Run the Wav2Lip model on the video and audio - DIRECTLY copying from combined_pipeline.py"""
    logger.debug(f"Starting Wav2Lip with image: {image_path}")
    
    # Check if image exists
    if not os.path.exists(image_path):
        logger.error(f"Input image file not found: {image_path}")
        raise FileNotFoundError(f"Input image file not found: {image_path}")
    
    # Check cache first
    cache_key = get_cache_key(audio_path, image_path)
    cached_video = check_cache(cache_key)
    if cached_video:
        logger.debug(f"Using cached video: {cached_video}")
        shutil.copy2(cached_video, output_path)
        return output_path
    
    # Optimize input image resolution
    optimized_image = optimize_image_resolution(image_path)
    
    # Find the correct wav2lip directory (case insensitive)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Fix: Try both lowercase and uppercase spellings
    if os.path.exists(os.path.join(script_dir, 'wav2lip')):
        wav2lip_dir = os.path.join(script_dir, 'wav2lip')
        logger.debug(f"Using lowercase wav2lip directory: {wav2lip_dir}")
    elif os.path.exists(os.path.join(script_dir, 'Wav2Lip')):
        wav2lip_dir = os.path.join(script_dir, 'Wav2Lip')
        logger.debug(f"Using uppercase Wav2Lip directory: {wav2lip_dir}")
    else:
        raise FileNotFoundError("Neither wav2lip nor Wav2Lip directory found")
    
    inference_path = os.path.join(wav2lip_dir, 'inference.py')
    checkpoint_path = os.path.join(wav2lip_dir, 'checkpoints', 'wav2lip_gan.pth')
    
    # Check if the Wav2Lip files exist
    if not os.path.exists(inference_path):
        logger.error(f"Wav2Lip inference.py not found at: {inference_path}")
        raise FileNotFoundError(f"Wav2Lip inference.py not found: {inference_path}")
    
    if not os.path.exists(checkpoint_path):
        logger.error(f"Wav2Lip checkpoint not found at: {checkpoint_path}")
        raise FileNotFoundError(f"Wav2Lip checkpoint not found: {checkpoint_path}")
    
    # Check if CUDA is available
    try:
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.debug(f"Using device: {device}")
    except ImportError:
        device = 'cpu'
        logger.debug("PyTorch not available, using CPU")
    
    # Optimize batch sizes based on device
    face_det_batch_size = 4 if device == 'cuda' else 1
    wav2lip_batch_size = 4 if device == 'cuda' else 1
    
    # Start with the simple command as used in combined_pipeline.py
    command = [
        'python', inference_path,
        '--checkpoint_path', checkpoint_path,
        '--face', optimized_image,
        '--audio', audio_path,
        '--outfile', output_path,
        '--pads', '0', '5', '0', '0',
        '--nosmooth',
        '--face_det_batch_size', str(face_det_batch_size),
        '--wav2lip_batch_size', str(wav2lip_batch_size)
    ]
    
    logger.debug(f"Running Wav2Lip command: {' '.join(command)}")
    
    try:
        # Run the command using subprocess with detailed logging
        logger.debug("Starting subprocess...")
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True,
            env=os.environ.copy(),  # Use current environment
            cwd=script_dir         # Run from script directory
        )
        
        # Full diagnostic output
        logger.debug(f"Command stdout: {result.stdout}")
        
        # Check if the command was successful
        if result.returncode != 0:
            logger.error(f"Error running Wav2Lip: {result.stderr}")
            logger.error(f"Return code: {result.returncode}")
            # Try with conda run as a fallback
            logger.debug("Trying with conda run...")
            conda_cmd = [
                'conda', 'run', '-n', 'kirk-ai',
                'python', inference_path,
                '--checkpoint_path', checkpoint_path,
                '--face', optimized_image,
                '--audio', audio_path,
                '--outfile', output_path,
                '--pads', '0', '5', '0', '0',
                '--nosmooth',
                '--face_det_batch_size', str(face_det_batch_size),
                '--wav2lip_batch_size', str(wav2lip_batch_size)
            ]
            
            result = subprocess.run(
                conda_cmd,
                capture_output=True,
                text=True,
                cwd=script_dir
            )
            
            if result.returncode != 0:
                logger.error(f"Conda run also failed: {result.stderr}")
                raise RuntimeError(f"Wav2Lip failed with error: {result.stderr}")
    except Exception as e:
        logger.error(f"Error during Wav2Lip execution: {str(e)}")
        raise
    
    # Check if the output file was created
    if not os.path.exists(output_path):
        logger.error(f"Wav2Lip failed to generate output video: {output_path}")
        raise FileNotFoundError(f"Wav2Lip failed to generate output video: {output_path}")
    
    # Save to cache
    cached_path = save_to_cache(cache_key, output_path)
    if cached_path:
        logger.debug(f"Video saved to cache: {cached_path}")
    
    logger.debug(f"Wav2Lip completed successfully: {output_path}")
    return output_path

def create_fallback_video(image_path, audio_path, output_path):
    """Create a simple video with the image and audio using ffmpeg as fallback"""
    try:
        logger.debug("Creating fallback video with ffmpeg")
        
        # Check if ffmpeg is available
        try:
            subprocess.run(
                ["ffmpeg", "-version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                check=True
            )
            logger.debug("FFmpeg is available")
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.error("ffmpeg is not installed or not available in PATH")
            # Just return the audio file if ffmpeg is not available
            return audio_path
        
        # Get audio duration
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        duration = float(result.stdout.strip())
        logger.debug(f"Audio duration: {duration} seconds")
        
        # Create video from image and audio
        command = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-i", audio_path,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-t", str(duration),
            output_path
        ]
        
        logger.debug(f"Running FFmpeg command: {' '.join(command)}")
        subprocess.run(command, check=True)
        
        # Verify the video was created
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Failed to generate output video: {output_path}")
            
        logger.debug(f"Fallback video created at {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error creating fallback video: {str(e)}")
        raise

def create_default_avatar():
    """Create a default avatar image"""
    try:
        # Create a simple placeholder image
        img = np.ones((300, 300, 3), dtype=np.uint8) * 255  # White background
        cv2.circle(img, (150, 150), 100, (200, 200, 200), -1)  # Gray circle for head
        cv2.circle(img, (120, 120), 15, (0, 0, 0), -1)  # Left eye
        cv2.circle(img, (180, 120), 15, (0, 0, 0), -1)  # Right eye
        cv2.ellipse(img, (150, 180), (50, 20), 0, 0, 180, (0, 0, 0), 2)  # Smile
        
        # Ensure directory exists
        os.makedirs("library", exist_ok=True)
        
        # Save image - using jpeg just like in combined_pipeline.py
        avatar_path = os.path.join("library", "avatar.jpeg")
        cv2.imwrite(avatar_path, img)
        logger.debug(f"Default avatar created at {avatar_path}")
        return avatar_path
    except Exception as e:
        logger.error(f"Error creating default avatar: {str(e)}")
        raise

def generate_video(audio_path, output_path, avatar_path=None):
    """Generate a video with lip-syncing from an audio file - FastAPI endpoint version"""
    ensure_directories()
    
    # Use the specified avatar or fallback to default
    if not avatar_path:
        avatar_path = os.path.join("library", "avatar.jpeg")
    
    if not os.path.exists(avatar_path):
        logger.warning(f"Avatar not found at {avatar_path}, using default or creating one")
        # Try both .jpeg and .png versions
        alt_path = os.path.join("library", "avatar.png")
        if os.path.exists(alt_path):
            avatar_path = alt_path
            logger.debug(f"Using alternative avatar at {alt_path}")
        else:
            avatar_path = create_default_avatar()
    
    # Try to use Wav2Lip for lip-synced video
    try:
        logger.debug("Starting Wav2Lip video generation")
        video_path = run_wav2lip(avatar_path, audio_path, output_path)
        
        # Verify the generation was successful
        if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
            logger.debug(f"Successfully generated video at {video_path}")
            return video_path
        else:
            logger.error(f"Generated video file not found or is empty: {video_path}")
            # Try fallback method
            return create_fallback_video(avatar_path, audio_path, output_path)
    
    except Exception as e:
        logger.error(f"Error during Wav2Lip video generation: {str(e)}")
        # If Wav2Lip fails, try the fallback method
        logger.debug("Attempting fallback video generation with FFmpeg")
        return create_fallback_video(avatar_path, audio_path, output_path)

def generate_video_from_audio(audio_file):
    """Generate a video with lip-syncing from an audio file - Legacy API for backward compatibility"""
    ensure_directories()
    
    # Generate a unique identifier for this response
    response_id = os.path.basename(audio_file).split('.')[0]
    
    # Define output paths with clear naming
    output_video = os.path.join("output", f"kirk_response_{response_id}.mp4")
    
    # Call the main generate_video function
    return generate_video(audio_file, output_video) 
import os
import sys
import cv2
import subprocess
import time
import shutil

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Create necessary directories
os.makedirs(os.path.join(script_dir, 'results'), exist_ok=True)
os.makedirs(os.path.join(script_dir, 'temp'), exist_ok=True)

# Set paths
results_dir = os.path.join(script_dir, 'results')
temp_dir = os.path.join(script_dir, 'temp')

# Use existing audio file or specify one
audio_path = os.path.join(script_dir, 'reply.mp3')

# Set avatar path - change this to your avatar file
avatar_path = os.path.join(script_dir, 'library', 'avatar.jpeg')
if not os.path.exists(avatar_path):
    avatar_path = os.path.join(script_dir, 'library', 'avatar.png')

# Output path in results directory - avoid spaces in filename
output_path = os.path.join(results_dir, f"result_{time.strftime('%Y%m%d_%H%M%S')}.mp4")

# Optimize image resolution
img = cv2.imread(avatar_path)
height, width = img.shape[:2]
aspect_ratio = width / height
new_height = int(256 / aspect_ratio)
resized = cv2.resize(img, (256, new_height))
optimized_image = os.path.join(temp_dir, 'optimized_avatar.jpeg')
cv2.imwrite(optimized_image, resized)

# Find Wav2Lip directory (case insensitive)
if os.path.exists(os.path.join(script_dir, 'wav2lip')):
    wav2lip_dir = os.path.join(script_dir, 'wav2lip')
elif os.path.exists(os.path.join(script_dir, 'Wav2Lip')):
    wav2lip_dir = os.path.join(script_dir, 'Wav2Lip')
else:
    print("Wav2Lip directory not found!")
    sys.exit(1)

# Create temporary working directory with no spaces
temp_working_dir = "/tmp/wav2lip_temp"
os.makedirs(temp_working_dir, exist_ok=True)

# Copy files to the temporary directory
temp_audio = os.path.join(temp_working_dir, "input.mp3")
temp_image = os.path.join(temp_working_dir, "face.jpeg")
temp_output = os.path.join(temp_working_dir, "output.mp4")

shutil.copy2(audio_path, temp_audio)
shutil.copy2(optimized_image, temp_image)

# Set paths
inference_path = os.path.join(wav2lip_dir, 'inference.py')
checkpoint_path = os.path.join(wav2lip_dir, 'checkpoints', 'wav2lip_gan.pth')

# Basic command with paths that don't have spaces
command = [
    'python', inference_path,
    '--checkpoint_path', checkpoint_path,
    '--face', temp_image,
    '--audio', temp_audio,
    '--outfile', temp_output,
    '--pads', '0', '5', '0', '0',
    '--nosmooth'
]

# Run Wav2Lip
print("Running Wav2Lip...")
print(" ".join(command))
subprocess.run(command)

# Copy the result back if it exists
if os.path.exists(temp_output):
    shutil.copy2(temp_output, output_path)
    print(f"✅ Success! Output saved to: {output_path}")
else:
    print("❌ Failed to generate video.") 
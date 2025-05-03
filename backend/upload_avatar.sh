#!/bin/bash

# This script uploads a default avatar that matches the format expected by combined_pipeline.py
# It copies avatar.png to avatar.jpeg to ensure compatibility

# Go to the backend directory
cd "$(dirname "$0")"

# Check if we have an avatar.png
if [ -f "library/avatar.png" ]; then
    echo "Found avatar.png, creating avatar.jpeg version..."
    # Convert PNG to JPEG (or just copy if conversion isn't needed)
    cp "library/avatar.png" "library/avatar.jpeg"
    echo "✅ Created avatar.jpeg from avatar.png"
else
    echo "❌ No avatar.png found in library/ directory"
    
    # Create the library directory if it doesn't exist
    mkdir -p library
    
    # Create a simple avatar using Python script
    echo "Creating a default avatar..."
    cat > create_avatar.py << 'EOF'
import cv2
import numpy as np

# Create a simple placeholder image
img = np.ones((300, 300, 3), dtype=np.uint8) * 255  # White background
cv2.circle(img, (150, 150), 100, (200, 200, 200), -1)  # Gray circle for head
cv2.circle(img, (120, 120), 15, (0, 0, 0), -1)  # Left eye
cv2.circle(img, (180, 120), 15, (0, 0, 0), -1)  # Right eye
cv2.ellipse(img, (150, 180), (50, 20), 0, 0, 180, (0, 0, 0), 2)  # Smile

# Save as both formats
cv2.imwrite("library/avatar.png", img)
cv2.imwrite("library/avatar.jpeg", img)
print("Default avatar created at library/avatar.png and library/avatar.jpeg")
EOF
    
    # Run the Python script with conda
    conda run -n kirk-ai python create_avatar.py
    rm create_avatar.py
fi

echo "🎉 Avatar setup complete! You can now run the server or combined_pipeline.py." 
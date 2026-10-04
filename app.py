import os
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
import google.genai as genai
from google.genai import types
from google.auth import default
from google.auth.transport.requests import Request
from dotenv import load_dotenv
import requests
import json

load_dotenv()

# ============================================================
# CHANGE THESE SETTINGS TO MODIFY VIDEO GENERATION
# ============================================================

VIDEO_MODEL = "veo-3.1-fast-generate-preview"

# Allowed: 4, 6, 8
VIDEO_DURATION_SECONDS = 8

# Allowed: 720p, 1080p, 4k
VIDEO_RESOLUTION = "720p"

# Allowed: 16:9, 9:16
VIDEO_ASPECT_RATIO = "16:9"

# Keep at 1 for this application.
NUMBER_OF_VIDEOS = 1

# Browser polling interval.
STATUS_POLL_INTERVAL_SECONDS = 5

# Maximum user prompt length.
MAX_PROMPT_LENGTH = 4000

# Timeout for downloading a completed MP4.
VIDEO_DOWNLOAD_TIMEOUT_SECONDS = 60

APPLICATION_NAME = "AI Video Generator"

# ============================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY not found in environment variables")

# Initialize OAuth2 token for API calls
def get_auth_token():
    """Get OAuth2 access token from service account or default credentials."""
    try:
        if SERVICE_ACCOUNT_JSON:
            # Use service account JSON
            import json
            from google.oauth2 import service_account

            creds_dict = json.loads(SERVICE_ACCOUNT_JSON)
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            credentials.refresh(Request())
            return credentials.token
        else:
            # Fall back to default credentials
            credentials, _ = default()
            if credentials and hasattr(credentials, 'refresh'):
                credentials.refresh(Request())
                return credentials.token
            return None
    except Exception as e:
        logger.error(f"Failed to get auth token: {str(e)}")
        return None

app = FastAPI()


def validate_configuration() -> tuple[bool, Optional[str]]:
    """Validate video configuration combinations."""
    # 1080p and 4k require 8 seconds
    if VIDEO_RESOLUTION in ["1080p", "4k"]:
        if VIDEO_DURATION_SECONDS != 8:
            return False, f"{VIDEO_RESOLUTION} requires VIDEO_DURATION_SECONDS = 8"
    
    # Validate duration
    if VIDEO_DURATION_SECONDS not in [4, 6, 8]:
        return False, f"VIDEO_DURATION_SECONDS must be 4, 6, or 8, got {VIDEO_DURATION_SECONDS}"
    
    # Validate resolution
    if VIDEO_RESOLUTION not in ["720p", "1080p", "4k"]:
        return False, f"VIDEO_RESOLUTION must be 720p, 1080p, or 4k"
    
    # Validate aspect ratio
    if VIDEO_ASPECT_RATIO not in ["16:9", "9:16"]:
        return False, f"VIDEO_ASPECT_RATIO must be 16:9 or 9:16"
    
    # Validate number of videos
    if NUMBER_OF_VIDEOS != 1:
        return False, "NUMBER_OF_VIDEOS must be 1"
    
    return True, None


# Validate configuration on startup
is_valid, error_msg = validate_configuration()
if not is_valid:
    logger.error(f"Configuration error: {error_msg}")


class GenerateRequest(BaseModel):
    prompt: str


@app.get("/", response_class=HTMLResponse)
async def get_homepage():
    """Return the web application's HTML interface."""
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{APPLICATION_NAME}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }}
            
            .container {{
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                max-width: 800px;
                width: 100%;
                padding: 40px;
            }}
            
            h1 {{
                text-align: center;
                color: #333;
                margin-bottom: 30px;
                font-size: 28px;
            }}
            
            .form-group {{
                margin-bottom: 20px;
            }}
            
            label {{
                display: block;
                margin-bottom: 8px;
                color: #555;
                font-weight: 500;
            }}
            
            textarea {{
                width: 100%;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-family: inherit;
                font-size: 14px;
                resize: vertical;
                min-height: 120px;
                transition: border-color 0.3s;
            }}
            
            textarea:focus {{
                outline: none;
                border-color: #667eea;
            }}
            
            .button-group {{
                display: flex;
                gap: 10px;
                margin-top: 20px;
            }}
            
            button {{
                flex: 1;
                padding: 12px 24px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            
            button:hover:not(:disabled) {{
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
            }}
            
            button:disabled {{
                opacity: 0.6;
                cursor: not-allowed;
            }}
            
            .status-area {{
                margin-top: 30px;
                padding: 16px;
                background: #f5f5f5;
                border-radius: 8px;
                text-align: center;
                color: #666;
                font-size: 14px;
                min-height: 20px;
            }}
            
            .video-container {{
                margin-top: 30px;
                display: none;
            }}
            
            .video-container.visible {{
                display: block;
            }}
            
            video {{
                width: 100%;
                border-radius: 8px;
                background: #000;
                margin-bottom: 15px;
            }}
            
            .download-link {{
                display: inline-block;
                padding: 12px 24px;
                background: #4caf50;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
                transition: background 0.3s;
            }}
            
            .download-link:hover {{
                background: #45a049;
            }}
            
            .error {{
                color: #d32f2f;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{APPLICATION_NAME}</h1>
            
            <div class="form-group">
                <label for="prompt">Describe the video you want to generate...</label>
                <textarea id="prompt" placeholder="A cinematic drone shot over a mountain lake at sunrise..."></textarea>
            </div>
            
            <div class="button-group">
                <button id="generateBtn" onclick="generateVideo()">Generate Video</button>
            </div>
            
            <div class="status-area" id="status">Ready</div>
            
            <div class="video-container" id="videoContainer">
                <video id="videoPlayer" controls></video>
                <div style="text-align: center;">
                    <a id="downloadLink" class="download-link" download="generated-video.mp4">Download Video</a>
                </div>
            </div>
        </div>
        
        <script>
            const STATUS_POLL_INTERVAL = {STATUS_POLL_INTERVAL_SECONDS} * 1000;
            const MAX_PROMPT_LENGTH = {MAX_PROMPT_LENGTH};
            
            let currentOperationId = null;
            let isPolling = false;
            
            // Try to resume from localStorage on page load
            function resumeIfNeeded() {{
                const savedOperation = localStorage.getItem('currentOperation');
                if (savedOperation && !currentOperationId) {{
                    currentOperationId = savedOperation;
                    document.getElementById('generateBtn').disabled = true;
                    updateStatus('Resuming video generation...');
                    pollStatus();
                }}
            }}
            
            window.addEventListener('load', resumeIfNeeded);
            
            async function generateVideo() {{
                const prompt = document.getElementById('prompt').value.trim();
                
                if (!prompt) {{
                    updateStatus('Please enter a prompt.', 'error');
                    return;
                }}
                
                if (prompt.length > MAX_PROMPT_LENGTH) {{
                    updateStatus(`Prompt exceeds maximum allowed length ({{prompt.length}}/{MAX_PROMPT_LENGTH}).`, 'error');
                    return;
                }}
                
                const generateBtn = document.getElementById('generateBtn');
                generateBtn.disabled = true;
                updateStatus('Starting video generation...');
                
                try {{
                    const response = await fetch('/generate', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{prompt}})
                    }});
                    
                    if (!response.ok) {{
                        const error = await response.json();
                        updateStatus(`Error: {{error.detail || 'Generation failed'}}`, 'error');
                        generateBtn.disabled = false;
                        return;
                    }}
                    
                    const data = await response.json();
                    currentOperationId = data.operation;
                    localStorage.setItem('currentOperation', currentOperationId);
                    updateStatus('Generating video...');
                    pollStatus();
                }} catch (error) {{
                    updateStatus(`Error: {{error.message}}`, 'error');
                    generateBtn.disabled = false;
                }}
            }}
            
            async function pollStatus() {{
                if (isPolling || !currentOperationId) return;
                
                isPolling = true;
                
                try {{
                    const response = await fetch(`/status?operation=${{currentOperationId}}`);
                    
                    if (!response.ok) {{
                        updateStatus('Temporary status error. Retrying...', 'error');
                        isPolling = false;
                        setTimeout(pollStatus, STATUS_POLL_INTERVAL);
                        return;
                    }}
                    
                    const data = await response.json();
                    
                    if (data.status === 'processing') {{
                        updateStatus('Generating video...');
                        isPolling = false;
                        setTimeout(pollStatus, STATUS_POLL_INTERVAL);
                    }} else if (data.status === 'completed') {{
                        updateStatus('Video generated successfully.');
                        isPolling = false;
                        loadVideo();
                    }} else if (data.status === 'failed') {{
                        updateStatus(`Video generation failed: {{data.error || 'Unknown error'}}`, 'error');
                        isPolling = false;
                        document.getElementById('generateBtn').disabled = false;
                        localStorage.removeItem('currentOperation');
                        currentOperationId = null;
                    }}
                }} catch (error) {{
                    updateStatus('Temporary status error. Retrying...', 'error');
                    isPolling = false;
                    setTimeout(pollStatus, STATUS_POLL_INTERVAL);
                }}
            }}
            
            async function loadVideo() {{
                try {{
                    const videoUrl = `/video?operation=${{currentOperationId}}`;
                    const videoPlayer = document.getElementById('videoPlayer');
                    videoPlayer.src = videoUrl;
                    
                    const videoContainer = document.getElementById('videoContainer');
                    videoContainer.classList.add('visible');
                    
                    const downloadLink = document.getElementById('downloadLink');
                    downloadLink.href = videoUrl;
                    
                    localStorage.removeItem('currentOperation');
                    
                    // Allow new generation
                    document.getElementById('generateBtn').disabled = false;
                    currentOperationId = null;
                }} catch (error) {{
                    updateStatus(`Error loading video: {{error.message}}`, 'error');
                    document.getElementById('generateBtn').disabled = false;
                }}
            }}
            
            function updateStatus(message, type = 'info') {{
                const statusDiv = document.getElementById('status');
                statusDiv.textContent = message;
                statusDiv.className = 'status-area';
                if (type === 'error') {{
                    statusDiv.classList.add('error');
                }}
            }}
        </script>
    </body>
    </html>
    """
    return html


@app.post("/generate")
async def generate_video(request: GenerateRequest):
    """Start a new video generation."""
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not configured")
        raise HTTPException(status_code=500, detail="Server configuration error")
    
    prompt = request.prompt.strip()
    
    # Validate prompt
    if not prompt:
        raise HTTPException(status_code=400, detail="Please enter a prompt.")
    
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Prompt exceeds maximum allowed length ({len(prompt)}/{MAX_PROMPT_LENGTH})."
        )
    
    # Validate configuration
    is_valid, error_msg = validate_configuration()
    if not is_valid:
        logger.error(f"Configuration error: {error_msg}")
        raise HTTPException(status_code=500, detail="Server configuration error")
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        logger.info(f"Starting video generation with prompt: {prompt[:50]}...")
        
        operation = client.models.generate_videos(
            model=VIDEO_MODEL,
            prompt=prompt,
            config=types.GenerateVideosConfig(
                resolution=VIDEO_RESOLUTION,
                aspect_ratio=VIDEO_ASPECT_RATIO,
                duration_seconds=str(VIDEO_DURATION_SECONDS),
                number_of_videos=NUMBER_OF_VIDEOS,
            ),
        )
        
        operation_id = operation.name
        
        logger.info(f"Generation started: {operation_id}")
        
        return {
            "status": "processing",
            "operation": operation_id
        }
    
    except Exception as e:
        logger.error(f"Generation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start video generation"
        )


def get_operation_from_google(operation_name: str):
    """Get operation status from Google API using OAuth2."""
    try:
        # Get OAuth2 token
        token = get_auth_token()
        if not token:
            logger.error("Could not get OAuth2 token")
            return None

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Use Google's REST API to get operation status (without API key)
        url = f"https://generativelanguage.googleapis.com/v1beta/{operation_name}"

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Google API error: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.error(f"Failed to get operation from Google: {str(e)}")
        return None


@app.get("/status")
async def check_status(operation: str):
    """Check the status of a video generation operation."""
    if not operation:
        raise HTTPException(status_code=400, detail="Operation ID required")
    
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not configured")
        raise HTTPException(status_code=500, detail="Server configuration error")
    
    try:
        logger.info(f"Checking status for operation: {operation}")
        
        # Get operation status from Google API
        op_data = get_operation_from_google(operation)
        
        if not op_data:
            logger.warning(f"Could not retrieve operation: {operation}")
            return {"status": "processing"}
        
        # Check if operation is complete
        is_done = op_data.get("done", False)
        
        if is_done:
            # Check if there was an error
            if "error" in op_data:
                error_msg = op_data.get("error", {}).get("message", "Unknown error")
                logger.error(f"Operation failed: {error_msg}")
                return {
                    "status": "failed",
                    "error": error_msg
                }
            else:
                logger.info(f"Operation completed: {operation}")
                return {"status": "completed"}
        else:
            logger.info(f"Operation still processing: {operation}")
            return {"status": "processing"}
    
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return {"status": "processing"}


@app.get("/video")
async def get_video(operation: str):
    """Retrieve the generated video."""
    if not operation:
        raise HTTPException(status_code=400, detail="Operation ID required")
    
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not configured")
        raise HTTPException(status_code=500, detail="Server configuration error")
    
    try:
        logger.info(f"Retrieving video for operation: {operation}")
        
        # Get operation from Google API
        op_data = get_operation_from_google(operation)
        
        if not op_data or not op_data.get("done"):
            raise HTTPException(status_code=400, detail="Video generation not complete")
        
        if "error" in op_data:
            raise HTTPException(status_code=400, detail="Video generation failed")
        
        # Get the video URL from the response
        response_data = op_data.get("response", {})
        generated_videos = response_data.get("generatedVideos", [])
        
        if not generated_videos:
            raise HTTPException(status_code=500, detail="No video in response")
        
        video_uri = generated_videos[0].get("video", {}).get("uri")
        
        if not video_uri:
            raise HTTPException(status_code=500, detail="No video URI found")
        
        # Download the video from the provided URL
        logger.info(f"Downloading video from: {video_uri[:50]}...")
        
        video_response = requests.get(
            video_uri,
            timeout=VIDEO_DOWNLOAD_TIMEOUT_SECONDS,
            stream=True
        )
        
        if video_response.status_code != 200:
            logger.error(f"Failed to download video: {video_response.status_code}")
            raise HTTPException(status_code=500, detail="Failed to download video")
        
        logger.info(f"Video downloaded successfully: {operation}")
        
        return StreamingResponse(
            video_response.iter_content(chunk_size=8192),
            media_type="video/mp4",
            headers={"Content-Disposition": "inline; filename=video.mp4"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve video")

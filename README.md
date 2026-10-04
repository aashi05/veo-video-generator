# AI Video Generator

A minimal, production-ready web application that allows users to generate videos using Google Veo directly from the browser. Built with FastAPI and deployed to Vercel.

## Features

- **Text-to-Video Generation**: Enter a prompt and generate an 8-second video
- **Asynchronous Processing**: Non-blocking video generation with browser-side polling
- **Multiple Generations**: Generate multiple independent videos sequentially
- **Public Access**: No authentication required - instantly accessible to evaluators
- **Secure API Key Management**: Gemini API key stored server-side only
- **Vercel Deployment**: Directly deployable as a serverless application

## Technology Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Video Generation**: Google Gemini API (Veo 3.1 Fast)
- **Deployment**: Vercel (Python Functions)
- **Dependencies**: google-genai, python-dotenv, requests

## Local Development

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd veo-video-generator
```

### 2. Create a Python virtual environment

```bash
python3 -m venv .venv
```

### 3. Activate the virtual environment

**On Linux/macOS:**
```bash
source .venv/bin/activate
```

**On Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Create a `.env` file

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Then edit `.env` and add your Gemini API key:

```env
GEMINI_API_KEY=your_actual_gemini_api_key
```

### 6. Run the application

```bash
uvicorn app:app --reload
```

### 7. Open in browser

Navigate to:
```
http://localhost:8000
```

## Usage

1. **Enter a prompt** in the text area describing the video you want to generate
2. **Click "Generate Video"** to start the generation
3. **Wait for processing** - the status will update as the video is being generated
4. **Watch and download** - once complete, the video appears in the player below
5. **Generate another video** - you can immediately submit a new prompt

## Configuration

All important settings are in the configuration section at the top of `app.py`:

```python
# ============================================================
# CHANGE THESE SETTINGS TO MODIFY VIDEO GENERATION
# ============================================================

VIDEO_MODEL = "veo-3.1-fast-generate-preview"
VIDEO_DURATION_SECONDS = 8              # Allowed: 4, 6, 8
VIDEO_RESOLUTION = "720p"               # Allowed: 720p, 1080p, 4k
VIDEO_ASPECT_RATIO = "16:9"            # Allowed: 16:9, 9:16
NUMBER_OF_VIDEOS = 1                    # Keep at 1
STATUS_POLL_INTERVAL_SECONDS = 5        # Browser polling interval
MAX_PROMPT_LENGTH = 4000                # Maximum prompt length
VIDEO_DOWNLOAD_TIMEOUT_SECONDS = 60     # Video download timeout
APPLICATION_NAME = "AI Video Generator"

# ============================================================
```

### Supported Configurations

- **720p**: Supports 4, 6, and 8-second videos
- **1080p**: Requires 8-second videos only
- **4K**: Requires 8-second videos only

The application validates configuration combinations on startup.

## API Endpoints

### `GET /`
Returns the web application's HTML interface.

### `POST /generate`
Starts a new video generation.

**Request:**
```json
{
  "prompt": "A cinematic drone shot over a mountain lake at sunrise."
}
```

**Response:**
```json
{
  "status": "processing",
  "operation": "operations/abc123..."
}
```

### `GET /status?operation=operations/abc123`
Checks the status of a generation operation.

**Responses:**
- Processing: `{"status": "processing"}`
- Completed: `{"status": "completed"}`
- Failed: `{"status": "failed", "error": "error message"}`

### `GET /video?operation=operations/abc123`
Retrieves the generated MP4 video (only available after completion).

## Vercel Deployment

### Prerequisites

1. Vercel CLI installed:
```bash
npm install -g vercel
```

2. Gemini API key ready

### Deployment Steps

1. **Initialize Vercel project:**
```bash
vercel
```

2. **Configure environment variable:**
   - When prompted, set `GEMINI_API_KEY` to your actual API key
   - Or configure it later in Vercel dashboard

3. **Deploy to production:**
```bash
vercel --prod
```

4. **Access your application:**
   - The CLI will output your public URL: `https://your-project.vercel.app`
   - Anyone can access this URL without authentication

### Vercel Dashboard Configuration

If you prefer to set the environment variable through the Vercel dashboard:

1. Go to your project settings
2. Navigate to **Environment Variables**
3. Add `GEMINI_API_KEY` with your API key value
4. Redeploy the application

## Security

- ✅ API key stored only on server (`.env` file)
- ✅ API key never exposed to frontend JavaScript
- ✅ API key not returned in API responses
- ✅ `.env` file excluded from Git (see `.gitignore`)
- ✅ Prompt length validated (max 4000 characters)
- ✅ No user authentication or personal data storage

## Troubleshooting

### "GEMINI_API_KEY not found"
Ensure your `.env` file exists and contains:
```env
GEMINI_API_KEY=your_key_here
```

### "Configuration error"
Check the configuration section in `app.py`. Common issues:
- Using 1080p or 4k with duration < 8 seconds
- Using invalid duration (must be 4, 6, or 8)
- Using invalid resolution or aspect ratio

### Video generation fails
- Check your Gemini API quota and billing
- Verify your API key is valid
- Check server logs for detailed error messages

### Polling never completes
- This is normal for first-time videos or large models
- Generation can take several minutes
- The application will eventually complete or show an error

## Project Structure

```
veo-video-generator/
├── app.py                 # FastAPI application with frontend
├── requirements.txt       # Python dependencies
├── vercel.json           # Vercel deployment configuration
├── .env.example          # Environment variable template
├── .gitignore            # Git exclusion rules
└── README.md             # This file
```

## Testing

### Test 1: Basic Generation
Prompt: "A cinematic drone shot flying over a green mountain valley at sunrise"
- Expected: Video generation completes and plays

### Test 2: Sequential Generation
Prompt 2: "A golden retriever running on a beach at sunset"
- Expected: New independent video is generated

### Test 3: Another Generation
Prompt 3: "A futuristic autonomous tractor in an agricultural field at sunrise"
- Expected: Another independent video is generated

All three tests should work without artificial limits.

## Cost Considerations

- Each prompt generates **exactly one video**
- No automatic retries (only manual polling)
- Generate button disabled during submission
- Polling does not create new generations
- Costs depend on your Google Veo API pricing

With a $5 USD budget and 720p resolution, you can typically generate 2-3 videos.

## Development Notes

- No database required - operation IDs are maintained client-side
- No authentication layer - suitable for public demo/evaluation
- Lightweight implementation - minimal dependencies
- Browser-side polling - doesn't block the server
- Serverless-ready - designed for Vercel Functions

## License

This project is provided as-is for demonstration and evaluation purposes.

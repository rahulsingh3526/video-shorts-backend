# VideoShorts Backend API

Flask API server for processing videos and generating content using Python scripts.

## Features

- **Video to Shorts**: Converts uploaded videos to short format using `auto_short.py`
- **Text to Video**: Generates videos from text using `auto_text_short.py`
- **File Management**: Handles uploads, processing, and downloads
- **CORS Support**: Configured for frontend communication
- **Error Handling**: Comprehensive error handling and timeouts

## API Endpoints

### Health Check
```
GET /api/health
```
Returns server status.

### Process Video
```
POST /api/process-video
Content-Type: multipart/form-data

Body:
- video: Video file (mp4, mov, avi, mkv, webm)
```

Returns:
```json
{
  "success": true,
  "downloadUrl": "/api/download/shorts_uuid.mp4",
  "message": "Video processed successfully"
}
```

### Process Text
```
POST /api/process-text
Content-Type: application/json

Body:
{
  "text": "Your story or text content here..."
}
```

Returns:
```json
{
  "success": true,
  "downloadUrl": "/api/download/text_video_uuid.mp4",
  "message": "Video generated successfully"
}
```

### Download File
```
GET /api/download/<filename>
```
Downloads the processed video file.

## Local Development

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Server

```bash
python app.py
```

Server will run on `http://localhost:8000`

### 3. Test Endpoints

**Health Check:**
```bash
curl http://localhost:8000/api/health
```

**Process Video:**
```bash
curl -X POST -F "video=@test.mp4" http://localhost:8000/api/process-video
```

**Process Text:**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"text":"Your story here"}' \
  http://localhost:8000/api/process-text
```

## Deployment on Render

### 1. Create Render Account

1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Connect your repository

### 2. Deploy Service

1. **New Web Service**
2. **Connect Repository**: Select your backend repo
3. **Settings**:
   - **Name**: `videoshorts-api`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 600 --workers 1`
   - **Plan**: `Free`

### 3. Environment Variables

Set in Render dashboard:
```
PYTHON_VERSION=3.9.19
PORT=8000
```

### 4. Update Frontend

Update your frontend `.env.local`:
```
NEXT_PUBLIC_API_URL=https://your-app-name.onrender.com
```

## File Structure

```
backend/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker configuration
├── render.yaml            # Render deployment config
├── auto_short.py          # Video to shorts script
├── auto_text_short.py     # Text to video script
├── video_creation/        # Video processing modules
├── utils/                 # Utility functions
├── TTS/                   # Text-to-speech modules
├── fonts/                 # Font files
├── uploads/               # Temporary uploads (created at runtime)
├── results/               # Processed videos (created at runtime)
└── assets/                # Asset files and temp storage
```

## Processing Flow

### Video Processing
1. **Upload**: Frontend sends video file
2. **Validation**: Check file type and size
3. **Storage**: Save to temp uploads folder
4. **Processing**: Run `auto_short.py` script
5. **Output**: Move result to downloads folder
6. **Response**: Return download URL to frontend
7. **Cleanup**: Remove temporary files

### Text Processing
1. **Input**: Frontend sends text content
2. **Validation**: Check text length and content
3. **File Creation**: Save text to temporary file
4. **Processing**: Run `auto_text_short.py` script
5. **Output**: Move result to downloads folder
6. **Response**: Return download URL to frontend
7. **Cleanup**: Remove temporary files

## Security Features

- **File Type Validation**: Only allowed video formats
- **File Size Limits**: 100MB maximum
- **Secure Filenames**: Sanitized file handling
- **Temporary File Cleanup**: Automatic cleanup after processing
- **Timeout Protection**: Processing timeouts to prevent hanging
- **CORS Configuration**: Restricted to frontend domain

## Error Handling

- **File Upload Errors**: Invalid format, size limits
- **Processing Errors**: Script failures, timeouts
- **Server Errors**: Internal server issues
- **Download Errors**: Missing files, access issues

## Monitoring

- **Health Check**: `/api/health` endpoint for monitoring
- **Logging**: Console logging for debugging
- **Error Tracking**: Detailed error messages

## Limitations

- **File Size**: 100MB maximum upload
- **Processing Time**: 10-15 minute timeout
- **Concurrent Users**: Single worker (free tier)
- **Storage**: Temporary file storage only

## Scaling

For production scaling:
- **Paid Render Plan**: More CPU/memory
- **Multiple Workers**: Increase worker count
- **File Storage**: Use cloud storage (S3, etc.)
- **Queue System**: Add Redis for job queuing
- **Load Balancing**: Multiple instances
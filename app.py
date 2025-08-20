import os
import uuid
import subprocess
import tempfile
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import shutil

app = Flask(__name__)
CORS(app, origins=["https://video-shorts-frontend-one.vercel.app", "http://localhost:3000"], 
     methods=["GET", "POST", "OPTIONS"], 
     allow_headers=["Content-Type", "Authorization"])

# Configuration
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def cleanup_file(filepath):
    """Clean up temporary files"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Error cleaning up {filepath}: {e}")

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'VideoShorts API is running',
        'version': '2.0-fixed',
        'processing': 'High-quality 60-second clips in 1080p with CORS enabled'
    })

@app.route('/api/upload-video', methods=['POST'])
def upload_video():
    """Simple video upload endpoint - just accepts and stores the file"""
    try:
        # Check if file is in request
        if 'video' not in request.files:
            return jsonify({'success': False, 'error': 'No video file provided'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Validate file type
        if not allowed_file(file.filename, ALLOWED_VIDEO_EXTENSIONS):
            return jsonify({'success': False, 'error': 'Invalid file type. Supported: mp4, mov, avi, mkv, webm'}), 400
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        upload_filename = f"{file_id}.{file_extension}"
        upload_filepath = os.path.join(UPLOAD_FOLDER, upload_filename)
        
        # Save uploaded file
        file.save(upload_filepath)
        
        # Get file info
        file_size = os.path.getsize(upload_filepath)
        
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'file_id': file_id,
            'filename': upload_filename,
            'size': file_size,
            'note': 'Processing endpoint will be available separately'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Upload error: {str(e)}'}), 500

@app.route('/api/process-video', methods=['POST'])
def process_video():
    """Process video to shorts format using auto_short.py"""
    try:
        # Check if file is in request
        if 'video' not in request.files:
            return jsonify({'success': False, 'error': 'No video file provided'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Validate file type
        if not allowed_file(file.filename, ALLOWED_VIDEO_EXTENSIONS):
            return jsonify({'success': False, 'error': 'Invalid file type. Supported: mp4, mov, avi, mkv, webm'}), 400
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        input_filename = f"{file_id}.{file_extension}"
        input_filepath = os.path.join(UPLOAD_FOLDER, input_filename)
        
        # Save uploaded file
        file.save(input_filepath)
        
        # Create temporary input directory for the script
        temp_input_dir = os.path.join('assets', 'temp', f'input_{file_id}')
        os.makedirs(temp_input_dir, exist_ok=True)
        
        # Copy file to expected input location
        script_input_path = os.path.join(temp_input_dir, input_filename)
        shutil.copy2(input_filepath, script_input_path)
        
        try:
            # Run auto_short_api.py script
            result = subprocess.run([
                'python3', 'auto_short_api.py', script_input_path
            ], capture_output=True, text=True)  # No timeout - let processing take the time it needs  # 2 minute timeout
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or 'Unknown error during processing'
                return jsonify({'success': False, 'error': f'Processing failed: {error_msg}'}), 500
            
            # Find the output file
            results_dir = Path('results/creator_shorts')
            if not results_dir.exists():
                return jsonify({'success': False, 'error': 'Results directory not found'}), 500
            
            # Look for the most recent output file
            output_files = list(results_dir.glob('*.mp4'))
            if not output_files:
                return jsonify({'success': False, 'error': 'No output file generated'}), 500
            
            # Get the most recent file
            latest_file = max(output_files, key=os.path.getctime)
            
            # Move to results folder with unique name
            output_filename = f"shorts_{file_id}.mp4"
            final_output_path = os.path.join(RESULTS_FOLDER, output_filename)
            shutil.move(str(latest_file), final_output_path)
            
            # Return success with download URL
            download_url = f"/api/download/{output_filename}"
            return jsonify({
                'success': True,
                'downloadUrl': download_url,
                'message': 'Video processed successfully'
            })
            
        finally:
            # Cleanup temporary files
            cleanup_file(input_filepath)
            cleanup_file(script_input_path)
            if os.path.exists(temp_input_dir):
                shutil.rmtree(temp_input_dir, ignore_errors=True)
                
    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/api/process-text', methods=['POST'])
def process_text():
    """Generate video from text using auto_text_short.py"""
    try:
        # Get JSON data
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'success': False, 'error': 'No text provided'}), 400
        
        text_content = data['text'].strip()
        if not text_content:
            return jsonify({'success': False, 'error': 'Empty text provided'}), 400
        
        if len(text_content) < 10:
            return jsonify({'success': False, 'error': 'Text too short. Minimum 10 characters required.'}), 400
        
        # Generate unique ID for this request
        file_id = str(uuid.uuid4())
        
        # Create temporary text file
        temp_text_dir = os.path.join('assets', 'temp', f'text_{file_id}')
        os.makedirs(temp_text_dir, exist_ok=True)
        
        try:
            # Run auto_text_short_api.py script with text content directly
            result = subprocess.run([
                'python3', 'auto_text_short_api.py', text_content
            ], capture_output=True, text=True)  # No timeout - let processing take the time it needs  # 2 minute timeout for text processing
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or 'Unknown error during processing'
                return jsonify({'success': False, 'error': f'Processing failed: {error_msg}'}), 500
            
            # Find the output file
            results_dir = Path('results/creator_shorts')
            if not results_dir.exists():
                return jsonify({'success': False, 'error': 'Results directory not found'}), 500
            
            # Look for the most recent output file
            output_files = list(results_dir.glob('*.mp4'))
            if not output_files:
                return jsonify({'success': False, 'error': 'No output file generated'}), 500
            
            # Get the most recent file
            latest_file = max(output_files, key=os.path.getctime)
            
            # Move to results folder with unique name
            output_filename = f"text_video_{file_id}.mp4"
            final_output_path = os.path.join(RESULTS_FOLDER, output_filename)
            shutil.move(str(latest_file), final_output_path)
            
            # Return success with download URL
            download_url = f"/api/download/{output_filename}"
            return jsonify({
                'success': True,
                'downloadUrl': download_url,
                'message': 'Video generated successfully'
            })
            
        finally:
            # Cleanup temporary files
            cleanup_file(text_filepath)
            if os.path.exists(temp_text_dir):
                shutil.rmtree(temp_text_dir, ignore_errors=True)
                
    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """Serve processed video files for download"""
    try:
        # Secure the filename
        safe_filename = secure_filename(filename)
        file_path = os.path.join(RESULTS_FOLDER, safe_filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Serve the file
        return send_file(file_path, as_attachment=True, download_name=safe_filename)
        
    except Exception as e:
        return jsonify({'error': f'Download error: {str(e)}'}), 500

@app.route('/api/cleanup', methods=['POST'])
def cleanup_old_files():
    """Clean up old uploaded and result files (for maintenance)"""
    try:
        # This endpoint can be called periodically to clean up old files
        # For now, just return success
        return jsonify({'success': True, 'message': 'Cleanup completed'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # For development
    app.run(debug=True, host='0.0.0.0', port=8000)
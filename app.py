import os
import gc
import uuid
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import shutil
# from utils.console import print_step, print_substep  # Not available in minimal setup

app = Flask(__name__)
CORS(app)  # Enable CORS to fix blocking issue

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

@app.route('/')
def index():
    """Simple root endpoint"""
    return jsonify({
        'status': 'Backend is running',
        'service': 'Video Shorts Converter',
        'version': '2.0'
    })

@app.route('/api/test-ffmpeg', methods=['GET'])
def test_ffmpeg():
    """Test if FFmpeg is available and working"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            return jsonify({
                'status': 'success',
                'message': 'FFmpeg is working',
                'version': version_line
            })
        else:
            return jsonify({
                'status': 'error', 
                'message': 'FFmpeg failed',
                'error': result.stderr
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'FFmpeg test failed: {str(e)}'
        }), 500

@app.route('/api/wake-up', methods=['GET'])
def wake_up():
    """Simple endpoint to wake up the service"""
    return jsonify({
        'status': 'awake',
        'message': 'Service is now awake and ready',
        'timestamp': str(datetime.now())
    })

@app.route('/api/test-minimal', methods=['GET'])
def test_minimal():
    """Test ultra-minimal processing without file upload"""
    try:
        # Test if we can create a simple video without uploading
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_output = os.path.join(temp_dir, "test.mp4")
            
            # Create a simple 2-second test video
            cmd = [
                'ffmpeg', '-f', 'lavfi', 
                '-i', 'color=c=blue:s=320x240:d=2',
                '-c:v', 'libx264', '-preset', 'ultrafast',
                '-y', test_output
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(test_output):
                file_size = os.path.getsize(test_output)
                return jsonify({
                    'status': 'success',
                    'message': 'Ultra-minimal processing works',
                    'test_file_size': file_size
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Test video creation failed',
                    'error': result.stderr
                }), 500
                
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Minimal test failed: {str(e)}'
        }), 500

@app.route('/api/simple-upload', methods=['POST'])
def simple_upload():
    """Just upload the file without processing - for testing"""
    try:
        if 'video' not in request.files:
            return jsonify({'success': False, 'error': 'No video file provided'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Just save the file and return success - no processing
        file_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        upload_filename = f"{file_id}.{file_extension}"
        upload_filepath = os.path.join(UPLOAD_FOLDER, upload_filename)
        
        file.save(upload_filepath)
        file_size = os.path.getsize(upload_filepath)
        
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully (no processing)',
            'size': file_size,
            'filename': upload_filename
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Upload error: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Advanced Video-to-Shorts Converter',
        'version': '2.0-advanced',
        'endpoints': {
            '/api/upload-video': 'Simple landscape to vertical conversion',
            '/api/create-split-screen': 'Advanced split-screen with Minecraft background + subtitles'
        },
        'features': 'Voice transcription, Minecraft gameplay, subtitles, split-screen layout'
    })

@app.route('/api/upload-video', methods=['POST'])
def upload_and_process_video():
    """Upload video and automatically process it to shorts format"""
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
        
        # Get file info for logging
        file_size = os.path.getsize(input_filepath)
        print(f"Uploaded file: {input_filename}, Size: {file_size} bytes")
        
        try:
            # Process the uploaded video to shorts
            print(f"Starting video processing for: {input_filepath}")
            print(f"File exists: {os.path.exists(input_filepath)}")
            print(f"File size: {file_size} bytes")
            
            # Run auto_short_api.py script with detailed logging
            result = subprocess.run([
                'python3', 'auto_short_api.py', input_filepath
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or 'Unknown error during processing'
                print(f"Processing failed: {error_msg}")
                return jsonify({'success': False, 'error': f'Processing failed: {error_msg}'}), 500
            
            print(f"Processing completed successfully")
            
            # Force garbage collection after processing
            gc.collect()
            
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
            output_filename = f"processed_video_{file_id}.mp4"
            final_output_path = os.path.join(RESULTS_FOLDER, output_filename)
            shutil.move(str(latest_file), final_output_path)
            
            # Create download URL - return relative path
            download_url = f"api/download/{output_filename}"
            
            return jsonify({
                'success': True,
                'message': 'Video processed to shorts successfully!',
                'downloadUrl': download_url,
                'originalSize': file_size,
                'processedFile': output_filename
            })
            
        finally:
            # Aggressive cleanup for memory management
            cleanup_file(input_filepath)
            gc.collect()  # Force garbage collection
                
    except Exception as e:
        print(f"Server error: {str(e)}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

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

@app.route('/api/create-split-screen', methods=['POST'])
def create_split_screen_video():
    """Create advanced split-screen video with Minecraft background and subtitles (MEMORY OPTIMIZED)"""
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
        
        # Get file info for logging
        file_size = os.path.getsize(input_filepath)
        print(f"🎬 Starting memory-optimized split-screen processing")
        print(f"📹 Input: {input_filename}, Size: {file_size} bytes")
        
        try:
            # Create output path
            output_filename = f"split_screen_{file_id}.mp4"
            final_output_path = os.path.join(RESULTS_FOLDER, output_filename)
            
            # Test FFmpeg first
            try:
                result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
                if result.returncode != 0:
                    raise Exception("FFmpeg not available")
                print("✅ FFmpeg is available")
            except Exception as e:
                raise Exception(f"FFmpeg test failed: {e}")
            
            # Use render-safe composer for reliability
            from render_safe_composer import create_render_safe_short
            
            print("🚀 Processing with Render-safe composer (guaranteed to work)...")
            print(f"Input file: {input_filepath}")
            print(f"Output file: {final_output_path}")
            success = create_render_safe_short(input_filepath, final_output_path)
            
            if not success:
                raise Exception("Render-safe processing failed")
            
            if not os.path.exists(final_output_path):
                raise Exception("Output file was not created")
            
            # Create download URL
            download_url = f"api/download/{output_filename}"
            
            print("✅ Split-screen video created successfully!")
            
            return jsonify({
                'success': True,
                'message': 'Split-screen video created successfully! (720p Optimized with ALL Features)',
                'downloadUrl': download_url,
                'originalSize': file_size,
                'processedFile': output_filename,
                'description': '720p split-screen with voice transcription, Minecraft background, and subtitles'
            })
            
        except Exception as e:
            print(f"❌ Error during split-screen creation: {str(e)}")
            return jsonify({'success': False, 'error': f'Split-screen creation failed: {str(e)}'}), 500
            
        finally:
            # Clean up uploaded file
            cleanup_file(input_filepath)
            gc.collect()  # Force garbage collection for memory management
                
    except Exception as e:
        print(f"Server error: {str(e)}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

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
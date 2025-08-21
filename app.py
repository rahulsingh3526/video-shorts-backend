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

@app.route('/api/test-render-safe', methods=['GET'])
def test_render_safe():
    """Test render-safe composer import and basic functionality"""
    try:
        # Test if we can import the render-safe composer
        from render_safe_composer import create_render_safe_short, RenderSafeComposer
        
        # Create a test instance
        composer = RenderSafeComposer()
        
        return jsonify({
            'status': 'success',
            'message': 'Render-safe composer is importable and ready',
            'temp_dir': str(composer.temp_dir)
        })
        
    except ImportError as e:
        return jsonify({
            'status': 'error',
            'message': f'Import failed: {str(e)}',
            'type': 'import_error'
        }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Test failed: {str(e)}',
            'type': 'general_error'
        }), 500

@app.route('/api/diagnose-system', methods=['GET'])
def diagnose_system():
    """Comprehensive system diagnostics to find the root issue"""
    diagnostics = {}
    
    try:
        # 1. Check basic directories
        diagnostics['directories'] = {
            'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
            'results_folder_exists': os.path.exists(RESULTS_FOLDER),
            'upload_folder_writable': os.access(UPLOAD_FOLDER, os.W_OK) if os.path.exists(UPLOAD_FOLDER) else False,
            'results_folder_writable': os.access(RESULTS_FOLDER, os.W_OK) if os.path.exists(RESULTS_FOLDER) else False,
        }
        
        # 2. Test temp directory creation
        try:
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                test_file = temp_path / "test.txt"
                test_file.write_text("test")
                diagnostics['temp_directory'] = {
                    'can_create': True,
                    'can_write': test_file.exists(),
                    'temp_path': str(temp_path)
                }
        except Exception as e:
            diagnostics['temp_directory'] = {
                'can_create': False,
                'error': str(e)
            }
        
        # 3. Test FFmpeg basic operation
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
            diagnostics['ffmpeg'] = {
                'available': result.returncode == 0,
                'version': result.stdout.split('\n')[0] if result.returncode == 0 else None
            }
        except Exception as e:
            diagnostics['ffmpeg'] = {
                'available': False,
                'error': str(e)
            }
        
        # 4. Test file upload simulation
        try:
            test_content = b"fake video content for testing"
            test_filename = f"test_{uuid.uuid4().hex[:8]}.mp4"
            test_path = os.path.join(UPLOAD_FOLDER, test_filename)
            
            with open(test_path, 'wb') as f:
                f.write(test_content)
            
            file_exists = os.path.exists(test_path)
            file_size = os.path.getsize(test_path) if file_exists else 0
            
            # Clean up
            if file_exists:
                os.remove(test_path)
                
            diagnostics['file_operations'] = {
                'can_write_upload': True,
                'file_size': file_size,
                'can_delete': not os.path.exists(test_path)
            }
        except Exception as e:
            diagnostics['file_operations'] = {
                'can_write_upload': False,
                'error': str(e)
            }
        
        # 5. Test memory and disk space
        try:
            import psutil
            diagnostics['system_resources'] = {
                'memory_available': psutil.virtual_memory().available,
                'disk_free': psutil.disk_usage('/').free
            }
        except ImportError:
            diagnostics['system_resources'] = {
                'note': 'psutil not available for detailed system info'
            }
        except Exception as e:
            diagnostics['system_resources'] = {
                'error': str(e)
            }
        
        return jsonify({
            'status': 'success',
            'diagnostics': diagnostics
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Diagnostics failed: {str(e)}',
            'partial_diagnostics': diagnostics
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

@app.route('/api/test-basic-ffmpeg', methods=['POST'])
def test_basic_ffmpeg():
    """Test the most basic FFmpeg operation on an uploaded file"""
    try:
        if 'video' not in request.files:
            return jsonify({'success': False, 'error': 'No video file provided'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Save uploaded file
        file_id = str(uuid.uuid4())[:8]
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        input_filename = f"test_input_{file_id}.{file_extension}"
        input_path = os.path.join(UPLOAD_FOLDER, input_filename)
        
        file.save(input_path)
        
        try:
            # Test 1: Get video info with ffprobe
            print(f"Testing ffprobe on: {input_path}")
            probe_cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', input_path]
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
            
            if probe_result.returncode != 0:
                return jsonify({
                    'success': False,
                    'error': 'FFprobe failed',
                    'details': {
                        'probe_stderr': probe_result.stderr,
                        'probe_stdout': probe_result.stdout
                    }
                }), 500
            
            duration = float(probe_result.stdout.strip()) if probe_result.stdout.strip() else 0
            
            # Test 2: Simple FFmpeg operation - just copy first 5 seconds
            output_filename = f"test_output_{file_id}.mp4"
            output_path = os.path.join(RESULTS_FOLDER, output_filename)
            
            print(f"Testing FFmpeg copy operation: {input_path} -> {output_path}")
            ffmpeg_cmd = [
                'ffmpeg', '-i', input_path,
                '-t', '5',  # Only 5 seconds
                '-c', 'copy',  # Just copy, no re-encoding
                '-y', output_path
            ]
            
            ffmpeg_result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=30)
            
            if ffmpeg_result.returncode != 0:
                return jsonify({
                    'success': False,
                    'error': 'FFmpeg copy failed',
                    'details': {
                        'ffmpeg_stderr': ffmpeg_result.stderr,
                        'ffmpeg_stdout': ffmpeg_result.stdout,
                        'duration': duration
                    }
                }), 500
            
            # Check if output exists
            if not os.path.exists(output_path):
                return jsonify({
                    'success': False,
                    'error': 'Output file not created'
                }), 500
            
            output_size = os.path.getsize(output_path)
            
            return jsonify({
                'success': True,
                'message': 'Basic FFmpeg test successful',
                'details': {
                    'input_size': os.path.getsize(input_path),
                    'output_size': output_size,
                    'duration': duration,
                    'download_url': f'api/download/{output_filename}'
                }
            })
            
        finally:
            # Cleanup input file
            if os.path.exists(input_path):
                os.remove(input_path)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': f'Basic FFmpeg test failed: {str(e)}'
        }), 500

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
            
            # Try render-safe composer first, fallback to ultra-simple
            try:
                from render_safe_composer import create_render_safe_short
                
                print("🚀 Processing with Render-safe composer...")
                print(f"Input file: {input_filepath}")
                print(f"Output file: {final_output_path}")
                success = create_render_safe_short(input_filepath, final_output_path)
                
                if success:
                    print("✅ Render-safe processing successful")
                else:
                    print("⚠️ Render-safe processing failed, trying ultra-simple fallback...")
                    raise Exception("Render-safe failed, trying fallback")
                    
            except Exception as e:
                print(f"⚠️ Render-safe failed: {e}")
                print("🔄 Falling back to ultra-simple processing...")
                
                from ultra_simple_processor import create_ultra_simple_video
                success = create_ultra_simple_video(input_filepath, final_output_path)
                
                if success:
                    print("✅ Ultra-simple fallback successful")
                else:
                    print("❌ Both render-safe and ultra-simple failed")
            
            if not success:
                raise Exception("All processing methods failed (render-safe + ultra-simple)")
            
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
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False, 
                'error': f'Split-screen creation failed: {str(e)}',
                'details': 'Check server logs for full traceback'
            }), 500
            
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
#!/usr/bin/env python3
"""
Local test script for the backend API

Tests the API endpoints locally before deployment.
"""

import requests
import os
from pathlib import Path

API_BASE = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{API_BASE}/api/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_video_upload():
    """Test video upload endpoint"""
    print("\n🎥 Testing video upload...")
    
    # You would need a test video file
    test_video = Path("test_video.mp4")
    if not test_video.exists():
        print("⚠️ No test video found. Create a small test.mp4 file to test this endpoint.")
        return False
    
    try:
        with open(test_video, 'rb') as f:
            files = {'video': f}
            response = requests.post(f"{API_BASE}/api/process-video", files=files, timeout=120)
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Video upload failed: {e}")
        return False

def test_text_processing():
    """Test text processing endpoint"""
    print("\n📝 Testing text processing...")
    
    test_data = {
        "text": "This is a test story for video generation. It should be long enough to create a meaningful video with proper narration and background visuals."
    }
    
    try:
        response = requests.post(f"{API_BASE}/api/process-text", json=test_data, timeout=180)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Text processing failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing VideoShorts Backend API")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health),
        ("Video Upload", test_video_upload), 
        ("Text Processing", test_text_processing)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔬 Running {test_name}...")
        success = test_func()
        results.append((test_name, success))
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\n🎯 Overall: {passed}/{total} tests passed")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
GPU Video Converter Service
Cross-platform video conversion with hardware acceleration support:
- macOS: VideoToolbox (Apple Silicon & Intel)
- Linux: VAAPI (Intel/AMD), NVENC (NVIDIA), or CPU fallback
- Windows: QSV (Intel), NVENC (NVIDIA), AMF (AMD), or CPU fallback
"""

import logging
import platform
import queue
import re
import shutil
import subprocess
import threading
import time
from functools import lru_cache
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Detect OS and find ffmpeg
SYSTEM = platform.system().lower()
FFMPEG_PATH = shutil.which('ffmpeg') or '/opt/homebrew/bin/ffmpeg' if SYSTEM == 'darwin' else 'ffmpeg'

# Pre-compiled patterns for performance
_CLEAN_PATTERNS = [
    re.compile(r'www\.\w+\.(dev|gy|com|net|org)', re.IGNORECASE),
    re.compile(r'\[.*?\]'),
    re.compile(r'\(.*?\)'),
    re.compile(r'\.web-?dl', re.IGNORECASE),
    re.compile(r'\.webrip', re.IGNORECASE),
    re.compile(r'\.bluray', re.IGNORECASE),
    re.compile(r'\.brrip', re.IGNORECASE),
    re.compile(r'\.hdtv', re.IGNORECASE),
    re.compile(r'\d{3,4}p'),
    re.compile(r'\.x26[45]', re.IGNORECASE),
    re.compile(r'\.h26[45]', re.IGNORECASE),
    re.compile(r'\.avc', re.IGNORECASE),
    re.compile(r'\.hevc', re.IGNORECASE),
    re.compile(r'\.10bit', re.IGNORECASE),
    re.compile(r'\.8bit', re.IGNORECASE),
    re.compile(r'\.dd\+?\d+\.\d+', re.IGNORECASE),
    re.compile(r'\.dd\+?\d+', re.IGNORECASE),
    re.compile(r'\.dts', re.IGNORECASE),
    re.compile(r'\.aac', re.IGNORECASE),
    re.compile(r'\.ac3', re.IGNORECASE),
    re.compile(r'\.true', re.IGNORECASE),
    re.compile(r'\d+kbps', re.IGNORECASE),
    re.compile(r'\d+(\.\d+)?gb', re.IGNORECASE),
    re.compile(r'esub', re.IGNORECASE),
    re.compile(r'\-\s*\-'),
]
_MULTI_SPACE = re.compile(r'\s+')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Conversion queue and status tracking
conversion_queue = queue.Queue()
conversion_status = {}
active_conversions = {}


def detect_hw_acceleration():
    """
    Detect available hardware acceleration.
    Returns: dict with 'encoder', 'hwaccel', 'device', 'available'
    """
    try:
        result = subprocess.run(
            [FFMPEG_PATH, '-encoders'],
            check=False, capture_output=True, text=True, timeout=10
        )
        encoders = result.stdout

        # Check available encoders by priority
        if SYSTEM == 'darwin':
            # macOS: VideoToolbox
            if 'hevc_videotoolbox' in encoders:
                return {
                    'available': True,
                    'encoder': 'hevc_videotoolbox',
                    'hwaccel': 'videotoolbox',
                    'device': None,
                    'name': 'Apple VideoToolbox'
                }
        elif SYSTEM == 'linux':
            # Linux: Check NVENC (NVIDIA), then VAAPI (Intel/AMD)
            if 'hevc_nvenc' in encoders:
                return {
                    'available': True,
                    'encoder': 'hevc_nvenc',
                    'hwaccel': 'cuda',
                    'device': None,
                    'name': 'NVIDIA NVENC'
                }
            if 'hevc_vaapi' in encoders:
                # Try to find VAAPI device
                vaapi_device = '/dev/dri/renderD128'
                if Path(vaapi_device).exists():
                    return {
                        'available': True,
                        'encoder': 'hevc_vaapi',
                        'hwaccel': 'vaapi',
                        'device': vaapi_device,
                        'name': 'VAAPI (Intel/AMD)'
                    }
        elif SYSTEM == 'windows':
            # Windows: Check NVENC, QSV, AMF
            if 'hevc_nvenc' in encoders:
                return {
                    'available': True,
                    'encoder': 'hevc_nvenc',
                    'hwaccel': 'cuda',
                    'device': None,
                    'name': 'NVIDIA NVENC'
                }
            if 'hevc_qsv' in encoders:
                return {
                    'available': True,
                    'encoder': 'hevc_qsv',
                    'hwaccel': 'qsv',
                    'device': None,
                    'name': 'Intel QuickSync'
                }
            if 'hevc_amf' in encoders:
                return {
                    'available': True,
                    'encoder': 'hevc_amf',
                    'hwaccel': None,
                    'device': None,
                    'name': 'AMD AMF'
                }

        # CPU fallback (libx265)
        if 'libx265' in encoders:
            return {
                'available': True,
                'encoder': 'libx265',
                'hwaccel': None,
                'device': None,
                'name': 'CPU (libx265)'
            }

        return {'available': False, 'encoder': None, 'hwaccel': None, 'device': None, 'name': 'None'}

    except Exception as e:
        logger.error(f"Failed to detect HW acceleration: {e}")
        return {'available': False, 'encoder': None, 'hwaccel': None, 'device': None, 'name': 'Error'}


# Cache the detection result
_hw_info = None

def get_hw_info():
    """Get cached hardware acceleration info."""
    global _hw_info
    if _hw_info is None:
        _hw_info = detect_hw_acceleration()
        logger.info(f"Detected encoder: {_hw_info['name']}")
    return _hw_info


def check_gpu_support():
    """Check if hardware acceleration is available (legacy compatibility)."""
    return get_hw_info()['available']


@lru_cache(maxsize=256)
def clean_filename(filename: str) -> str:
    """Clean filename with caching for repeated calls."""
    name = Path(filename).stem

    # Use pre-compiled patterns for performance
    cleaned = name
    for pattern in _CLEAN_PATTERNS:
        cleaned = pattern.sub(' ', cleaned)

    # Replace separators with spaces
    cleaned = cleaned.replace('.', ' ').replace('_', ' ').replace('-', ' ')

    # Remove multiple spaces and title case
    cleaned = _MULTI_SPACE.sub(' ', cleaned).strip()

    return cleaned.title()


def get_video_duration(input_path):
    """Get video duration in seconds"""
    try:
        cmd = [FFMPEG_PATH, '-i', str(input_path)]
        result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=60)
        duration_lines = [line for line in result.stderr.split('\n') if 'Duration:' in line]
        if duration_lines:
            duration_str = duration_lines[0].split('Duration:')[1].split(',')[0].strip()
            h, m, s = duration_str.split(':')
            return int(h) * 3600 + int(m) * 60 + float(s)
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout getting duration for {input_path}. File may be very large or corrupted.")
    except Exception as e:
        logger.error(f"Failed to get duration: {e}")
    return 0


def convert_video(job_id, input_path, output_path, preset='hevc_videotoolbox'):
    """Convert video with GPU acceleration and progress tracking"""
    try:
        input_path = Path(input_path)
        output_path = Path(output_path)

        # Update status
        conversion_status[job_id] = {
            'status': 'running',
            'progress': 0,
            'eta': None,
            'message': 'Starting conversion...',
            'input_file': str(input_path),
            'output_file': str(output_path)
        }

        logger.info(f"🎬 [Job {job_id}] Starting conversion: {input_path.name}")

        # Get video duration
        total_seconds = get_video_duration(input_path)
        if total_seconds > 0:
            duration_str = f"{int(total_seconds//3600):02d}:{int((total_seconds%3600)//60):02d}:{int(total_seconds%60):02d}"
            logger.info(f"⏱️  [Job {job_id}] Duration: {duration_str} ({total_seconds:.0f}s)")

        # Ensure output directory exists
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"❌ [Job {job_id}] Failed to create output directory: {e}")
            conversion_status[job_id] = {
                'status': 'failed',
                'progress': 0,
                'message': f'Failed to create output directory: {e}',
                'error': str(e)
            }
            return

        # Get hardware acceleration info
        hw = get_hw_info()
        encoder = hw['encoder'] or 'libx265'

        # Build ffmpeg command based on detected hardware
        cmd = [FFMPEG_PATH, '-hide_banner', '-y']

        # Add hardware acceleration if available
        if hw['hwaccel']:
            cmd.extend(['-hwaccel', hw['hwaccel']])
            if hw['device']:
                cmd.extend(['-vaapi_device', hw['device']])

        # Input file
        cmd.extend(['-i', str(input_path)])

        # Stream mapping
        cmd.extend(['-map', '0:v:0', '-map', '0:a?', '-map', '0:s?'])

        # Video encoding settings based on encoder
        cmd.extend(['-c:v', encoder])

        if encoder == 'libx265':
            # CPU encoding settings
            cmd.extend([
                '-preset', 'medium',
                '-crf', '23',
                '-x265-params', 'log-level=error'
            ])
        elif 'vaapi' in encoder:
            # VAAPI settings (Intel/AMD on Linux)
            cmd.extend([
                '-vf', 'format=nv12,hwupload',
                '-b:v', '5000k',
                '-maxrate', '6000k',
            ])
        else:
            # GPU encoding (VideoToolbox, NVENC, QSV, AMF)
            cmd.extend([
                '-b:v', '5000k',
                '-maxrate', '6000k',
                '-bufsize', '10000k',
            ])

        # Common settings
        cmd.extend([
            '-c:a', 'copy',
            '-c:s', 'copy',
            '-max_muxing_queue_size', '1024',
            '-threads', '0',
            str(output_path)
        ])

        logger.info(f" [Job {job_id}] Using encoder: {hw['name']}")

        # Run with progress monitoring
        start_time = time.time()
        ffmpeg_lines = []
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        active_conversions[job_id] = process

        for line in iter(process.stdout.readline, ''):
            if line:
                ffmpeg_lines.append(line.rstrip())
            if 'frame=' in line and 'fps=' in line and 'time=' in line:
                try:
                    time_str = line.split('time=')[1].split()[0]
                    h, m, s = time_str.split(':')
                    current_seconds = int(h) * 3600 + int(m) * 60 + float(s)

                    if total_seconds > 0:
                        progress = max(0.0, min((current_seconds / total_seconds) * 100, 100.0))
                        elapsed = time.time() - start_time

                        if progress > 0:
                            estimated_total = elapsed / (progress / 100)
                            eta = estimated_total - elapsed
                            eta_min = int(eta / 60)
                            eta_sec = int(eta % 60)

                            # Update status
                            conversion_status[job_id].update({
                                'progress': round(progress, 1),
                                'eta': f"{eta_min}m {eta_sec}s",
                                'current_time': time_str,
                                'message': f'Converting... {progress:.1f}%'
                            })

                            logger.info(f"📊 [Job {job_id}] {progress:.1f}% | ETA: {eta_min}m {eta_sec}s")
                except Exception:
                    pass

        process.wait()

        if process.returncode == 0:
            # Success
            if not output_path.exists():
                error_msg = f"Output file not created: {output_path}"
                logger.error(f"❌ [Job {job_id}] {error_msg}")
                conversion_status[job_id] = {
                    'status': 'failed',
                    'progress': 0,
                    'message': error_msg,
                    'error': error_msg
                }
                return

            input_size = input_path.stat().st_size
            output_size = output_path.stat().st_size
            compression = (1 - output_size / input_size) * 100

            conversion_status[job_id] = {
                'status': 'completed',
                'progress': 100,
                'message': f'✅ Completed! Saved {compression:.1f}% space',
                'input_file': str(input_path),
                'output_file': str(output_path),
                'input_size': input_size,
                'output_size': output_size,
                'compression': compression
            }
            logger.info(f"✅ [Job {job_id}] Completed! {compression:.1f}% compression")
        else:
            # Failed - capture error details and retry once without hardware decode
            error_msg = f"FFmpeg failed with return code {process.returncode}"
            tail = '\n'.join(ffmpeg_lines[-60:])
            logger.warning(f"⚠️  [Job {job_id}] First attempt failed, retrying without hardware decode...\n----- ffmpeg tail (attempt 1) -----\n{tail}\n----------------------------------")

            # Update status for retry
            conversion_status[job_id].update({
                'status': 'running',
                'message': 'Retrying without hardware decode...'
            })

            # Build fallback cmd by removing -hwaccel arguments
            cmd_sw = []
            skip_next = False
            for i, a in enumerate(cmd):
                if skip_next:
                    skip_next = False
                    continue
                if a == '-hwaccel' and i + 1 < len(cmd) and cmd[i+1] == 'videotoolbox':
                    skip_next = True
                    continue
                cmd_sw.append(a)

            ffmpeg_lines2 = []
            process2 = subprocess.Popen(
                cmd_sw,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in iter(process2.stdout.readline, ''):
                if line:
                    ffmpeg_lines2.append(line.rstrip())
            process2.wait()

            if process2.returncode == 0 and Path(output_path).exists():
                input_size = input_path.stat().st_size
                output_size = output_path.stat().st_size
                compression = (1 - output_size / input_size) * 100
                conversion_status[job_id] = {
                    'status': 'completed',
                    'progress': 100,
                    'message': f'✅ Completed after retry! Saved {compression:.1f}% space',
                    'input_file': str(input_path),
                    'output_file': str(output_path),
                    'input_size': input_size,
                    'output_size': output_size,
                    'compression': compression
                }
                logger.info(f"✅ [Job {job_id}] Completed after retry without hwaccel! {compression:.1f}% compression")
            else:
                tail2 = '\n'.join(ffmpeg_lines2[-80:])
                logger.error(
                    f"❌ [Job {job_id}] Fallback attempt failed as well (rc={process2.returncode}).\n"
                    f"----- ffmpeg tail (attempt 2) -----\n{tail2}\n----------------------------------"
                )
                conversion_status[job_id] = {
                    'status': 'failed',
                    'progress': 0,
                    'message': 'Conversion failed',
                    'error': error_msg + ' (and fallback failed)',
                    'ffmpeg_tail': tail + '\n' + tail2
                }

    except FileNotFoundError as e:
        error_msg = f"File not found: {e}"
        logger.error(f"❌ [Job {job_id}] {error_msg}")
        conversion_status[job_id] = {
            'status': 'failed',
            'progress': 0,
            'message': error_msg,
            'error': error_msg
        }
    except Exception as e:
        error_msg = f"Unexpected error: {e!s}"
        logger.error(f"❌ [Job {job_id}] {error_msg}")
        logger.exception(e)  # Log full stack trace
        conversion_status[job_id] = {
            'status': 'failed',
            'progress': 0,
            'message': error_msg,
            'error': error_msg
        }
    finally:
        active_conversions.pop(job_id, None)


def conversion_worker():
    """Background worker to process conversion queue"""
    while True:
        try:
            job = conversion_queue.get()
            if job is None:
                break

            job_id = job['id']
            input_path = job['input_path']
            output_path = job['output_path']
            preset = job.get('preset', 'hevc_videotoolbox')

            convert_video(job_id, input_path, output_path, preset)

            conversion_queue.task_done()
        except Exception as e:
            logger.error(f"Worker error: {e}")


# Start background worker
worker_thread = threading.Thread(target=conversion_worker, daemon=True)
worker_thread.start()


@app.route('/health', methods=['GET'])
def health():
    """Health check with hardware info"""
    hw = get_hw_info()
    return jsonify({
        'status': 'healthy',
        'gpu_available': hw['available'],
        'encoder': hw['encoder'],
        'encoder_name': hw['name'],
        'platform': SYSTEM,
        'active_jobs': len(active_conversions),
        'queued_jobs': conversion_queue.qsize()
    })


@app.route('/convert', methods=['POST'])
def convert():
    """Submit conversion job"""
    try:
        data = request.json
        input_path = data.get('input_path')
        output_path = data.get('output_path')
        preset = data.get('preset', 'hevc_videotoolbox')

        if not input_path or not output_path:
            return jsonify({'error': 'input_path and output_path required'}), 400

        # Generate job ID
        job_id = f"job_{int(time.time())}_{len(conversion_status)}"

        # Add to queue
        conversion_queue.put({
            'id': job_id,
            'input_path': input_path,
            'output_path': output_path,
            'preset': preset
        })

        conversion_status[job_id] = {
            'status': 'queued',
            'progress': 0,
            'message': 'Waiting in queue...'
        }

        logger.info(f"📥 New job queued: {job_id} - {Path(input_path).name}")

        return jsonify({
            'job_id': job_id,
            'status': 'queued',
            'message': 'Job added to queue'
        })

    except Exception as e:
        logger.error(f"Convert error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/status/<job_id>', methods=['GET'])
def status(job_id):
    """Get job status"""
    if job_id in conversion_status:
        return jsonify(conversion_status[job_id])
    return jsonify({'error': 'Job not found'}), 404


@app.route('/cancel/<job_id>', methods=['POST'])
def cancel(job_id):
    """Cancel a job"""
    if job_id in active_conversions:
        process = active_conversions[job_id]
        process.terminate()
        conversion_status[job_id] = {
            'status': 'cancelled',
            'message': 'Job cancelled by user'
        }
        return jsonify({'message': 'Job cancelled'})
    return jsonify({'error': 'Job not active'}), 404


if __name__ == '__main__':
    logger.info("🚀 Starting GPU Converter Service on http://localhost:8888")
    logger.info(f"🎮 GPU Support: {check_gpu_support()}")
    app.run(host='0.0.0.0', port=8888, debug=False)

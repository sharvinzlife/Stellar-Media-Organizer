"""
Video Conversion Service with GPU Acceleration
Optimized for Apple Silicon (M2 Pro) using VideoToolbox
"""
import subprocess
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class VideoConverter:
    """Handle video conversion with hardware acceleration"""
    
    # Best codec settings for Plex compatibility
    CODEC_PRESETS = {
        'hevc_best': {
            'codec': 'hevc_videotoolbox',
            'codec_fallback': 'libx265',  # Software fallback
            'description': 'H.265/HEVC - Best Quality (50% smaller, GPU accelerated)',
            'quality': 'b:v 5000k',
            'quality_fallback': 'crf 23',  # Software quality
            'extension': 'mkv',
            'plex_compatible': True,
            'recommended': True
        },
        'h264_compatible': {
            'codec': 'h264_videotoolbox',
            'codec_fallback': 'libx264',  # Software fallback
            'description': 'H.264/AVC - Universal Compatible',
            'quality': 'b:v 6000k',
            'quality_fallback': 'crf 23',  # Software quality
            'extension': 'mp4',
            'plex_compatible': True,
            'recommended': False
        },
        'hevc_ultra': {
            'codec': 'hevc_videotoolbox',
            'codec_fallback': 'libx265',  # Software fallback
            'description': 'H.265/HEVC - Ultra Quality (Archival)',
            'quality': 'q:v 75',
            'quality_fallback': 'crf 18',  # Software quality (lower = better)
            'extension': 'mkv',
            'plex_compatible': True,
            'recommended': False
        }
    }
    
    def __init__(self):
        import os
        self.use_host_ffmpeg = os.getenv('USE_HOST_FFMPEG', 'false').lower() == 'true'
        self.use_external_gpu = os.getenv('USE_EXTERNAL_GPU', 'false').lower() == 'true'
        self.external_gpu_url = os.getenv('EXTERNAL_GPU_URL', 'http://host.docker.internal:8888')
        self.ffmpeg_cmd = '/usr/local/bin/ffmpeg-host' if self.use_host_ffmpeg else 'ffmpeg'
        self.has_gpu_encoding = self.check_hardware_encoding()
    
    def check_hardware_encoding(self) -> bool:
        """Check if VideoToolbox hardware encoding is available"""
        try:
            result = subprocess.run(
                [self.ffmpeg_cmd, '-encoders'],
                capture_output=True,
                text=True,
                timeout=5
            )
            has_hevc = 'hevc_videotoolbox' in result.stdout
            has_h264 = 'h264_videotoolbox' in result.stdout
            
            if has_hevc and has_h264:
                logger.info("✅ GPU encoding available (VideoToolbox)")
                return True
            else:
                logger.warning("⚠️  VideoToolbox not available, will use software encoding")
                return False
        except Exception as e:
            logger.error(f"Failed to check hardware encoding: {e}")
            return False
    
    def _clean_filename(self, filename: str) -> str:
        """Clean and format filename like the organize operation"""
        # Remove extension
        name = Path(filename).stem
        
        # Remove common quality indicators and formats
        patterns_to_remove = [
            r'\[.*?\]',  # Remove [anything]
            r'\(.*?\)',  # Remove (anything)
            r'\.web-?dl',
            r'\.webrip',
            r'\.bluray',
            r'\.brrip',
            r'\.hdtv',
            r'\d{3,4}p',  # Remove resolution like 1080p, 720p
            r'\.x264', r'\.x265', r'\.h264', r'\.h265',
            r'\.avc', r'\.hevc',
            r'\.10bit', r'\.8bit',
            r'\.dd\d+\.\d+', r'\.dd\d+',  # Remove audio info like DD5.1
            r'\.dts', r'\.aac', r'\.ac3',
            r'\-.*team.*', r'\-.*group.*',  # Remove release group
        ]
        
        cleaned = name
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Replace dots and underscores with spaces
        cleaned = cleaned.replace('.', ' ').replace('_', ' ')
        
        # Remove multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Title case
        cleaned = cleaned.title()
        
        return cleaned
    
    def convert_video_external_gpu(
        self,
        input_path: Path,
        output_dir: Path,
        preset: str = 'hevc_best'
    ) -> Dict[str, Any]:
        """Convert video using external GPU service on host"""
        import requests
        import time
        
        try:
            # Prepare paths
            clean_name = self._clean_filename(input_path.name)
            output_filename = f"{clean_name}.mkv"
            output_path = output_dir / output_filename
            
            logger.info(f"🖥️ Using external GPU service: {self.external_gpu_url}")
            
            # Submit job to external service
            response = requests.post(
                f"{self.external_gpu_url}/convert",
                json={
                    'input_path': str(input_path),
                    'output_path': str(output_path),
                    'preset': 'hevc_videotoolbox'
                },
                timeout=10
            )
            
            if response.status_code != 200:
                raise Exception(f"GPU service error: {response.text}")
            
            job_data = response.json()
            job_id = job_data['job_id']
            
            logger.info(f"📥 Job submitted: {job_id}")
            
            # Poll for status
            while True:
                time.sleep(5)  # Poll every 5 seconds
                
                status_response = requests.get(
                    f"{self.external_gpu_url}/status/{job_id}",
                    timeout=5
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status_val = status_data.get('status')
                    progress = status_data.get('progress', 0)
                    eta = status_data.get('eta', 'Unknown')
                    
                    logger.info(f"📊 GPU Progress: {progress}% | ETA: {eta}")
                    
                    if status_val == 'completed':
                        logger.info(f"✅ GPU conversion completed!")
                        return {
                            'success': True,
                            'input_file': str(input_path),
                            'input_name': input_path.name,
                            'output_file': str(output_path),
                            'output_name': output_path.name,
                            'input_size': status_data.get('input_size', 0),
                            'output_size': status_data.get('output_size', 0),
                            'compression_ratio': status_data.get('compression', 0)
                        }
                    elif status_val == 'failed':
                        raise Exception(status_data.get('error', 'Conversion failed'))
                        
        except Exception as e:
            logger.error(f"❌ External GPU error: {e}")
            return {
                'success': False,
                'error': str(e),
                'input_file': str(input_path),
                'output_file': None
            }
    
    def convert_video(
        self,
        input_path: Path,
        output_dir: Path,
        preset: str = 'hevc_best',
        keep_audio: bool = True,
        keep_subtitles: bool = True,
        organize_name: bool = True
    ) -> Dict[str, Any]:
        """
        Convert video using GPU acceleration
        
        Args:
            input_path: Source video file
            output_dir: Output directory
            preset: Codec preset from CODEC_PRESETS
            keep_audio: Keep all audio tracks
            keep_subtitles: Keep all subtitle tracks
            
        Returns:
            Dictionary with conversion results
        """
        if preset not in self.CODEC_PRESETS:
            raise ValueError(f"Invalid preset: {preset}")
        
        # Use external GPU service if enabled
        if self.use_external_gpu:
            return self.convert_video_external_gpu(input_path, output_dir, preset)
        
        codec_config = self.CODEC_PRESETS[preset]
        
        # Check if hardware encoding is available, fallback to software
        use_hardware = self.has_gpu_encoding
        codec = codec_config['codec'] if use_hardware else codec_config['codec_fallback']
        quality = codec_config['quality'] if use_hardware else codec_config['quality_fallback']
        
        logger.info(f"🎯 Using {'GPU' if use_hardware else 'Software'} encoding with {codec}")
        
        # Clean and organize filename
        if organize_name:
            clean_name = self._clean_filename(input_path.name)
            output_filename = f"{clean_name}.{codec_config['extension']}"
        else:
            output_filename = f"{input_path.stem}_converted.{codec_config['extension']}"
        
        output_path = output_dir / output_filename
        
        # Build FFmpeg command
        cmd = [
            self.ffmpeg_cmd,
            '-i', str(input_path),
            '-c:v', codec,  # Video codec (hardware or software)
        ]
        
        # Add quality settings
        quality_parts = quality.split()
        if len(quality_parts) == 2:
            cmd.extend(['-' + quality_parts[0], quality_parts[1]])
        
        # Add preset for software encoding
        if not use_hardware and 'libx265' in codec:
            cmd.extend(['-preset', 'medium'])  # Balance speed/quality
        
        # Add tag for HEVC compatibility
        if 'hevc' in codec or 'h265' in codec:
            cmd.extend(['-tag:v', 'hvc1'])
        
        # Audio settings
        if keep_audio:
            cmd.extend([
                '-c:a', 'copy',  # Copy audio without re-encoding
            ])
        else:
            cmd.extend(['-an'])  # No audio
        
        # Subtitle settings
        if keep_subtitles:
            cmd.extend([
                '-c:s', 'copy',  # Copy subtitles
            ])
        else:
            cmd.extend(['-sn'])  # No subtitles
        
        # Additional settings for quality and compatibility
        cmd.extend([
            '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
            '-movflags', '+faststart',  # Enable fast start for streaming
            '-y',  # Overwrite output
            str(output_path)
        ])
        
        logger.info(f"🎬 Converting: {input_path.name}")
        logger.info(f"📝 Using preset: {preset} ({codec_config['description']})")
        logger.info(f"🚀 Command: {' '.join(cmd)}")
        
        try:
            # Get input file size
            input_size = input_path.stat().st_size
            
            logger.info(f"🎬 Starting conversion: {input_path.name}")
            logger.info(f"⚙️  Command: {' '.join(cmd)}")
            
            if self.use_host_ffmpeg:
                logger.info(f"🖥️🚀 Using HOST ffmpeg with M2 Pro GPU acceleration!")
            
            # Run with real-time progress output
            import time
            start_time = time.time()
            
            # Get video duration first
            duration_cmd = [self.ffmpeg_cmd, '-i', str(input_path)]
            duration_result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=60)
            duration_line = [line for line in duration_result.stderr.split('\n') if 'Duration:' in line]
            total_seconds = 0
            if duration_line:
                duration_str = duration_line[0].split('Duration:')[1].split(',')[0].strip()
                h, m, s = duration_str.split(':')
                total_seconds = int(h) * 3600 + int(m) * 60 + float(s)
                logger.info(f"⏱️  Total duration: {duration_str} ({total_seconds:.0f} seconds)")
            
            # Run conversion with progress monitoring
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            output_lines = []
            last_log_time = time.time()
            
            for line in iter(process.stdout.readline, ''):
                output_lines.append(line)
                
                # Parse ffmpeg progress
                if 'frame=' in line and 'fps=' in line:
                    # Extract time processed
                    if 'time=' in line:
                        time_str = line.split('time=')[1].split()[0]
                        try:
                            h, m, s = time_str.split(':')
                            current_seconds = int(h) * 3600 + int(m) * 60 + float(s)
                            
                            if total_seconds > 0:
                                progress = (current_seconds / total_seconds) * 100
                                elapsed = time.time() - start_time
                                if progress > 0:
                                    estimated_total = elapsed / (progress / 100)
                                    eta = estimated_total - elapsed
                                    eta_min = int(eta / 60)
                                    eta_sec = int(eta % 60)
                                    
                                    # Log every 10 seconds
                                    if time.time() - last_log_time > 10:
                                        logger.info(f"📊 Progress: {progress:.1f}% | ETA: {eta_min}m {eta_sec}s | Time: {time_str}")
                                        last_log_time = time.time()
                        except Exception:
                            pass
            
            process.wait()
            result_code = process.returncode
            result_output = ''.join(output_lines)
            
            # Create result object compatible with old code
            class Result:
                def __init__(self, returncode, stderr):
                    self.returncode = returncode
                    self.stderr = stderr
            
            result = Result(result_code, result_output)
            
            if result.returncode != 0:
                logger.error(f"❌ Conversion failed: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr,
                    'input_file': str(input_path),
                    'output_file': None
                }
            
            # Get output file size
            output_size = output_path.stat().st_size
            compression_ratio = (1 - output_size / input_size) * 100
            
            logger.info(f"✅ Conversion successful!")
            logger.info(f"📊 Original size: {input_size / (1024**3):.2f} GB")
            logger.info(f"📊 New size: {output_size / (1024**3):.2f} GB")
            logger.info(f"📉 Compression: {compression_ratio:.1f}%")
            
            return {
                'success': True,
                'input_file': str(input_path),
                'input_name': input_path.name,
                'output_file': str(output_path),
                'output_name': output_path.name,
                'input_size': input_size,
                'output_size': output_size,
                'compression_ratio': compression_ratio,
                'codec': codec_config['codec'],
                'preset': preset
            }
            
        except subprocess.TimeoutExpired:
            logger.error("❌ Conversion timeout (> 1 hour)")
            return {
                'success': False,
                'error': 'Conversion timeout',
                'input_file': str(input_path),
                'output_file': None
            }
        except Exception as e:
            logger.error(f"❌ Conversion error: {e}")
            return {
                'success': False,
                'error': str(e),
                'input_file': str(input_path),
                'output_file': None
            }
    
    def batch_convert(
        self,
        input_dir: Path,
        output_dir: Path,
        preset: str = 'hevc_best',
        file_extensions: tuple = ('.mkv', '.mp4', '.avi', '.mov')
    ) -> Dict[str, Any]:
        """
        Batch convert all videos in a directory
        
        Args:
            input_dir: Source directory
            output_dir: Output directory
            preset: Codec preset
            file_extensions: File extensions to process
            
        Returns:
            Dictionary with batch conversion results
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = []
        total_input_size = 0
        total_output_size = 0
        
        video_files = []
        for ext in file_extensions:
            video_files.extend(input_dir.rglob(f"*{ext}"))
        
        logger.info(f"🎬 Found {len(video_files)} video files to convert")
        
        if len(video_files) == 0:
            logger.warning(f"⚠️  No video files found in {input_dir}")
            logger.info(f"💡 Looking for extensions: {', '.join(file_extensions)}")
        
        for video_file in video_files:
            result = self.convert_video(
                input_path=video_file,
                output_dir=output_dir,
                preset=preset
            )
            results.append(result)
            
            if result['success']:
                total_input_size += result['input_size']
                total_output_size += result['output_size']
        
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        overall_compression = 0
        if total_input_size > 0:
            overall_compression = (1 - total_output_size / total_input_size) * 100
        
        return {
            'success': failed == 0,
            'total_files': len(results),
            'successful': successful,
            'failed': failed,
            'total_input_size': total_input_size,
            'total_output_size': total_output_size,
            'compression_ratio': overall_compression,
            'results': results
        }
    
    @staticmethod
    def get_available_presets() -> Dict[str, Dict[str, Any]]:
        """Get all available codec presets"""
        return VideoConverter.CODEC_PRESETS

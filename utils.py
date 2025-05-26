"""
Utility functions for the Audio Transcription App.
Includes error handling, audio processing, and file validation.
"""
import os
import time
import logging
from typing import Optional, Tuple, List, Generator
from io import BytesIO
from functools import wraps

import streamlit as st
from pydub import AudioSegment
from openai import OpenAI

from config import config

# Set up logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def retry_with_exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    jitter: bool = True
):
    """
    Decorator to retry functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter to delays
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import random
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                        raise
                    
                    delay = initial_delay * (exponential_base ** attempt)
                    if jitter:
                        delay *= (0.5 + random.random())
                    
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {delay:.2f}s")
                    time.sleep(delay)
            
            return None
        return wrapper
    return decorator

def validate_audio_file(uploaded_file) -> Tuple[bool, Optional[str]]:
    """
    Validate uploaded audio file.
    
    Args:
        uploaded_file: Streamlit uploaded file object
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if uploaded_file is None:
        return False, "No file uploaded"
    
    # Check file size
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    if file_size_mb > config.transcription.max_file_size_mb:
        return False, f"File size ({file_size_mb:.1f}MB) exceeds limit of {config.transcription.max_file_size_mb}MB"
    
    # Check file extension
    file_extension = uploaded_file.name.split('.')[-1].lower()
    if file_extension not in config.formats.upload_types:
        return False, f"Unsupported file format: {file_extension}"
    
    return True, None

def preprocess_audio(audio_bytes: bytes) -> AudioSegment:
    """
    Preprocess audio for better transcription results.
    
    Args:
        audio_bytes: Raw audio file bytes
    
    Returns:
        Preprocessed AudioSegment
    """
    try:
        # Load audio
        audio = AudioSegment.from_file(BytesIO(audio_bytes))
        
        # Add silence padding at the beginning
        silence = AudioSegment.silent(duration=config.transcription.silence_padding_ms)
        audio = silence + audio
        
        # Normalize audio levels (optional - can improve transcription)
        # audio = audio.normalize()
        
        logger.info(f"Preprocessed audio: duration={len(audio)/1000:.2f}s, channels={audio.channels}")
        return audio
        
    except Exception as e:
        logger.error(f"Audio preprocessing failed: {e}")
        raise

def create_smart_chunks(audio: AudioSegment, max_duration_ms: int) -> List[AudioSegment]:
    """
    Create audio chunks with smart splitting at silence boundaries.
    
    Args:
        audio: AudioSegment to split
        max_duration_ms: Maximum duration per chunk in milliseconds
    
    Returns:
        List of audio chunks
    """
    if len(audio) <= max_duration_ms:
        return [audio]
    
    chunks = []
    overlap_ms = config.transcription.chunk_overlap_seconds * 1000
    
    # Try to find silence boundaries for splitting
    try:
        # Detect silence (you might want to adjust these parameters)
        silence_thresh = audio.dBFS - 16  # 16dB below average
        min_silence_len = 500  # 500ms minimum silence
        
        # Simple chunking with overlap for now
        # In a more advanced version, you'd use silence detection
        start = 0
        while start < len(audio):
            end = min(start + max_duration_ms, len(audio))
            
            # Add overlap except for the first chunk
            chunk_start = max(0, start - overlap_ms) if start > 0 else start
            chunk = audio[chunk_start:end]
            
            chunks.append(chunk)
            start = end - overlap_ms
    
    except Exception as e:
        logger.warning(f"Smart chunking failed, using simple chunking: {e}")
        # Fallback to simple chunking
        chunks = []
        for i in range(0, len(audio), max_duration_ms):
            chunks.append(audio[i:i + max_duration_ms])
    
    logger.info(f"Created {len(chunks)} chunks from audio")
    return chunks

@retry_with_exponential_backoff(max_retries=3)
def transcribe_chunk(
    client: OpenAI,
    chunk: AudioSegment,
    chunk_index: int,
    total_chunks: int,
    model: str,
    language: Optional[str],
    context_prompt: str
) -> str:
    """
    Transcribe a single audio chunk with retry logic.
    
    Args:
        client: OpenAI client
        chunk: AudioSegment to transcribe
        chunk_index: Index of current chunk (0-based)
        total_chunks: Total number of chunks
        model: Model to use for transcription
        language: Language code (None for auto-detection)
        context_prompt: Context prompt for transcription
    
    Returns:
        Transcribed text
    """
    # Export chunk to bytes
    chunk_bytes_io = BytesIO()
    chunk.export(chunk_bytes_io, format="mp3")
    chunk_bytes_io.seek(0)
    
    # Create transcription
    response = client.audio.transcriptions.create(
        model=model,
        file=(f"chunk_{chunk_index + 1}.mp3", chunk_bytes_io),
        response_format="text",
        language=language if language != "auto" else None,
        prompt=context_prompt
    )
    
    transcribed_text = str(response) if response else ""
    logger.info(f"Transcribed chunk {chunk_index + 1}/{total_chunks}: {len(transcribed_text)} characters")
    
    return transcribed_text

def create_progress_bar(total_chunks: int) -> Tuple[any, any]:
    """
    Create progress bar components for Streamlit.
    
    Args:
        total_chunks: Total number of chunks to process
    
    Returns:
        Tuple of (progress_bar, status_text)
    """
    progress_bar = st.progress(0)
    status_text = st.empty()
    return progress_bar, status_text

def update_progress(
    progress_bar,
    status_text,
    current: int,
    total: int,
    message: str = ""
):
    """
    Update progress bar and status text.
    
    Args:
        progress_bar: Streamlit progress bar
        status_text: Streamlit text element
        current: Current progress value
        total: Total progress value
        message: Optional status message
    """
    progress = current / total if total > 0 else 0
    progress_bar.progress(progress)
    
    if message:
        status_text.text(f"{message} ({current}/{total})")
    else:
        status_text.text(f"Processing: {current}/{total}")

def export_transcript(transcript: str, format: str = "txt") -> bytes:
    """
    Export transcript in various formats.
    
    Args:
        transcript: Transcript text
        format: Export format ("txt", "md", etc.)
    
    Returns:
        Exported content as bytes
    """
    if format == "txt":
        return transcript.encode('utf-8')
    elif format == "md":
        formatted = f"# Transcript\n\n{transcript}"
        return formatted.encode('utf-8')
    else:
        raise ValueError(f"Unsupported export format: {format}")

def estimate_processing_time(audio_duration_seconds: float) -> str:
    """
    Estimate processing time based on audio duration.
    
    Args:
        audio_duration_seconds: Duration of audio in seconds
    
    Returns:
        Estimated time as a formatted string
    """
    # Rough estimates based on typical processing times
    # These are very rough estimates and can vary significantly
    base_time = audio_duration_seconds * 0.1  # ~10% of audio duration
    chunk_overhead = (audio_duration_seconds / config.transcription.max_duration_seconds) * 5  # 5s per chunk
    
    total_seconds = max(10, base_time + chunk_overhead)  # Minimum 10 seconds
    
    if total_seconds < 60:
        return f"~{int(total_seconds)} seconds"
    else:
        minutes = int(total_seconds / 60)
        return f"~{minutes} minute{'s' if minutes != 1 else ''}" 
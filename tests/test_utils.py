"""
Unit tests for utility functions.
"""
import pytest
from unittest.mock import Mock, patch
from io import BytesIO

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import validate_audio_file, estimate_processing_time, export_transcript

class TestValidateAudioFile:
    """Test audio file validation."""
    
    def test_validate_none_file(self):
        """Test validation with None file."""
        is_valid, error = validate_audio_file(None)
        assert not is_valid
        assert error == "No file uploaded"
    
    def test_validate_file_too_large(self):
        """Test validation with oversized file."""
        mock_file = Mock()
        mock_file.getvalue.return_value = b"x" * (30 * 1024 * 1024)  # 30MB
        mock_file.name = "test.mp3"
        
        is_valid, error = validate_audio_file(mock_file)
        assert not is_valid
        assert "exceeds limit" in error
    
    def test_validate_unsupported_format(self):
        """Test validation with unsupported format."""
        mock_file = Mock()
        mock_file.getvalue.return_value = b"test data"
        mock_file.name = "test.xyz"
        
        is_valid, error = validate_audio_file(mock_file)
        assert not is_valid
        assert "Unsupported file format" in error
    
    def test_validate_valid_file(self):
        """Test validation with valid file."""
        mock_file = Mock()
        mock_file.getvalue.return_value = b"test data"
        mock_file.name = "test.mp3"
        
        is_valid, error = validate_audio_file(mock_file)
        assert is_valid
        assert error is None

class TestEstimateProcessingTime:
    """Test processing time estimation."""
    
    def test_short_audio(self):
        """Test estimation for short audio."""
        result = estimate_processing_time(30)  # 30 seconds
        assert "second" in result
    
    def test_long_audio(self):
        """Test estimation for long audio."""
        result = estimate_processing_time(1800)  # 30 minutes
        assert "minute" in result

class TestExportTranscript:
    """Test transcript export functionality."""
    
    def test_export_txt(self):
        """Test exporting as text."""
        transcript = "Hello world"
        result = export_transcript(transcript, "txt")
        assert result == b"Hello world"
    
    def test_export_md(self):
        """Test exporting as markdown."""
        transcript = "Hello world"
        result = export_transcript(transcript, "md")
        assert b"# Transcript" in result
        assert b"Hello world" in result
    
    def test_export_unsupported_format(self):
        """Test exporting with unsupported format."""
        with pytest.raises(ValueError):
            export_transcript("test", "pdf")

if __name__ == "__main__":
    pytest.main([__file__]) 
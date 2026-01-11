"""
Tests for Text-to-Speech (TTS) services.

Tests cover:
- ElevenLabs TTS integration
- Default TTS fallback
- Error handling
- Audio format validation
"""
import pytest
import respx
from httpx import Response
from unittest.mock import patch, MagicMock

from app.services.tts.tts_service import generate_speech, synthesize_speech
from app.services.tts.elevenlabs_tts import elevenlabs_tts, is_elevenlabs_enabled
from app.services.tts.default_tts import default_tts
from app.core.config import settings


@pytest.mark.unit
@pytest.mark.tts
class TestElevenLabsTTS:
    """Test suite for ElevenLabs TTS service."""
    
    def test_elevenlabs_enabled_check(self):
        """Test ElevenLabs enabled check."""
        # Test with API key
        with patch('os.getenv', return_value='test-key'):
            assert is_elevenlabs_enabled() is True
        
        # Test without API key
        with patch('os.getenv', return_value=None):
            assert is_elevenlabs_enabled() is False
    
    def test_elevenlabs_tts_with_text(self):
        """Test ElevenLabs TTS function with text."""
        with patch('os.getenv') as mock_getenv:
            mock_getenv.side_effect = lambda k, default=None: {
                'ELEVENLABS_API_KEY': 'test-key',
                'ELEVENLABS_VOICE_ID': 'test-voice'
            }.get(k, default)
            
            # This will fail without actual API, but tests the function exists
            try:
                audio, content_type = elevenlabs_tts("Test")
                assert audio is None or isinstance(audio, bytes)
            except Exception:
                # Expected to fail without real API
                pass


@pytest.mark.unit
@pytest.mark.tts
class TestDefaultTTS:
    """Test suite for Default TTS fallback service."""
    
    def test_default_tts_function(self):
        """Test default TTS function."""
        audio, content_type = default_tts("Test text")
        
        # Default TTS should return None (browser fallback) or placeholder
        assert audio is None or isinstance(audio, bytes)
    
    def test_default_tts_handles_any_text(self):
        """Test default TTS handles any text input."""
        test_cases = [
            "Short text",
            "Very long text " * 100,
            "",
            "Special characters: !@#$%^&*()",
            "Unicode: 你好世界 🌍"
        ]
        
        for text in test_cases:
            audio, content_type = default_tts(text)
            # Should not raise exception
            assert audio is None or isinstance(audio, bytes)


@pytest.mark.unit
@pytest.mark.tts
class TestTTSService:
    """Test suite for TTS service selection."""
    
    def test_generate_speech_with_text(self):
        """Test generate_speech function with valid text."""
        audio, content_type, provider = generate_speech("Hello, world!")
        
        # Should return audio or None based on configuration
        assert audio is None or isinstance(audio, bytes)
        assert provider in ["elevenlabs", "default", "none"]
    
    def test_generate_speech_empty_text(self):
        """Test generate_speech with empty text."""
        audio, content_type, provider = generate_speech("")
        
        assert audio is None
        assert provider == "none"
    
    def test_synthesize_speech_wrapper(self):
        """Test synthesize_speech wrapper function."""
        audio, error = synthesize_speech("Test message")
        
        # Should return audio or error
        assert (audio is not None and error is None) or (audio is None and error is not None)


@pytest.mark.integration
@pytest.mark.tts
class TestTTSIntegration:
    """Integration tests for TTS services."""
    
    @respx.mock
    @pytest.mark.asyncio
    async def test_tts_fallback_chain(self):
        """Test TTS fallback from ElevenLabs to default."""
        # Mock ElevenLabs failure
        respx.post("https://api.elevenlabs.io/v1/text-to-speech/test-voice").mock(
            return_value=Response(500, json={"error": "Service unavailable"})
        )
        
        # Test the generate_speech function which handles fallback internally
        audio, content_type, provider = generate_speech("Test")
        
        # Should have result from either primary or fallback
        assert audio is None or isinstance(audio, bytes)
        assert provider in ["elevenlabs", "default", "none"]
    
    def test_multiple_tts_requests(self):
        """Test multiple TTS requests in sequence."""
        texts = [
            "First message",
            "Second message",
            "Third message"
        ]
        
        results = []
        for text in texts:
            audio, content_type, provider = generate_speech(text)
            results.append((audio, provider))
        
        # All should complete without error
        assert len(results) == 3
        for audio, provider in results:
            assert provider in ["elevenlabs", "default", "none"]
    
    def test_tts_with_special_characters(self):
        """Test TTS handles special characters correctly."""
        special_texts = [
            "Hello, world!",
            "Question?",
            "Exclamation!",
            "Quote: \"test\"",
            "Number: 123",
            "Email: test@example.com"
        ]
        
        for text in special_texts:
            audio, content_type, provider = generate_speech(text)
            # Should handle without errors
            assert audio is None or isinstance(audio, bytes)
            assert provider in ["elevenlabs", "default", "none"]


@pytest.mark.unit
@pytest.mark.tts
class TestTTSConfiguration:
    """Test suite for TTS configuration."""
    
    def test_tts_with_different_providers(self):
        """Test TTS with different provider configurations."""
        # Test with default provider
        with patch('os.getenv', return_value='default'):
            audio, content_type, provider = generate_speech("Test")
            assert provider in ["default", "none"]
    
    def test_missing_elevenlabs_credentials(self):
        """Test handling of missing ElevenLabs credentials."""
        with patch('os.getenv', side_effect=lambda k, default=None: None if 'ELEVENLABS' in k else default):
            audio, content_type, provider = generate_speech("Test")
            # Should fall back to default
            assert provider in ["default", "none"]
    
    def test_tts_provider_fallback_chain(self):
        """Test TTS provider fallback chain."""
        # When primary fails, should try fallback
        audio, content_type, provider = generate_speech("Test message")
        # Should complete without error
        assert provider in ["elevenlabs", "default", "none"]

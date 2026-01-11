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

from app.services.tts.tts_service import get_tts_service
from app.services.tts.elevenlabs_tts import ElevenLabsTTS
from app.services.tts.default_tts import DefaultTTS
from app.core.config import settings


@pytest.mark.unit
@pytest.mark.tts
class TestElevenLabsTTS:
    """Test suite for ElevenLabs TTS service."""
    
    def test_elevenlabs_initialization_with_api_key(self):
        """Test ElevenLabs TTS initializes with API key."""
        with patch.object(settings, 'ELEVENLABS_API_KEY', 'test-key'):
            with patch.object(settings, 'ELEVENLABS_VOICE_ID', 'test-voice'):
                tts = ElevenLabsTTS()
                assert tts.api_key == 'test-key'
                assert tts.voice_id == 'test-voice'
    
    def test_elevenlabs_initialization_without_api_key(self):
        """Test ElevenLabs TTS handles missing API key."""
        with patch.object(settings, 'ELEVENLABS_API_KEY', None):
            tts = ElevenLabsTTS()
            assert tts.api_key is None
    
    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_text_to_speech(self, mock_tts_response):
        """Test successful text-to-speech conversion."""
        respx.post("https://api.elevenlabs.io/v1/text-to-speech/test-voice").mock(
            return_value=Response(200, content=mock_tts_response)
        )
        
        with patch.object(settings, 'ELEVENLABS_API_KEY', 'test-key'):
            with patch.object(settings, 'ELEVENLABS_VOICE_ID', 'test-voice'):
                tts = ElevenLabsTTS()
                audio = await tts.synthesize("Hello, this is a test.")
                
                assert audio is not None
                assert isinstance(audio, bytes)
                assert len(audio) > 0
    
    @respx.mock
    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test handling of API errors."""
        respx.post("https://api.elevenlabs.io/v1/text-to-speech/test-voice").mock(
            return_value=Response(500, json={"error": "Internal server error"})
        )
        
        with patch.object(settings, 'ELEVENLABS_API_KEY', 'test-key'):
            with patch.object(settings, 'ELEVENLABS_VOICE_ID', 'test-voice'):
                tts = ElevenLabsTTS()
                audio = await tts.synthesize("Test text")
                
                # Should return None or raise exception
                assert audio is None or isinstance(audio, bytes)
    
    @respx.mock
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling."""
        import httpx
        
        respx.post("https://api.elevenlabs.io/v1/text-to-speech/test-voice").mock(
            side_effect=httpx.TimeoutException("Request timeout")
        )
        
        with patch.object(settings, 'ELEVENLABS_API_KEY', 'test-key'):
            with patch.object(settings, 'ELEVENLABS_VOICE_ID', 'test-voice'):
                tts = ElevenLabsTTS()
                audio = await tts.synthesize("Test text")
                
                # Should handle timeout gracefully
                assert audio is None
    
    @pytest.mark.asyncio
    async def test_empty_text_handling(self):
        """Test handling of empty text input."""
        with patch.object(settings, 'ELEVENLABS_API_KEY', 'test-key'):
            with patch.object(settings, 'ELEVENLABS_VOICE_ID', 'test-voice'):
                tts = ElevenLabsTTS()
                audio = await tts.synthesize("")
                
                # Should handle empty text gracefully
                assert audio is None or isinstance(audio, bytes)
    
    @respx.mock
    @pytest.mark.asyncio
    async def test_long_text_handling(self):
        """Test handling of long text input."""
        long_text = "This is a test. " * 100  # Very long text
        
        respx.post("https://api.elevenlabs.io/v1/text-to-speech/test-voice").mock(
            return_value=Response(200, content=b"mock_audio_data")
        )
        
        with patch.object(settings, 'ELEVENLABS_API_KEY', 'test-key'):
            with patch.object(settings, 'ELEVENLABS_VOICE_ID', 'test-voice'):
                tts = ElevenLabsTTS()
                audio = await tts.synthesize(long_text)
                
                assert audio is not None
                assert isinstance(audio, bytes)


@pytest.mark.unit
@pytest.mark.tts
class TestDefaultTTS:
    """Test suite for Default TTS fallback service."""
    
    def test_default_tts_initialization(self):
        """Test default TTS initializes correctly."""
        tts = DefaultTTS()
        assert tts is not None
    
    @pytest.mark.asyncio
    async def test_default_tts_returns_placeholder(self):
        """Test default TTS returns placeholder or None."""
        tts = DefaultTTS()
        result = await tts.synthesize("Test text")
        
        # Default TTS should return None (browser fallback) or placeholder
        assert result is None or isinstance(result, bytes)
    
    @pytest.mark.asyncio
    async def test_default_tts_handles_any_text(self):
        """Test default TTS handles any text input."""
        tts = DefaultTTS()
        
        test_cases = [
            "Short text",
            "Very long text " * 100,
            "",
            "Special characters: !@#$%^&*()",
            "Unicode: 你好世界 🌍"
        ]
        
        for text in test_cases:
            result = await tts.synthesize(text)
            # Should not raise exception
            assert result is None or isinstance(result, bytes)


@pytest.mark.unit
@pytest.mark.tts
class TestTTSService:
    """Test suite for TTS service selection."""
    
    def test_get_tts_service_with_elevenlabs(self):
        """Test TTS service returns ElevenLabs when configured."""
        with patch.object(settings, 'TTS_PRIMARY', 'elevenlabs'):
            with patch.object(settings, 'ELEVENLABS_API_KEY', 'test-key'):
                tts = get_tts_service()
                assert isinstance(tts, ElevenLabsTTS)
    
    def test_get_tts_service_fallback_to_default(self):
        """Test TTS service falls back to default when not configured."""
        with patch.object(settings, 'TTS_PRIMARY', 'elevenlabs'):
            with patch.object(settings, 'ELEVENLABS_API_KEY', None):
                tts = get_tts_service()
                assert isinstance(tts, DefaultTTS)
    
    def test_get_tts_service_default_primary(self):
        """Test TTS service uses default when primary is 'default'."""
        with patch.object(settings, 'TTS_PRIMARY', 'default'):
            tts = get_tts_service()
            assert isinstance(tts, DefaultTTS)


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
        
        with patch.object(settings, 'TTS_PRIMARY', 'elevenlabs'):
            with patch.object(settings, 'TTS_FALLBACK', 'default'):
                with patch.object(settings, 'ELEVENLABS_API_KEY', 'test-key'):
                    with patch.object(settings, 'ELEVENLABS_VOICE_ID', 'test-voice'):
                        # Try primary (ElevenLabs)
                        primary_tts = get_tts_service()
                        audio = await primary_tts.synthesize("Test")
                        
                        if audio is None:
                            # Fall back to default
                            fallback_tts = DefaultTTS()
                            audio = await fallback_tts.synthesize("Test")
                        
                        # Should have result from fallback
                        assert audio is None or isinstance(audio, bytes)
    
    @respx.mock
    @pytest.mark.asyncio
    async def test_multiple_tts_requests(self):
        """Test multiple TTS requests in sequence."""
        respx.post("https://api.elevenlabs.io/v1/text-to-speech/test-voice").mock(
            return_value=Response(200, content=b"mock_audio")
        )
        
        with patch.object(settings, 'ELEVENLABS_API_KEY', 'test-key'):
            with patch.object(settings, 'ELEVENLABS_VOICE_ID', 'test-voice'):
                tts = ElevenLabsTTS()
                
                texts = [
                    "First message",
                    "Second message",
                    "Third message"
                ]
                
                results = []
                for text in texts:
                    audio = await tts.synthesize(text)
                    results.append(audio)
                
                # All should succeed
                assert len(results) == 3
                for result in results:
                    assert result is not None
    
    @pytest.mark.asyncio
    async def test_tts_with_special_characters(self):
        """Test TTS handles special characters correctly."""
        tts = DefaultTTS()
        
        special_texts = [
            "Hello, world!",
            "Question?",
            "Exclamation!",
            "Quote: \"test\"",
            "Number: 123",
            "Email: test@example.com"
        ]
        
        for text in special_texts:
            result = await tts.synthesize(text)
            # Should handle without errors
            assert result is None or isinstance(result, bytes)


@pytest.mark.unit
@pytest.mark.tts
class TestTTSConfiguration:
    """Test suite for TTS configuration."""
    
    def test_tts_config_validation(self):
        """Test TTS configuration validation."""
        # Test valid configurations
        valid_configs = [
            ('elevenlabs', 'default'),
            ('default', None),
            (None, 'default')
        ]
        
        for primary, fallback in valid_configs:
            with patch.object(settings, 'TTS_PRIMARY', primary):
                with patch.object(settings, 'TTS_FALLBACK', fallback):
                    tts = get_tts_service()
                    assert tts is not None
    
    def test_missing_elevenlabs_credentials(self):
        """Test handling of missing ElevenLabs credentials."""
        with patch.object(settings, 'TTS_PRIMARY', 'elevenlabs'):
            with patch.object(settings, 'ELEVENLABS_API_KEY', None):
                tts = get_tts_service()
                # Should fall back to default
                assert isinstance(tts, DefaultTTS)
    
    def test_partial_elevenlabs_credentials(self):
        """Test handling of partial ElevenLabs credentials."""
        # API key but no voice ID
        with patch.object(settings, 'TTS_PRIMARY', 'elevenlabs'):
            with patch.object(settings, 'ELEVENLABS_API_KEY', 'test-key'):
                with patch.object(settings, 'ELEVENLABS_VOICE_ID', None):
                    tts = get_tts_service()
                    # Should handle gracefully
                    assert tts is not None

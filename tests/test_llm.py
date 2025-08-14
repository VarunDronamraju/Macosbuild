import pytest
from backend.llm import OllamaClient, WebSearchClient, RAGService

class TestOllamaClient:
    def test_is_available(self):
        client = OllamaClient()
        # This will fail if Ollama is not running - that's expected
        availability = client.is_available()
        assert isinstance(availability, bool)
    
    def test_generate_response_error_handling(self):
        client = OllamaClient()
        client.base_url = "http://invalid-url:1234"  # Force error
        
        responses = list(client.generate_response("test prompt", stream=False))
        assert len(responses) > 0
        assert "Error" in responses[0]

class TestWebSearchClient:
    def test_is_available_without_api_key(self):
        # Test without API key
        import os
        old_key = os.environ.get('TAVILY_API_KEY')
        if 'TAVILY_API_KEY' in os.environ:
            del os.environ['TAVILY_API_KEY']
        
        client = WebSearchClient()
        assert not client.is_available()
        
        # Restore key if it existed
        if old_key:
            os.environ['TAVILY_API_KEY'] = old_key

class TestRAGService:
    def test_create_prompt(self):
        service = RAGService()
        
        context = "This is test context about machine learning."
        query = "What is machine learning?"
        
        prompt = service.create_prompt(context, query)
        
        assert context in prompt
        assert query in prompt
        assert "Answer:" in prompt
    
    def test_get_service_status(self):
        service = RAGService()
        status = service.get_service_status()
        
        assert "ollama" in status
        assert "web_search" in status
        assert "vector_store" in status
        assert isinstance(status["vector_store"], bool)
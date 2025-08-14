import json
import requests
from typing import Iterator, Dict, Any, Optional
from tavily import TavilyClient
from .config import settings
from .rag import RAGPipeline

class OllamaClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_URL
        self.model = settings.LLM_MODEL
    
    def generate_response(self, prompt: str, stream: bool = True) -> Iterator[str]:
        """Generate response using Ollama"""
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream
        }
        
        try:
            response = requests.post(url, json=payload, stream=stream)
            response.raise_for_status()
            
            if stream:
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line.decode('utf-8'))
                        if 'response' in data:
                            yield data['response']
                        if data.get('done', False):
                            break
            else:
                data = response.json()
                yield data.get('response', '')
                
        except Exception as e:
            yield f"Error generating response: {str(e)}"
    
    def is_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

class WebSearchClient:
    def __init__(self):
        self.tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY) if settings.TAVILY_API_KEY else None
    
    def search(self, query: str, max_results: int = 3) -> str:
        """Search web for additional context"""
        if not self.tavily_client:
            return ""
        
        try:
            response = self.tavily_client.search(
                query=query,
                search_depth="basic",
                max_results=max_results
            )
            
            web_context = []
            for result in response.get('results', []):
                web_context.append(f"Source: {result.get('title', 'Unknown')}\n{result.get('content', '')}")
            
            return "\n\n".join(web_context)
            
        except Exception as e:
            print(f"Web search error: {str(e)}")
            return ""
    
    def is_available(self) -> bool:
        """Check if web search is available"""
        return self.tavily_client is not None

class RAGService:
    def __init__(self):
        self.rag_pipeline = RAGPipeline()
        self.ollama_client = OllamaClient()
        self.web_client = WebSearchClient()
    
    def create_prompt(self, context: str, query: str, has_web_context: bool = False) -> str:
        """Create prompt for LLM"""
        if context.strip():
            base_prompt = f"""You are a helpful AI assistant. Answer the user's question based on the provided context from the user's documents.

Context from Documents:
{context}

Question: {query}

Instructions:
- Provide a clear, accurate answer based primarily on the context from the user's documents
- If the context contains relevant information, use it to answer the question
- Be specific and cite relevant parts of the context when possible
- If the context doesn't contain enough information to fully answer the question, say so clearly
"""
        else:
            base_prompt = f"""You are a helpful AI assistant. The user has asked a question but no relevant documents were found in their personal collection.

Question: {query}

Instructions:
- Inform the user that no relevant documents were found in their collection
- Provide a general helpful response if possible
- Suggest they might want to upload relevant documents for better answers
"""
        
        if has_web_context:
            base_prompt += "\n- Some information comes from web search results - indicate this when relevant"
        
        base_prompt += "\n\nAnswer:"
        
        return base_prompt
    
    def query_documents(self, query: str, user_id: str, stream: bool = True) -> Iterator[str]:
        """Main RAG query function"""
        # Step 1: Retrieve context from user's documents
        context_data = self.rag_pipeline.retrieve_context(query, user_id)
        context = context_data["context"]
        has_context = context_data["has_context"]
        
        print(f"DEBUG RAG: Retrieved context: {len(context)} characters, has_context: {has_context}")
        print(f"DEBUG RAG: Number of sources: {len(context_data.get('sources', []))}")
        
        # Step 2: Check if we need web search fallback
        needs_web_search = not has_context or not self.rag_pipeline.assess_context_quality(context, query)
        
        print(f"DEBUG RAG: Needs web search: {needs_web_search}")
        
        web_context = ""
        if needs_web_search and self.web_client.is_available():
            print("DEBUG RAG: Using web search fallback")
            web_context = self.web_client.search(query)
            if web_context:
                context = f"{context}\n\n--- Web Search Results ---\n{web_context}" if context else web_context
        
        # Step 3: Generate response
        prompt = self.create_prompt(context, query, bool(web_context))
        
        print(f"DEBUG RAG: Final prompt length: {len(prompt)}")
        
        if not self.ollama_client.is_available():
            yield "Error: Local LLM is not available. Please ensure Ollama is running."
            return
        
        # Stream response from LLM
        for chunk in self.ollama_client.generate_response(prompt, stream):
            yield chunk
    
    def get_service_status(self) -> Dict[str, bool]:
        """Get status of all services"""
        return {
            "ollama": self.ollama_client.is_available(),
            "web_search": self.web_client.is_available(),
            "vector_store": True  # Assume Qdrant is available if we got this far
        }
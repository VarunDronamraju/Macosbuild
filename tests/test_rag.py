import pytest
import numpy as np
from backend.rag import VectorStore, RAGPipeline
from backend.database import create_tables

@pytest.fixture
def vector_store():
    return VectorStore()

@pytest.fixture
def test_user_id():
    return "test_user_123"

class TestVectorStore:
    def test_create_user_collection(self, vector_store, test_user_id):
        collection_name = vector_store.create_user_collection(test_user_id)
        assert "user_" in collection_name
        assert test_user_id.replace('-', '_') in collection_name
    
    def test_store_and_search_embedding(self, vector_store, test_user_id):
        # Create test embedding
        embedding = np.random.rand(384).astype(np.float32)
        metadata = {
            "document_id": "test_doc",
            "chunk_index": 0,
            "content": "Test content"
        }
        
        # Store embedding
        vector_store.store_embedding("test_point", embedding, metadata, test_user_id)
        
        # Search for similar embeddings
        results = vector_store.search_similar(embedding, test_user_id, top_k=1)
        
        assert len(results) == 1
        assert results[0]["id"] == "test_point"
        assert results[0]["metadata"]["document_id"] == "test_doc"

class TestRAGPipeline:
    def test_retrieve_context_no_documents(self):
        pipeline = RAGPipeline()
        result = pipeline.retrieve_context("test query", "nonexistent_user")
        assert not result["has_context"]
        assert result["context"] == ""
    
    def test_assess_context_quality(self):
        pipeline = RAGPipeline()
        
        # Good context
        good_context = "This document contains information about machine learning algorithms and their applications."
        assert pipeline.assess_context_quality(good_context, "machine learning")
        
        # Poor context
        poor_context = "Short."
        assert not pipeline.assess_context_quality(poor_context, "machine learning")
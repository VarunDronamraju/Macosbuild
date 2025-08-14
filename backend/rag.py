from typing import List, Dict, Optional, Any
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
from backend.config import settings
import uuid

class VectorStore:
    def __init__(self):
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None
        )
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.embedding_size = 384  # all-MiniLM-L6-v2 dimension
    
    def create_user_collection(self, user_id: str):
        """Create a collection for a specific user"""
        # CRITICAL FIX: Keep collection naming consistent
        collection_name = f"user_{user_id.replace('-', '_')}"
        print(f"DEBUG RAG: Creating/accessing collection: {collection_name}")
        
        try:
            self.client.get_collection(collection_name)
            print(f"DEBUG RAG: Collection {collection_name} exists")
        except:
            print(f"DEBUG RAG: Creating new collection {collection_name}")
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_size,
                    distance=Distance.COSINE
                )
            )
        
        return collection_name
    
    def store_embedding(self, point_id: str, embedding: np.ndarray, metadata: Dict, user_id: str):
        """Store embedding in user's collection"""
        collection_name = self.create_user_collection(user_id)
        
        print(f"DEBUG RAG: Storing embedding {point_id} in collection {collection_name}")
        print(f"DEBUG RAG: Metadata: {metadata}")
        
        point = PointStruct(
            id=point_id,
            vector=embedding.tolist(),
            payload=metadata
        )
        
        self.client.upsert(
            collection_name=collection_name,
            points=[point]
        )
        print(f"DEBUG RAG: Successfully stored embedding {point_id}")
    
    def search_similar(self, query_embedding: np.ndarray, user_id: str, top_k: int = 5, score_threshold: float = 0.0) -> List[Dict]:
        """Search for similar vectors"""
        collection_name = self.create_user_collection(user_id)
        
        print(f"DEBUG RAG: Searching in collection: {collection_name}")
        print(f"DEBUG RAG: Query embedding shape: {query_embedding.shape}")
        print(f"DEBUG RAG: Top-k: {top_k}, Score threshold: {score_threshold}")
        
        try:
            # Search without score threshold to see all results
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding.tolist(),
                limit=top_k
            )
            
            print(f"DEBUG RAG: Found {len(search_result)} total results")
            for i, hit in enumerate(search_result):
                print(f"DEBUG RAG: Result {i}: score={hit.score:.4f}, id={hit.id}")
                print(f"DEBUG RAG: Payload: {hit.payload}")
            
            # Filter by score threshold manually
            filtered_results = [hit for hit in search_result if hit.score >= score_threshold]
            print(f"DEBUG RAG: After filtering with threshold {score_threshold}: {len(filtered_results)} results")
            
            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "chunk_metadata": hit.payload
                }
                for hit in filtered_results
            ]
        except Exception as e:
            print(f"DEBUG RAG: Search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def delete_document_embeddings(self, document_id: str, user_id: str):
        """Delete all embeddings for a document"""
        collection_name = self.create_user_collection(user_id)
        
        print(f"DEBUG RAG: Deleting embeddings for document {document_id} from collection {collection_name}")
        
        self.client.delete(
            collection_name=collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            )
        )

class RAGPipeline:
    def __init__(self):
        self.vector_store = VectorStore()
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
    
    def retrieve_context(self, query: str, user_id: str, top_k: int = 5) -> Dict[str, Any]:
        """Retrieve relevant context for a query"""
        print(f"DEBUG RAG PIPELINE: Retrieving context for query: '{query}' and user: '{user_id}'")
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query])[0]
        print(f"DEBUG RAG PIPELINE: Generated query embedding shape: {query_embedding.shape}")
        
        # Search for similar chunks
        similar_chunks = self.vector_store.search_similar(
            query_embedding, user_id, top_k
        )
        
        print(f"DEBUG RAG PIPELINE: Found {len(similar_chunks)} similar chunks")
        
        if not similar_chunks:
            print("DEBUG RAG PIPELINE: No similar chunks found - returning empty context")
            return {
                "context": "",
                "sources": [],
                "has_context": False
            }
        
        # Get full chunk content from database
        from backend.database import SessionLocal, DocumentChunk, Document
        db = SessionLocal()
        
        try:
            context_parts = []
            sources = []
            
            for i, chunk_data in enumerate(similar_chunks):
                chunk_id = chunk_data["id"]
                print(f"DEBUG RAG PIPELINE: Processing chunk {i} with ID {chunk_id}")
                
                chunk = db.query(DocumentChunk).filter(
                    DocumentChunk.embedding_id == chunk_id
                ).first()
                
                if chunk:
                    print(f"DEBUG RAG PIPELINE: Found chunk in database")
                    context_parts.append(chunk.content)
                    
                    # Get document info for sources
                    document = db.query(Document).filter(Document.id == chunk.document_id).first()
                    
                    sources.append({
                        "document_id": str(chunk.document_id),
                        "document_name": document.filename if document else "Unknown Document",
                        "chunk_index": chunk.chunk_index,
                        "score": float(chunk_data["score"]),
                        "preview": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                        "source_type": "local_document"
                    })
                    print(f"DEBUG RAG PIPELINE: Added source: {document.filename if document else 'Unknown'}")
                else:
                    print(f"DEBUG RAG PIPELINE: Chunk {chunk_id} not found in database!")
            
            # Combine context with length limit
            full_context = "\n\n".join(context_parts)
            if len(full_context) > settings.MAX_CONTEXT_LENGTH:
                # Truncate to fit context window
                full_context = full_context[:settings.MAX_CONTEXT_LENGTH] + "..."
            
            print(f"DEBUG RAG PIPELINE: Final context length: {len(full_context)} characters")
            print(f"DEBUG RAG PIPELINE: Number of sources: {len(sources)}")
            
            return {
                "context": full_context,
                "sources": sources,
                "has_context": len(context_parts) > 0
            }
            
        finally:
            db.close()
    
    def assess_context_quality(self, context: str, query: str) -> bool:
        """Assess if context is sufficient for answering the query"""
        if len(context.strip()) < 50:
            print(f"DEBUG RAG PIPELINE: Context too short: {len(context)} characters")
            return False
        
        # Simple keyword overlap check
        query_words = set(query.lower().split())
        context_words = set(context.lower().split())
        overlap = len(query_words.intersection(context_words))
        
        required_overlap = max(1, len(query_words) * 0.3)
        quality_good = overlap >= required_overlap
        
        print(f"DEBUG RAG PIPELINE: Context quality check - overlap: {overlap}, required: {required_overlap}, good: {quality_good}")
        
        return quality_good
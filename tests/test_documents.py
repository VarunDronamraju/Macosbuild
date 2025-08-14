import pytest
import os
import tempfile
from pathlib import Path
from backend.documents import DocumentProcessor
from backend.database import create_tables, SessionLocal, User

@pytest.fixture
def sample_pdf():
    """Create a sample PDF for testing"""
    # You'll need to create actual test files
    return "tests/fixtures/sample.pdf"

@pytest.fixture
def sample_txt():
    """Create a sample TXT file for testing"""
    content = "This is a sample document for testing. It contains multiple sentences for chunking."
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(content)
        return f.name

@pytest.fixture
def test_user():
    """Create test user"""
    create_tables()
    db = SessionLocal()
    user = User(
        google_id="test_google_id",
        email="test@example.com",
        name="Test User"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield str(user.id)
    db.close()

class TestDocumentProcessor:
    def test_extract_txt_text(self, sample_txt):
        processor = DocumentProcessor()
        text = processor.extract_text(sample_txt, 'txt')
        assert "sample document" in text.lower()
        os.unlink(sample_txt)  # cleanup
    
    def test_chunk_text(self):
        processor = DocumentProcessor()
        text = "This is sentence one. This is sentence two. This is sentence three. " * 10
        chunks = processor.chunk_text(text, chunk_size=100, overlap=20)
        assert len(chunks) > 1
        assert len(chunks[0]) <= 120  # chunk_size + some tolerance for sentence boundaries
    
    def test_generate_embeddings(self):
        processor = DocumentProcessor()
        texts = ["This is a test sentence.", "This is another test sentence."]
        embeddings = processor.generate_embeddings(texts)
        assert embeddings.shape[0] == 2
        assert embeddings.shape[1] == 384  # all-MiniLM-L6-v2 dimension
    
    def test_process_document(self, sample_txt, test_user):
        processor = DocumentProcessor()
        try:
            document_id = processor.process_document(sample_txt, "test.txt", test_user)
            assert document_id is not None
        finally:
            os.unlink(sample_txt)
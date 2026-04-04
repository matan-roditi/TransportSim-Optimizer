import os
import sys
from unittest.mock import MagicMock, patch
from crew.rag_retriever import fetch_time_context

# Dynamically add the src directory to the path for testing
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(current_dir, "..", "src"))
if src_dir not in sys.path:
    sys.path.append(src_dir)


def test_fetch_time_context_returns_joined_documents():
    """Results from the vector DB are joined into a single space-separated string."""
    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "documents": [["Morning rush hour starts.", "High demand near train station."]]
    }
    with patch("crew.rag_retriever.chromadb.PersistentClient") as mock_client:
        mock_client.return_value.get_collection.return_value = mock_collection
        result = fetch_time_context("08:00")
    assert result == "Morning rush hour starts. High demand near train station."


def test_fetch_time_context_returns_empty_string_on_no_results():
    """An empty documents list causes the function to return an empty string."""
    mock_collection = MagicMock()
    mock_collection.query.return_value = {"documents": []}
    with patch("crew.rag_retriever.chromadb.PersistentClient") as mock_client:
        mock_client.return_value.get_collection.return_value = mock_collection
        result = fetch_time_context("08:00")
    assert result == ""

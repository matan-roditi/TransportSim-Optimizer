import os
import chromadb

# Setup absolute paths to ensure the database is found regardless of where the script runs
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
db_path = os.path.join(root_dir, "chroma_db")


def fetch_time_context(time_str: str) -> str:
    # Connect to the local vector database
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_collection(name="herzliya_context")

    # Formulate a search query based on the time
    search_query = f"What happens in Herzliya around {time_str}?"

    # Query the database for the top two most relevant patterns
    results = collection.query(
        query_texts=[search_query],
        n_results=2
    )

    # Extract the documents from the result payload and combine them into a single string
    if results and "documents" in results and results["documents"]:
        retrieved_facts = results["documents"][0]
        return " ".join(retrieved_facts)

    return ""

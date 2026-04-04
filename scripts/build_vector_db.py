import os
import chromadb

# Setup paths for data and database storage
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
data_file = os.path.join(root_dir, "data", "herzliya_facts.txt")
db_path = os.path.join(root_dir, "chroma_db")


def build_database():
    # Initialize the persistent Chroma client
    client = chromadb.PersistentClient(path=db_path)

    # Create or get the collection for our knowledge base
    collection = client.get_or_create_collection(name="herzliya_context")

    # Read the facts from the text file
    with open(data_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Filter out empty lines and strip whitespace
    facts = [line.strip() for line in lines if line.strip()]

    # Generate simple string IDs for each fact
    ids = [f"fact_{i}" for i in range(len(facts))]

    # Add the facts to the vector database
    collection.add(
        documents=facts,
        ids=ids
    )

    print(f"Successfully loaded {len(facts)} facts into ChromaDB at {db_path}")


if __name__ == "__main__":
    build_database()

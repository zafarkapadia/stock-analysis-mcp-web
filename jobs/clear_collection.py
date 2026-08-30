import chromadb

def reset_chroma_collection(db_path: str, collection_name: str, strategy: str = "clear_content"):
    """
    Manages the lifecycle reset of a ChromaDB collection based on a specified strategy.
    
    Parameters:
        db_path (str): Path to the persistent database directory.
        collection_name (str): Name of the target collection.
        strategy (str): 'clear_content' to delete rows but keep schema, 
                        'drop_collection' to delete the collection entirely.
    """
    # 1. Connect to the persistent database directory
    chroma_client = chromadb.PersistentClient(path=db_path)

    def _clear_collection_documents():
        """Deletes all rows/documents inside the collection, keeping it alive for immediate reuse."""
        try:
            collection = chroma_client.get_collection(name=collection_name)
            existing_data = collection.get()
            all_ids = existing_data.get("ids", [])

            if all_ids:
                collection.delete(ids=all_ids)
                print(f"🧹 Cleared {len(all_ids)} document(s) from collection '{collection_name}'.")
                print("The collection is now empty and ready for new data.")
            else:
                print(f"ℹ️ Collection '{collection_name}' is already empty.")
        except ValueError:
            print(f"❌ Collection '{collection_name}' does not exist.")

    def _delete_entire_collection():
        """Completely drops the collection from the database metadata."""
        try:
            chroma_client.delete_collection(name=collection_name)
            print(f"💥 Successfully deleted the entire collection '{collection_name}'.")
        except ValueError:
            print(f"❌ Collection '{collection_name}' does not exist to delete.")

    # Execute the requested reset strategy
    if strategy == "clear_content":
        _clear_collection_documents()
    elif strategy == "drop_collection":
        _delete_entire_collection()
    else:
        print(f"❌ Invalid strategy '{strategy}'. Use 'clear_content' or 'drop_collection'.")


# --- Example Usage ---
if __name__ == "__main__":
    DB_PATH = "../data/chroma_db_market_news"
    COLLECTION_NAME = "stock_news_sentiment"

    # Option A: Just empty the content out
    reset_chroma_collection(DB_PATH, COLLECTION_NAME, strategy="clear_content")

    # Option B: Drop the whole table entirely (uncomment to use)
    reset_chroma_collection(DB_PATH, COLLECTION_NAME, strategy="drop_collection")

import logging
import os
import time
import uuid
import chromadb
import requests
from typing import List
from dotenv import load_dotenv

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("../data/chroma_ingest.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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

def fetch_and_store_stock_news(
    tickers: List[str], 
    db_path: str = "../data/chroma_db_market_news", 
    collection_name: str = "stock_news_sentiment", 
    max_articles: int = 5,
    delay_seconds: int = 15
):
    """
    Loops through a list of tickers, fetches news sentiment data from Alpha Vantage,
    and stores the processed summaries into a local ChromaDB collection.
    
    Parameters:
        tickers (List[str]): List of stock ticker symbols (e.g., ['AAPL', 'MSFT']).
        db_path (str): File path for the persistent ChromaDB database.
        collection_name (str): Name of the ChromaDB collection.
        max_articles (int): Maximum number of top articles to fetch per ticker.
        delay_seconds (int): Pause duration between API requests to respect rate limits.
    """
    # Load environment variables and get API Key
    load_dotenv()
    api_key = os.environ.get('API_KEY')
    
    if not api_key:
        logger.error("API_KEY not found in environment or .env file.")
        return

    # 1. Initialize ChromaDB client and collection once
    logger.info(f"Connecting to ChromaDB at '{db_path}'...")
    chroma_client = chromadb.PersistentClient(path=db_path)
    collection = chroma_client.get_or_create_collection(name=collection_name)

    # 2. Iterate through each ticker in the provided list
    for idx, ticker in enumerate(tickers):
        ticker = ticker.strip().upper()
        logger.info(f"Processing [{idx + 1}/{len(tickers)}]: {ticker}")

        # Construct API URL
        url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&limit={max_articles}&sort=LATEST&apikey={api_key}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP Request failed for {ticker}: {e}")
            continue

        # Check for Alpha Vantage API note (rate limit message)
        if "Information" in data:
            logger.warning(f"API Notice received: {data['Information']}")
            
        # 3. Process and ingest the feed data for this ticker
        if "feed" in data and len(data["feed"]) > 0:
            documents_list = []
            metadatas_list = []
            ids_list = []

            for index, article in enumerate(data["feed"][:max_articles], start=1):
                title = article.get("title", "No Title Available")
                summary = article.get("summary", "No Summary Available")
                url_link = article.get("url", "")

                full_text_content = f"Title: {title}\nSummary: {summary}"

                documents_list.append(full_text_content)
                ids_list.append(f"stock_news_{uuid.uuid4().hex[:8]}")
                metadatas_list.append({
                    "source_url": url_link, 
                    "ticker": ticker, 
                    "article_index": index
                })

            # Write batch to ChromaDB
            collection.add(
                documents=documents_list, 
                metadatas=metadatas_list, 
                ids=ids_list
            )
            logger.info(f"Successfully wrote {len(documents_list)} articles for {ticker} to ChromaDB.")
        else:
            logger.warning(f"No news feed found or API limit hit for {ticker}.")

        # 4. Rate limit guard: skip delay on the very last ticker
        if idx < len(tickers) - 1:
            logger.info(f"Sleeping for {delay_seconds} seconds to respect API rate limits...")
            time.sleep(delay_seconds)

    logger.info("Multi-ticker news ingestion pipeline complete!")


# --- Example Usage ---
if __name__ == "__main__":

    DB_PATH = "../data/chroma_db_market_news"
    COLLECTION_NAME = "stock_news_sentiment"

    # Option A: Just empty the content out
    reset_chroma_collection(DB_PATH, COLLECTION_NAME, strategy="clear_content")
    # Your target list of prominent tickers
    target_tickers = ["GOOGL", "GOOG", "AMZN", "AAPL", "META", "MSFT", "NVDA", "TSLA"]
    
    # 15 seconds is optimal for most standard API keys to stay under limits [1]
    fetch_and_store_stock_news(tickers=target_tickers, max_articles=5, delay_seconds=5)

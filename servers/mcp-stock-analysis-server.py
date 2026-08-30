import logging
import sqlite3
import chromadb
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

# Import the official Model Context Protocol (MCP) Server components
from fastmcp import FastMCP

# Configure logging module uniformly
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Load variables from your local .env file
load_dotenv()

# =====================================================================
# INITIALIZE MCP SERVER
# =====================================================================
# FastMCP automatically parses docstrings and type hints into JSON schemas
mcp = FastMCP("Stock Analysis Tool Server")


# =====================================================================
# MCP TOOL 1: RSI Database Retriever
# =====================================================================
@mcp.tool()
def retrieve_stored_rsi(symbol: Optional[str] = None, db_name: str = "../data/trading_signals.db") -> List[Dict[str, Any]]:
    """
    Retrieves the latest saved Relative Strength Index (RSI) from the database.
    
    Use this tool when you need to check the current Relative Strength Index (RSI) data for market indicators.
    You can filter for a specific stock ticker symbol (e.g., 'AAPL', 'GOOGL') or leave it blank to pull the entire portfolio.
    """
    saved_signals = []
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        if symbol:
            cursor.execute("SELECT symbol, timestamp, rsi FROM signals WHERE symbol = ?", (symbol.strip().upper(),))
        else:
            cursor.execute("SELECT symbol, timestamp, rsi FROM signals")
        rows = cursor.fetchall()
        for row in rows:
            saved_signals.append({
                "symbol": row[0],
                "timestamp": row[1],
                "rsi": row[2]
            })
    except sqlite3.Error as db_error:
        logging.error(f"❌ Database Retrieval Failed: {str(db_error)}")
    finally:
        if 'conn' in locals():
            conn.close()
    return saved_signals


# =====================================================================
# MCP TOOL 2: ChromaDB News Context Retriever
# =====================================================================
@mcp.tool()
def get_stock_news(ticker: str) -> str:
    """
    Queries a local ChromaDB vector database for recent financial news articles related to a specific stock ticker.
    
    Use this tool when you need context, market news, sentiment data, or recent financial articles about a specific stock 
    (e.g., 'AMZN', 'AAPL', 'GOOGL') to evaluate company performance or quarterly revenue trends.
    """
    chroma_client = chromadb.PersistentClient(path="../data/chroma_db_market_news")
    collection = chroma_client.get_or_create_collection(name="stock_news_sentiment")
    search_query = f"{ticker} stock performance and market revenue"
    
    results = collection.query(query_texts=[search_query], n_results=3)
    news_for_the_day = ""
    
    if results["documents"] and len(results["documents"][0]) > 0:
        for i in range(len(results["documents"][0])):
            document = results["documents"][0][i]
            news_for_the_day += document + "\n\n"
            
    return news_for_the_day.strip()


# --- Start the MCP Server ---
if __name__ == "__main__":
    # Runs the server using standard input/output (stdio) streams
    # This matches the interface expected by host apps like Claude Desktop
    mcp.run()

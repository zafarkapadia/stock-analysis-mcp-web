import os
import logging
import asyncio
from typing import TypedDict, Annotated, Sequence
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
load_dotenv()

# --- LangGraph State Definition ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    ticker: str
    rsi_data: str
    sentiment_data: str

async def main():
    if not os.environ.get("OPENAI_API_KEY"):
        logging.error("❌ 'OPENAI_API_KEY' is missing.")
        return

    target_ticker = input("Enter stock ticker symbol (e.g., GOOG, AAPL): ").strip().upper()
    if not target_ticker:
        return

    # 1. Connect to MCP Server
    server_script_path = os.path.abspath("../servers/mcp-stock-analysis-server.py")
    config = {
        "market-analyzer": {
            "command": "python",
            "args": [server_script_path],
            "transport": "stdio"
        }
    }
    
    client = MultiServerMCPClient(config)
    mcp_tools = await client.get_tools()
    
    # Map tools for individual agent assignments
    rsi_tool = [t for t in mcp_tools if t.name == "retrieve_stored_rsi"]
    news_tool = [t for t in mcp_tools if t.name == "get_stock_news"]

    # 2. Define LLM Model
    llm = ChatOpenAI(model="gpt-4o", temperature=0) 

    # =====================================================================
    # AGENT 1: RSI Analyst Node
    # =====================================================================
    async def rsi_analyst_node(state: AgentState):
        logging.info("🤖 RSI Analyst Agent Active")
        llm_with_tools = llm.bind_tools(rsi_tool)
        
        prompt = (
            f"You are a Quantitative RSI Analyst. Use your 'retrieve_stored_rsi' tool "
            f"to look up the RSI data for {state['ticker']}. Explain if the stock "
            f"is overbought (RSI > 70), oversold (RSI < 30), or neutral."
        )
        
        # Simple execution loop to handle tool calling explicitly
        response = await llm_with_tools.ainvoke([SystemMessage(content=prompt)])
        
        # If agent decides to call the tool
        if response.tool_calls:
            tool_call = response.tool_calls[0]
            result = await rsi_tool[0].ainvoke(tool_call["args"])
            # Final synthesis with data
            analysis = await llm.ainvoke([
                SystemMessage(content="Synthesize this raw DB information for the strategist."),
                HumanMessage(content=f"Ticker: {state['ticker']}, Raw Data: {str(result)}")
            ])
            return {"rsi_data": analysis.content}
        
        return {"rsi_data": "No RSI data retrieved."}

    # =====================================================================
    # AGENT 2: Sentiment Analyst Node
    # =====================================================================
    async def sentiment_analyst_node(state: AgentState):
        logging.info("🤖 Sentiment Analyst Agent Active")
        llm_with_tools = llm.bind_tools(news_tool)
        
        prompt = (
            f"You are a Qualitative Sentiment Analyst. Use your 'get_stock_news' tool "
            f"to read local articles regarding {state['ticker']}. Extract recent financial sentiment "
            f"trends, risks, or key quarterly revenue takeaways."
        )
        
        response = await llm_with_tools.ainvoke([SystemMessage(content=prompt)])
        
        if response.tool_calls:
            tool_call = response.tool_calls[0]
            result = await news_tool[0].ainvoke(tool_call["args"])
            analysis = await llm.ainvoke([
                SystemMessage(content="Synthesize these news summaries for the strategist."),
                HumanMessage(content=f"Ticker: {state['ticker']}, Raw News: {str(result)}")
            ])
            return {"sentiment_data": analysis.content}
            
        return {"sentiment_data": "No news data retrieved."}

    # =====================================================================
    # AGENT 3: Portfolio Strategist Node (Orchestrator)
    # =====================================================================
    async def strategist_node(state: AgentState):
        logging.info("👑 Portfolio Strategist Synthesizing Final Report")
        
        prompt = (
            f"You are the Lead Portfolio Strategist. Review the analytical data gathered by your sub-agents "
            f"for ticker {state['ticker']} and engineer a final investment verdict.\n\n"
            f"--- QUANTITATIVE RSI ANALYSIS ---\n{state['rsi_data']}\n\n"
            f"--- QUALITATIVE NEWS SENTIMENT ---\n{state['sentiment_data']}\n\n"
            f"CRITICAL INSTRUCTIONS:\n"
            f"1. Before making a final recommendation, write a 'THOUGHT PROCESS' section analyzing any conflicts "
            f"   (e.g., What if RSI says Overbought, but News Sentiment is hyper-bullish?).\n"
            f"2. Weigh the technical indicator against the fundamental sentiment narratives explicitly.\n"
            f"3. Provide a risk mitigation summary.\n"
            f"4. Conclude with a clear, bolded final action statement: BUY, SELL, or HOLD."
        )
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        return {"messages": [response]}

    # =====================================================================
    # BUILD THE COMPOSABLE GRAPH
    # =====================================================================
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("RsiAnalyst", rsi_analyst_node)
    workflow.add_node("SentimentAnalyst", sentiment_analyst_node)
    workflow.add_node("Strategist", strategist_node)

    # Establish Parallel Execution Layout (Fork-Join pattern)
    workflow.add_edge(START, "RsiAnalyst")
    workflow.add_edge(START, "SentimentAnalyst")
    
    # Both sub-agents must finish before hitting the Strategist
    workflow.add_edge("RsiAnalyst", "Strategist")
    workflow.add_edge("SentimentAnalyst", "Strategist")
    workflow.add_edge("Strategist", END)

    # Compile Graph Runtime
    graph = workflow.compile()

    # Execute Runtime Flow
    initial_state = {
        "messages": [HumanMessage(content=f"Analyze {target_ticker}")],
        "ticker": target_ticker,
        "rsi_data": "",
        "sentiment_data": ""
    }
    
    final_output = await graph.ainvoke(initial_state)
    
    print("\n=== FINAL MULTI-AGENT VERDICT ===")
    print(final_output["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())

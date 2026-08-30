import React, { useState, useEffect } from 'react';

// Explicit whitelist of allowed stock symbols
const ALLOWED_TICKERS = ['AAPL', 'AMZN', 'GOOG', 'GOOGL', 'META', 'MSFT', 'NVDA', 'TSLA'] as const;
type AllowedTicker = typeof ALLOWED_TICKERS[number];

export default function App() {
  const [ticker, setTicker] = useState<string>('AAPL');
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [verdict, setVerdict] = useState<string>('');
  
  // 🌟 NEW STATE: History list initialized from browser local storage memory (filtered to allowed tickers)
  const [history, setHistory] = useState<string[]>(() => {
    const saved = localStorage.getItem('mcp_ticker_history');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          return parsed.filter(item => ALLOWED_TICKERS.includes(item as any));
        }
      } catch (e) {
        console.error("Failed to parse history", e);
      }
    }
    return ['AAPL', 'GOOG', 'MSFT', 'NVDA'];
  });

  // Sync history array changes to local storage automatically
  useEffect(() => {
    localStorage.setItem('mcp_ticker_history', JSON.stringify(history));
  }, [history]);

  const handleRunAnalysis = (targetTicker?: string) => {
    const cleanTicker = (targetTicker || ticker).trim().toUpperCase();
    
    // Safety check enforcing whitelist values explicitly
    if (!ALLOWED_TICKERS.includes(cleanTicker as any)) {
      alert("Selected ticker symbol is unauthorized.");
      return;
    }

    // Update form input view if selected via sidebar click trigger
    if (targetTicker) {
      setTicker(cleanTicker);
    }

    setLoading(true);
    setLogs(["⏳ Request dispatched to broker..."]);
    setVerdict('');

    const eventSource = new EventSource(`http://localhost:8000/api/analyze?ticker=${cleanTicker}`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const payload = data.log;

        if (payload.startsWith('__FINAL_REPORT__:')) {
          const reportContent = payload.replace('__FINAL_REPORT__:', '');
          setVerdict(reportContent);
          
          // 🌟 HISTORICAL LOGGER: Append successfully run items uniquely to top of history view
          setHistory((prev) => {
            const filtered = prev.filter(item => item !== cleanTicker);
            return [cleanTicker, ...filtered].slice(0, 10); // Keep top 10 lookups maximum
          });

          eventSource.close();
          setLoading(false);
        } else {
          setLogs((prev) => [...prev, payload]);
        }
      } catch (err) {
        console.error("Stream parse error:", err);
      }
    };

    eventSource.onerror = (err) => {
      console.error("Stream disrupted endpoint info:", err);
      setLogs((prev) => [...prev, "❌ Endpoint disconnected. Verify python backend_api.py is listening on port 8000."]);
      eventSource.close();
      setLoading(false);
    };
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleRunAnalysis();
  };

  const clearHistory = () => {
    setHistory([]);
  };

  const renderFormattedReport = (text: string) => {
    if (!text) return null;
    const lines = text.split('\n');

    return lines.map((line, index) => {
      const isVerdictLine = /final\s*action/i.test(line);

      if (isVerdictLine) {
        const cleanLine = line.replace(/[\*#_`]/g, '').trim();
        const isBuy = /BUY/i.test(cleanLine);
        const isHold = /HOLD/i.test(cleanLine);

        return (
          <div 
            key={index} 
            style={{ 
              margin: '16px 0',
              padding: '14px', 
              borderRadius: '6px',
              backgroundColor: isBuy ? '#f0fdf4' : isHold ? '#fffbeb' : '#fef2f2',
              border: `2px solid ${isBuy ? '#22c55e' : isHold ? '#eab308' : '#ef4444'}`,
              display: 'inline-block'
            }}
          >
            <span style={{ fontWeight: 'bold', fontSize: '20px', color: isBuy ? '#16a34a' : isHold ? '#ca8a04' : '#dc2626' }}>
              🎯 {cleanLine}
            </span>
          </div>
        );
      }
      return <div key={index} style={{ marginBottom: '6px' }}>{line}</div>;
    });
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'system-ui, sans-serif', backgroundColor: '#f1f5f9' }}>
      
      {/* 🌟 NEW SIDEBAR CONTAINER */}
      <aside style={{ width: '240px', backgroundColor: '#1e293b', color: '#f8fafc', padding: '24px 16px', display: 'flex', flexDirection: 'column', borderRight: '1px solid #334155' }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          🔍 Recent Lookups
        </h3>
        
        <div style={{ flexGrow: 1, display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto' }}>
          {history.length === 0 ? (
            <span style={{ color: '#64748b', fontSize: '14px', fontStyle: 'italic' }}>No history logged yet.</span>
          ) : (
            history.map((histTicker) => (
              <button
                key={histTicker}
                onClick={() => !loading && handleRunAnalysis(histTicker)}
                disabled={loading}
                style={{
                  textAlign: 'left',
                  padding: '10px 14px',
                  backgroundColor: ticker === histTicker ? '#334155' : 'transparent',
                  color: ticker === histTicker ? '#38bdf8' : '#cbd5e1',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  fontSize: '15px',
                  fontWeight: '600',
                  transition: 'background-color 0.2s',
                  display: 'flex',
                  justifyContent: 'between'
                }}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#334155')}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = ticker === histTicker ? '#334155' : 'transparent')}
              >
                📈 {histTicker}
              </button>
            ))
          )}
        </div>

        {history.length > 0 && (
          <button 
            onClick={clearHistory}
            style={{ marginTop: 'auto', background: 'transparent', color: '#ef4444', border: '1px solid #7f1d1d', padding: '8px', borderRadius: '4px', cursor: 'pointer', fontSize: '13px' }}
          >
            Clear History
          </button>
        )}
      </aside>

      {/* MAIN MAIN VIEWBOARD WORKSPACE */}
      <main style={{ flexGrow: 1, padding: '40px', maxWidth: '1000px' }}>
        <h2 style={{ color: '#0f172a', margin: '0 0 4px 0' }}>📊 Multi-Agent Market Intelligence Board</h2>
        <p style={{ color: '#64748b', marginTop: '0', marginBottom: '24px' }}>FastMCP + LangGraph Agent Pipeline Workspace Panel</p>

        <form onSubmit={handleFormSubmit} style={{ display: 'flex', gap: '12px', marginBottom: '24px' }}>
          {/* Switched from text type input component to select configuration drop layer */}
          <select
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            disabled={loading}
            style={{ padding: '12px', fontSize: '15px', borderRadius: '6px', border: '1px solid #cbd5e1', width: '220px', backgroundColor: '#ffffff', color: '#0f172a' }}
          >
            {ALLOWED_TICKERS.map((allowedSymbol) => (
              <option key={allowedSymbol} value={allowedSymbol}>
                {allowedSymbol}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={loading}
            style={{
              padding: '12px 24px',
              fontSize: '15px',
              backgroundColor: loading ? '#94a3b8' : '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontWeight: '600'
            }}
          >
            {loading ? 'Running Analysis...' : 'Analyse Ticker'}
          </button>
        </form>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div>
            <h4 style={{ margin: '0 0 8px 0', color: '#475569' }}>Terminal Stream (Agent Activity)</h4>
            <div style={{ backgroundColor: '#0f172a', color: '#38bdf8', padding: '16px', borderRadius: '8px', height: '180px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '13px', lineHeight: '1.6' }}>
              {logs.map((l, idx) => <div key={idx}>&gt; {l}</div>)}
            </div>
          </div>

          <div>
            <h4 style={{ margin: '0 0 8px 0', color: '#475569' }}>📋 Strategic Verdict Portfolio Report</h4>
            <div style={{ padding: '24px', borderRadius: '8px', border: '1px solid #e2e8f0', backgroundColor: '#ffffff', minHeight: '300px', color: '#0f172a', lineHeight: '1.7', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
              {verdict ? (
                renderFormattedReport(verdict)
              ) : (
                <span style={{ color: '#94a3b8' }}>Synthesis container outputs will render here when agent runs conclude...</span>
              )}
            </div>
          </div>
        </div>
      </main>

    </div>
  );
}

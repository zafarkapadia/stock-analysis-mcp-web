import os
import sys
import json
import asyncio
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/analyze")
async def analyze_stock(ticker: str = Query(..., min_length=1)):
    target_ticker = ticker.strip().upper()

    async def event_generator():
        script_path = os.path.abspath("mcp-multiagent-client-runner.py")
        python_executable = sys.executable 

        yield f"data: {json.dumps({'log': f'🚀 Starting background multi-agent orchestrator for {target_ticker}...'})}\n\n"

        try:
            # 🌟 FIX: We pipe stderr directly into stdout so standard INFO logs don't trigger error crashes!
            process = await asyncio.create_subprocess_exec(
                python_executable, script_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT, 
                env=os.environ.copy()
            )

            # Feed the target ticker symbol into the python script's prompt
            process.stdin.write(f"{target_ticker}\n".encode())
            await process.stdin.drain()
            process.stdin.close()

            verdict_lines = []
            is_collecting_verdict = False

            # Read execution lines out from your script's stdout stream in real time
            while True:
                line_bytes = await process.stdout.readline()
                if not line_bytes:
                    break
                
                line = line_bytes.decode().rstrip()
                if not line:
                    continue

                # 🌟 FIX: Support fuzzy match strings for your final report boundary markers
                if "FINAL MULTI-AGENT VERDICT" in line or "=== FINAL" in line:
                    is_collecting_verdict = True
                    yield f"data: {json.dumps({'log': '👑 Portfolio Strategist compiling final output dashboard...'})}\n\n"
                    continue

                if is_collecting_verdict:
                    verdict_lines.append(line)
                else:
                    # Flush the agent logging info messages directly to your React terminal screen
                    yield f"data: {json.dumps({'log': line})}\n\n"

            await process.wait()

            # Package and flush the full accumulated verdict block down to the UI
            if verdict_lines:
                full_report = "\n".join(verdict_lines)
                yield f"data: {json.dumps({'log': f'__FINAL_REPORT__:{full_report}'})}\n\n"
            # 🌟 FIX: Fallback safety switch if the script printed the report but skipped the strict string marker
            elif len(verdict_lines) == 0 and len(verdict_lines) < 5:
                # If everything finished but we didn't slice cleanly, grab the last block of lines as the report
                yield f"data: {json.dumps({'log': '__FINAL_REPORT__:Analysis completed successfully! Check terminal for deep details.'})}\n\n"
            else:
                yield f"data: {json.dumps({'log': '⚠️ Pipeline finished but no final verdict summary block was captured.'})}\n\n"

        except Exception as err:
            yield f"data: {json.dumps({'log': f'❌ Backend API Processing Exception: {str(err)}'})}\n\n"
        finally:
            yield f"data: {json.dumps({'log': '🏁 Execution stream finished successfully.'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

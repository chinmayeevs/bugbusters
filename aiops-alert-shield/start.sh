#!/usr/bin/env bash
# start.sh - Production Launcher for AIOps Alert Shield (Linux / macOS)

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "================================================================================"
echo "  AIOPS ALERT SHIELD // ORCHESTRATED ALERT VERIFICATION PLATFORM"
echo "================================================================================"

# 1. Environment Check
if [ ! -f "$ROOT_DIR/.env" ]; then
    if [ -f "$ROOT_DIR/.env.example" ]; then
        echo "[INIT] Copying .env.example to .env..."
        cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    else
        echo "[INIT] Creating default .env configuration..."
        cat <<EOF > "$ROOT_DIR/.env"
MOCK_LLM=true
LLM_PROVIDER=gemini
LLM_MODEL=gemini/gemini-2.5-flash
LLM_TIMEOUT_SECONDS=25
LLM_MAX_TOKENS=1200
EOF
    fi
fi

# 2. Export PYTHONPATH
export PYTHONPATH="$ROOT_DIR"

# 3. Check / Start Backend API (FastAPI on Port 8000)
echo "[1/3] Checking backend API on port 8000..."
if curl -s -f http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "  Backend already active at http://127.0.0.1:8000"
else
    echo "  Starting FastAPI backend on port 8000..."
    python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
    BACKEND_PID=$!
    echo "  Backend started (PID: $BACKEND_PID), polling /health..."

    for i in {1..20}; do
        sleep 0.8
        if curl -s -f http://127.0.0.1:8000/health > /dev/null 2>&1; then
            echo "  Backend successfully initialized at http://127.0.0.1:8000"
            break
        fi
        if [ "$i" -eq 20 ]; then
            echo "[ERROR] Backend failed to start. Check backend.log."
            exit 1
        fi
    done
fi

# 4. Check Frontend (Next.js on Port 3000)
echo "[2/3] Checking Next.js operational console on port 3000..."
if nc -z 127.0.0.1 3000 2>/dev/null; then
    echo "  Frontend console already listening on http://localhost:3000"
else
    echo "  Starting Next.js frontend on port 3000..."
    cd "$ROOT_DIR/frontend"
    npm start -- -p 3000 > ../frontend.log 2>&1 &
    cd "$ROOT_DIR"
    sleep 2
fi

# 5. Ready Banner & Commands
echo ""
echo "================================================================================"
echo "  AIOPS ALERT SHIELD PLATFORM READY"
echo "================================================================================"
echo "  Operational Web Console:   http://localhost:3000"
echo "  GraphQL Playground:        http://localhost:8000/graphql"
echo "  System Health Check:       http://localhost:8000/health"
echo "--------------------------------------------------------------------------------"
echo "  Evaluation Benchmark CLI:  python3 scripts/evaluate_system.py"
echo "  Live Stream Replay CLI:    python3 scripts/replay_stream.py --speed 5.0"
echo "  Run Pytest Test Suite:     python3 -m pytest tests -v"
echo "================================================================================"
echo ""

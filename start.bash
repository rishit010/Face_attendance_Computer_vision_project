#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
#  Face Attendance System — Full-Stack Start Script
#  Usage: bash start.bash
#
#  What this does:
#    1. Checks Python 3.11+ is available
#    2. Creates a virtual environment (venv) if not already present
#    3. Installs all Python dependencies
#    4. Creates required directories
#    5. Installs frontend Node.js dependencies
#    6. Starts the FastAPI backend on http://localhost:8000
#    7. Starts the Vite React frontend on http://localhost:5173
# ═══════════════════════════════════════════════════════════════════════════

set -e  # Exit immediately on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/venv"

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Colour

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }
info() { echo -e "${CYAN}[→]${NC} $1"; }

echo ""
echo -e "${BOLD}═══════════════════════════════════════════${NC}"
echo -e "${BOLD}   Face Attendance System — Startup        ${NC}"
echo -e "${BOLD}═══════════════════════════════════════════${NC}"
echo ""

# ── Step 1: Find Python 3.11+ ───────────────────────────────────────────────
info "Looking for Python 3.11+..."

PYTHON=""
for candidate in python3.11 python3 python; do
    if command -v "$candidate" &>/dev/null; then
        VERSION=$("$candidate" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        MAJOR=$(echo "$VERSION" | cut -d. -f1)
        MINOR=$(echo "$VERSION" | cut -d. -f2)
        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 11 ]; then
            PYTHON="$candidate"
            log "Found: $($PYTHON --version)"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    err "Python 3.11+ not found. Install it from https://www.python.org/downloads/ and re-run."
fi

# ── Step 2: Check Node.js ───────────────────────────────────────────────────
info "Checking Node.js..."

if ! command -v node &>/dev/null; then
    err "Node.js not found. Install it from https://nodejs.org/ (v18+ required) and re-run."
fi

NODE_VERSION=$(node --version | grep -oE '[0-9]+' | head -1)
if [ "$NODE_VERSION" -lt 18 ]; then
    err "Node.js v18+ required (found $(node --version)). Please upgrade."
fi
log "Found: Node $(node --version)"

# ── Step 3: Create virtual environment ──────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    info "Creating virtual environment at $VENV_DIR ..."
    "$PYTHON" -m venv "$VENV_DIR"
    log "Virtual environment created"
else
    log "Virtual environment already exists — skipping creation"
fi

# Activate venv
source "$VENV_DIR/bin/activate"
log "Virtual environment activated"

# ── Step 4: Upgrade pip + install Python deps ───────────────────────────────
info "Upgrading pip..."
pip install --upgrade pip --quiet

info "Installing Python dependencies from requirements.txt..."
pip install -r "$BACKEND_DIR/requirements.txt" --quiet
log "Python dependencies installed"

# ── Step 5: Create required directories ─────────────────────────────────────
info "Creating required directories..."
mkdir -p "$BACKEND_DIR/uploads/faces/embeddings"
mkdir -p "$BACKEND_DIR/uploads/faces/images"
log "Directories ready"

# ── Step 6: Download InsightFace models (first run only) ────────────────────
info "Pre-downloading InsightFace buffalo_l model (first run only — ~300MB)..."
"$PYTHON" -c "
from insightface.app import FaceAnalysis
app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))
print('InsightFace models ready')
" 2>/dev/null && log "InsightFace models ready" || warn "InsightFace model download skipped — will download on first request"

# ── Step 7: Install frontend dependencies ───────────────────────────────────
info "Installing frontend dependencies..."
cd "$FRONTEND_DIR"
npm install --silent 2>/dev/null || npm install
log "Frontend dependencies installed"
cd "$SCRIPT_DIR"

# ── Step 8: Launch both servers ─────────────────────────────────────────────
echo ""
echo -e "${BOLD}═══════════════════════════════════════════${NC}"
echo -e "${BOLD}   Starting Full-Stack Application         ${NC}"
echo -e "${BOLD}═══════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}Frontend:${NC}    http://localhost:5173"
echo -e "  ${CYAN}Backend API:${NC} http://localhost:8000"
echo -e "  ${CYAN}API Docs:${NC}    http://localhost:8000/docs"
echo -e "  ${CYAN}Health:${NC}      http://localhost:8000/health"
echo ""
echo -e "  ${YELLOW}Login Accounts:${NC}"
echo -e "    Teacher        → teacher@muj.manipal.edu / teacher123"
echo -e "    Student Portal → student@muj.manipal.edu / student123"
echo ""
echo -e "  ${YELLOW}SMTP Email (optional — set in backend/.env):${NC}"
echo -e "    SMTP_ENABLED=true"
echo -e "    SMTP_HOST=smtp.gmail.com"
echo -e "    SMTP_USER=your-email@gmail.com"
echo -e "    SMTP_PASSWORD=your-app-password"
echo ""
echo -e "  ${RED}Press Ctrl+C to stop both servers${NC}"
echo ""

# Trap SIGINT to kill both background processes
cleanup() {
    echo ""
    info "Shutting down..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID 2>/dev/null
    wait $FRONTEND_PID 2>/dev/null
    log "All servers stopped"
    exit 0
}
trap cleanup SIGINT SIGTERM

# Start backend
cd "$BACKEND_DIR"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start frontend
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!

cd "$SCRIPT_DIR"

# Wait for either to exit
wait $BACKEND_PID $FRONTEND_PID

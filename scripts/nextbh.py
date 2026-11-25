"""
Next-BH local launcher (Windows, Linux, macOS). Standard library only.

    python scripts/nextbh.py doctor          check prerequisites and running services
    python scripts/nextbh.py setup           create .venv (Python 3.12) and generate synthetic data
    python scripts/nextbh.py models          pre-download the LLM and embedding models (resumable)
    python scripts/nextbh.py up              start Docker infra, recommendation API, policy-service, Ollama
    python scripts/nextbh.py down            stop what `up` started
    python scripts/nextbh.py status          show services and URLs
    python scripts/nextbh.py rag             run the Data & RAG pipeline and promote if approved
    python scripts/nextbh.py rl [--quick]    run the RL pipeline and promote if approved
    python scripts/nextbh.py agent [--once]  run the sales agent (needs Ollama, see doctor)
    python scripts/nextbh.py relay [--once]  publish admin verdicts as decision_events
    python scripts/nextbh.py demo            recommendation + draft review demos (disposable MongoDB)
    python scripts/nextbh.py dashboard [--staging]  review dashboard pilot (Git Bash on Windows)
    python scripts/nextbh.py test            unit tests and lint

Settings come from `.env` at the repository root when present (see .env.example), then from
the defaults below. Background processes log to .run/<name>.log.
"""

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / ".run"
WINDOWS = os.name == "nt"
VENV = ROOT / ".venv"
VENV_PYTHON = VENV / ("Scripts/python.exe" if WINDOWS else "bin/python")

DEFAULTS = {
    "MONGODB_URI": "mongodb://localhost:27017/BH",
    "RECO_API_URL": "http://localhost:8083",
    "CHROMA_HOST": "localhost",
    "CHROMA_PORT": "8000",
    "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
    "POLICY_SERVICE_URL": "http://localhost:8010",
    "ARTIFACT_ROOT": str(ROOT / "artifacts"),
    "POLICY_MODEL_MANIFEST": str(ROOT / "artifacts" / "rl" / "latest.json"),
    "API_RESULTS_DIR": str(ROOT / ".run" / "api_results"),
    "PYTHONUTF8": "1",
    "PYTHONIOENCODING": "utf-8",
}

SERVICES = {
    # name: (command builder, working directory, health URL)
    "api": (lambda py: [py, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8083"],
            ROOT / "api_datasets", "http://127.0.0.1:8083/"),
    "policy": (lambda py: [py, "-m", "uvicorn", "policy_service.app:app", "--host", "127.0.0.1",
                           "--port", "8010"], ROOT, "http://127.0.0.1:8010/health"),
}

URLS = {
    "API recommandation (Swagger)": "http://127.0.0.1:8083/docs",
    "Policy-service (Swagger)": "http://127.0.0.1:8010/docs",
    "mongo-express": "http://127.0.0.1:8081",
    "ChromaDB": "http://127.0.0.1:8000/api/v2/heartbeat",
    "Zipkin": "http://127.0.0.1:9411",
    "Ollama (LLM de l'agent)": "http://127.0.0.1:11434/api/version",
    "AKHQ (Kafka, --events)": "http://127.0.0.1:8090",
}


# ---------------- helpers ----------------


def load_env() -> dict:
    env = dict(os.environ)
    for key, value in DEFAULTS.items():
        env.setdefault(key, value)
    dotenv = ROOT / ".env"
    if dotenv.exists():
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip() if not line.lstrip().startswith("#") else ""
            if "=" in line:
                key, value = (part.strip() for part in line.split("=", 1))
                if value:
                    env[key] = value
    rag_latest = Path(env["ARTIFACT_ROOT"]) / "rag" / "latest.json"
    if rag_latest.exists():
        env.setdefault("RAG_INDEX_MANIFEST", str(rag_latest))
    return env


def python() -> str:
    if not VENV_PYTHON.exists():
        sys.exit("No .venv yet: run `python scripts/nextbh.py setup` first.")
    return str(VENV_PYTHON)


def run(cmd, cwd=ROOT, env=None, check=True) -> int:
    print("$", " ".join(str(c) for c in cmd), flush=True)
    code = subprocess.call([str(c) for c in cmd], cwd=cwd, env=env or load_env())
    if check and code != 0:
        sys.exit(code)
    return code


def http_ok(url: str, timeout: float = 5.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status < 500
    except urllib.error.HTTPError as e:
        return e.code < 500  # e.g. 401 from mongo-express: the service answers
    except Exception:
        return False


def port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def wait_for(url: str, seconds: int) -> bool:
    for _ in range(seconds):
        if http_ok(url):
            return True
        time.sleep(1)
    return False


def pids() -> dict:
    path = RUN_DIR / "pids.json"
    return json.loads(path.read_text()) if path.exists() else {}


def save_pids(data: dict) -> None:
    RUN_DIR.mkdir(exist_ok=True)
    (RUN_DIR / "pids.json").write_text(json.dumps(data, indent=2))


def alive(pid: int) -> bool:
    if WINDOWS:
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                             capture_output=True, text=True).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def start_background(name: str, cmd, cwd: Path, env: dict) -> int:
    RUN_DIR.mkdir(exist_ok=True)
    log = open(RUN_DIR / f"{name}.log", "ab")
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if WINDOWS else 0
    proc = subprocess.Popen([str(c) for c in cmd], cwd=cwd, env=env, stdout=log,
                            stderr=subprocess.STDOUT, creationflags=flags,
                            start_new_session=not WINDOWS)
    return proc.pid


def stop_pid(pid: int) -> None:
    if WINDOWS:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    else:
        try:
            os.killpg(pid, signal.SIGTERM)
        except OSError:
            pass


def compose(*args, check=True) -> int:
    files = ["-f", "docker-compose.yaml"]
    return run(["docker", "compose", *files, *args], check=check)


def find_bash() -> str:
    if not WINDOWS:
        return shutil.which("bash") or "bash"
    git = shutil.which("git")
    candidates = []
    if git:
        git_root = Path(git).resolve().parents[1]
        candidates += [git_root / "bin" / "bash.exe", git_root / "usr" / "bin" / "bash.exe"]
    candidates += [Path(r"C:\Program Files\Git\bin\bash.exe")]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    sys.exit("Git Bash not found: install Git for Windows to run the dashboard pilot.")


# ---------------- commands ----------------


def cmd_setup(args) -> None:
    uv = shutil.which("uv")
    if uv:
        if not VENV_PYTHON.exists():
            run([uv, "venv", "--python", "3.12", str(VENV)])
        run([uv, "pip", "install", "--python", str(VENV_PYTHON), "-r", "requirements-local.txt"])
    else:
        if not VENV_PYTHON.exists():
            run([sys.executable, "-m", "venv", str(VENV)])
        run([str(VENV_PYTHON), "-m", "pip", "install", "-r", "requirements-local.txt"])
    run([python(), "scripts/generate_synthetic_datasets.py"])
    print("\nSetup done. Next: python scripts/nextbh.py up")


def cmd_doctor(args) -> None:
    env = load_env()
    checks = []

    def check(label, ok, hint=""):
        checks.append(ok)
        print(f"  [{'OK' if ok else '--'}] {label}{'' if ok or not hint else '  -> ' + hint}")

    print("Prerequisites")
    check(".venv (Python 3.12)", VENV_PYTHON.exists(), "python scripts/nextbh.py setup")
    docker_ok = subprocess.run(["docker", "info"], capture_output=True).returncode == 0 \
        if shutil.which("docker") else False
    check("Docker engine", docker_ok, "start Docker Desktop")
    check("Node.js / npm (dashboard)", bool(shutil.which("node") and shutil.which("npm")),
          "install Node.js 22+")
    check("Synthetic API datasets",
          (ROOT / "api_datasets" / "catboost_pm.csv").exists(),
          "python scripts/generate_synthetic_datasets.py")
    check("RAG documents", any((ROOT / "data" / "rag_docs").glob("*/*")),
          "python scripts/generate_synthetic_datasets.py")

    print("Services")
    check("MongoDB :27017", port_open(27017), "python scripts/nextbh.py up")
    check("ChromaDB :8000", http_ok("http://127.0.0.1:8000/api/v2/heartbeat"), "python scripts/nextbh.py up")
    check("Recommendation API :8083", http_ok("http://127.0.0.1:8083/"), "python scripts/nextbh.py up")
    check("Policy-service :8010", http_ok("http://127.0.0.1:8010/health"), "python scripts/nextbh.py up")
    model = env.get("NEXTBH_LLM_MODEL", "gemma3n:e4b")
    tags = ""
    try:
        with urllib.request.urlopen(f"{env['OLLAMA_BASE_URL']}/api/tags", timeout=2) as r:
            tags = r.read().decode()
    except Exception:
        pass
    check(f"Ollama ({env['OLLAMA_BASE_URL']})", bool(tags), "start `ollama serve` (needed by the agent)")
    check(f"Ollama model {model}", f'"{model}"' in tags or f'"name":"{model}"' in tags,
          f"ollama pull {model}")

    print("Artifacts")
    art = Path(env["ARTIFACT_ROOT"])
    check("RAG index promoted (rag/latest.json)", (art / "rag" / "latest.json").exists(),
          "python scripts/nextbh.py rag")
    check("RL policy promoted (rl/latest.json)", (art / "rl" / "latest.json").exists(),
          "python scripts/nextbh.py rl")
    print(f"\n{sum(checks)}/{len(checks)} checks passed")


PORTABLE_OLLAMA = ROOT.parent / "tools" / "ollama"


def ollama_command(env: dict):
    """Installed `ollama`, else the portable copy in ../tools/ollama (with its own models dir)."""
    env = dict(env)
    env["OLLAMA_HOST"] = env["OLLAMA_BASE_URL"].split("://", 1)[-1]
    installed = shutil.which("ollama")
    if installed:
        return installed, env
    portable = PORTABLE_OLLAMA / ("ollama.exe" if WINDOWS else "ollama")
    if portable.exists():
        env.setdefault("OLLAMA_MODELS", str(PORTABLE_OLLAMA / "models"))
        return str(portable), env
    return None, env


def start_ollama(env: dict, running: dict) -> None:
    if http_ok(f"{env['OLLAMA_BASE_URL']}/api/version"):
        print("ollama: already running")
        return
    exe, ollama_env = ollama_command(env)
    if not exe:
        print("ollama: not installed (needed by the agent, see docs/DEMARRAGE_LOCAL.md)")
        return
    running["ollama"] = start_background("ollama", [exe, "serve"], ROOT, ollama_env)
    save_pids(running)
    ok = wait_for(f"{env['OLLAMA_BASE_URL']}/api/version", 60)
    print(f"ollama: {'up' if ok else 'NOT READY, see .run/ollama.log'} (pid {running['ollama']})")


def cmd_up(args) -> None:
    env = load_env()
    compose("up", "-d")
    if args.events:
        # Kafka Connect is left out: it is built locally and does not fit a 2 GB Docker VM
        compose("--profile", "events", "up", "-d", "kafka", "akhq")
    py = python()
    running = pids()
    for name, (builder, cwd, health) in SERVICES.items():
        if http_ok(health):
            print(f"{name}: already running")
            continue
        pid = start_background(name, builder(py), cwd, env)
        running[name] = pid
        save_pids(running)
        ok = wait_for(health, 120)
        print(f"{name}: {'up' if ok else 'NOT READY, see .run/' + name + '.log'} (pid {pid})")
    start_ollama(env, running)
    if not wait_for("http://127.0.0.1:8000/api/v2/heartbeat", 120):
        print("ChromaDB not ready yet: check `docker compose logs server`")
    cmd_status(args)


def cmd_down(args) -> None:
    for name, pid in pids().items():
        if alive(pid):
            stop_pid(pid)
            print(f"{name}: stopped (pid {pid})")
    save_pids({})
    if not args.keep_infra:
        compose("--profile", "events", "down")


def cmd_status(args) -> None:
    print("\nServices")
    for label, url in URLS.items():
        state = "up" if http_ok(url) else "down"
        print(f"  {state:4}  {label:32} {url}")
    print("  " + ("up  " if port_open(27017) else "down") + "  MongoDB" + " " * 26 + "mongodb://127.0.0.1:27017/BH")


def cmd_rag(args) -> None:
    run([python(), "-m", "mlops.data_rag.run", "--promote", "--by", args.by])


def cmd_rl(args) -> None:
    extra = ["--quick"] if args.quick else []
    if args.algorithms:
        extra += ["--algorithms", *args.algorithms]
    run([python(), "-m", "mlops.rl.run", *extra, "--promote", "--by", args.by], check=False)
    if http_ok("http://127.0.0.1:8010/health"):
        urllib.request.urlopen(urllib.request.Request(
            "http://127.0.0.1:8010/policy/reload", method="POST"), timeout=10).read()
        print("policy-service reloaded")


def cmd_agent(args) -> None:
    run([python(), "app.py", *(["--once"] if args.once else [])], cwd=ROOT / "agent")


def cmd_relay(args) -> None:
    run([python(), "-m", "mlops.feedback.verdict_relay", *(["--once"] if args.once else [])])


def cmd_demo(args) -> None:
    py = python()
    run([py, "-B", "scripts/demo_recommendation.py"])
    container = subprocess.run(
        ["docker", "run", "--rm", "-d", "-p", "127.0.0.1::27017", "mongo:7.0"],
        capture_output=True, text=True, check=True).stdout.strip()
    try:
        for _ in range(60):
            ping = subprocess.run(["docker", "exec", container, "mongosh", "--quiet", "--eval",
                                   "db.adminCommand({ping: 1}).ok"], capture_output=True)
            if ping.returncode == 0:
                break
            time.sleep(1)
        mapping = subprocess.run(["docker", "port", container, "27017/tcp"],
                                 capture_output=True, text=True, check=True).stdout
        port = mapping.splitlines()[0].rsplit(":", 1)[1]
        run([py, "-B", "scripts/check_draft_decisions.py", "--port", port])
        run([py, "-B", "scripts/demo_draft_review.py", "--port", port])
    finally:
        subprocess.run(["docker", "stop", container], capture_output=True)


CATALOG = ROOT / "scripts" / "fixtures" / "wave3-catalog.json"
CATALOG_SHA256 = "d121baca9ecb41d985e4a1d30372253c1a87ed8f7dff72f31c6c264832ffe1e2"  # STAGING_PILOT.md


def cmd_dashboard(args) -> None:
    # Bash's dirname only splits on "/": hand over C:/... rather than C:\...
    command = [find_bash(), "scripts/run_dashboard_review_pilot.sh", python().replace("\\", "/")]
    if args.staging:
        env = load_env()
        model = env.get("NEXTBH_LLM_MODEL", "gemma3n:e4b")
        with urllib.request.urlopen(f"{env['OLLAMA_BASE_URL']}/api/tags", timeout=5) as r:
            tags = json.loads(r.read())["models"]
        digest = next((m["digest"] for m in tags if m["name"] == model), None)
        if not digest:
            sys.exit(f"{model} is not available in Ollama: python scripts/nextbh.py models")
        command += ["--staging", args.reviewer, "--catalog", str(CATALOG).replace("\\", "/"),
                    "--catalog-sha256", CATALOG_SHA256, "--ollama-url", env["OLLAMA_BASE_URL"],
                    "--ollama-digest", digest]
    print("The dashboard URL and a temporary password are printed below; Ctrl-C stops it.")
    run(command, check=False)


HF_DOWNLOAD = r'''
import os, sys, time
from huggingface_hub import list_repo_files, snapshot_download
for repo in sys.argv[1:]:
    files = list_repo_files(repo)
    # one weight format is enough: safetensors when published, else the PyTorch .bin
    weights = ["*.safetensors"] if any(f.endswith(".safetensors") for f in files) else ["*.bin"]
    patterns = ["*.json", "*.txt", "*.model", "*.py", "**/*.json", *weights]
    for attempt in range(1, 31):
        try:
            snapshot_download(repo, allow_patterns=patterns, ignore_patterns=["onnx/*", "openvino/*"])
            print(f"{repo}: ok", flush=True)
            break
        except Exception as e:  # flaky networks: downloads resume where they stopped
            print(f"{repo}: attempt {attempt} failed ({type(e).__name__}), retrying", flush=True)
            time.sleep(min(60, 5 * attempt))
    else:
        sys.exit(f"{repo}: download failed")
'''


def cmd_models(args) -> None:
    """Pre-download every model the agent and the RAG pipeline load, resuming on failure."""
    env = load_env()
    hf = [env.get("NEXTBH_EMBEDDING_MODEL", "intfloat/multilingual-e5-large"),
          env.get("NEXTBH_INTENT_MODEL", "joeddav/xlm-roberta-large-xnli"),
          env.get("NEXTBH_LLM_SMALL_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")]
    run([python(), "-c", HF_DOWNLOAD, *hf], env=env)
    model = env.get("NEXTBH_LLM_MODEL", "gemma3n:e4b")
    ollama, env = ollama_command(env)
    if not ollama:
        print(f"Ollama not found: install it, then run `ollama pull {model}`")
        return
    for attempt in range(1, 31):
        if run([ollama, "pull", model], env=env, check=False) == 0:
            return
        print(f"ollama pull {model}: attempt {attempt} failed, retrying")
        time.sleep(min(60, 5 * attempt))
    sys.exit(f"ollama pull {model} failed")


def cmd_test(args) -> None:
    py = python()
    run([py, "-m", "pytest", "-p", "no:cacheprovider"])
    lint = ["mlops", "policy_service", "scripts/smoke_policy_service.py", "scripts/nextbh.py",
            "scripts/generate_synthetic_datasets.py", "agent/orchestrator.py",
            "agent/compliance.py", "agent/feature_flags.py", "agent/utils/policy_client.py",
            "agent/utils/event_publisher.py", "agent/utils/llm_output.py", "agent/tests"]
    run([py, "-m", "ruff", "check", *lint])


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup").set_defaults(func=cmd_setup)
    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    up = sub.add_parser("up")
    up.add_argument("--events", action="store_true", help="also start Kafka and AKHQ")
    up.set_defaults(func=cmd_up)
    down = sub.add_parser("down")
    down.add_argument("--keep-infra", action="store_true")
    down.set_defaults(func=cmd_down)
    sub.add_parser("status").set_defaults(func=cmd_status)
    rag = sub.add_parser("rag")
    rag.add_argument("--by", default="local")
    rag.set_defaults(func=cmd_rag)
    rl = sub.add_parser("rl")
    rl.add_argument("--quick", action="store_true")
    rl.add_argument("--algorithms", nargs="+")
    rl.add_argument("--by", default="local")
    rl.set_defaults(func=cmd_rl)
    agent = sub.add_parser("agent")
    agent.add_argument("--once", action="store_true")
    agent.set_defaults(func=cmd_agent)
    relay = sub.add_parser("relay")
    relay.add_argument("--once", action="store_true")
    relay.set_defaults(func=cmd_relay)
    sub.add_parser("demo").set_defaults(func=cmd_demo)
    sub.add_parser("models").set_defaults(func=cmd_models)
    dashboard = sub.add_parser("dashboard")
    dashboard.add_argument("--staging", action="store_true",
                           help="generate the 24 wave-3 drafts with the Ollama model first")
    dashboard.add_argument("--reviewer", default="reviewer@example.invalid")
    dashboard.set_defaults(func=cmd_dashboard)
    sub.add_parser("test").set_defaults(func=cmd_test)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

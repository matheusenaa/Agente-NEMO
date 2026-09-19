"""
NEMO IDE — Launcher universal (Windows, Linux, Antigravity/nuvem).

Uso:
    python start_nemo.py               # inicia backend + dashboard compilado e abre o navegador
    python start_nemo.py --host 0.0.0.0
    python start_nemo.py --port 8798
    python start_nemo.py --no-browser  # não abre o navegador automaticamente
    python start_nemo.py --check       # modo diagnóstico (não inicia o servidor)
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dashboard" / "dist"
DEFAULT_HOST = os.getenv("HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("PORT", "8798"))


def print_banner() -> None:
    print("=" * 54)
    print("  🐟 NEMO IDE — Sala de operações dos agentes de IA")
    print("=" * 54)


def run(cmd: list[str], what: str) -> bool:
    print(f"\n▶ {what} ...")
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), text=True)
        return proc.returncode == 0
    except Exception as exc:  # pragma: no cover
        print(f"  ✖ Falha ao executar {what}: {exc}")
        return False


def check_environment() -> list[str]:
    problems: list[str] = []
    if shutil.which("python") is None:
        problems.append("Python não encontrado no PATH.")
    try:
        import fastapi  # noqa: F401
    except Exception:
        problems.append("Dependências Python ausentes. Rode: pip install -r requirements.txt")
    if not Path(ROOT / ".env").is_file():
        print("  ⚠  Arquivo .env não encontrado (o chat usará o modo offline).")
    if DIST.is_dir() and (DIST / "index.html").is_file():
        pass
    else:
        problems.append(
            "Dashboard não compilado. Será construído agora (requer Node.js). "
            "Se o Node não estiver no PATH, rode manualmente: cd dashboard && npm install && npm run build"
        )
    if DIST.is_dir() and (DIST / "index.html").is_file():
        print("  ✓ Dashboard compilado encontrado.")
    return problems


def build_dashboard() -> bool:
    print("\n▶ Compilando o dashboard (npm install + build)...")
    try:
        npm = "npm.cmd" if os.name == "nt" else "npm"
        subprocess.run([npm, "install"], cwd=str(ROOT / "dashboard"), check=True, text=True)
        subprocess.run([npm, "run", "build"], cwd=str(ROOT / "dashboard"), check=True, text=True)
        print("  ✓ Dashboard compilado em dashboard/dist.")
        return True
    except Exception as exc:
        print(f"  ✖ Falha ao compilar o dashboard: {exc}")
        return False


def diagnose() -> int:
    print_banner()
    print("\n🔍 NEMO Diagnostic")
    print("-" * 54)

    checks: list[tuple[str, bool]] = []
    python_ver = sys.version.split()[0]
    checks.append((f"Python ............ {python_ver}", True))

    node = shutil.which("node")
    checks.append(("Node .............. " + (node or "não encontrado"), node is not None))
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    checks.append(("npm ............... " + (npm or "não encontrado"), npm is not None))

    try:
        import fastapi  # noqa: F401
        checks.append(("Dependências Python  OK", True))
    except Exception:
        checks.append(("Dependências Python  FALHOU (pip install -r requirements.txt)", False))

    if DIST.is_dir() and (DIST / "index.html").is_file():
        checks.append(("Frontend (dist) .... OK", True))
    else:
        checks.append(("Frontend (dist) .... FALTANDO (npm run build)", False))

    agents = ROOT / "agents"
    n_agents = len(list(agents.glob("*.agent.md"))) if agents.is_dir() else 0
    checks.append((f"Agentes ............ {n_agents} carregados", n_agents > 0))

    env_key = os.getenv("OPENROUTER_API_KEY", "")
    if Path(ROOT / ".env").is_file():
        env_key = env_key or _read_env_key()
    checks.append(("OpenRouter Key ..... " + ("configurada" if env_key else "não configurada (modo offline)"), True))

    port_busy = False
    if os.name == "nt":
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("127.0.0.1", DEFAULT_PORT))
            sock.close()
        except OSError:
            port_busy = True
    checks.append((f"Porta {DEFAULT_PORT} ........ " + ("em uso (outra instância NEMO?)" if port_busy else "livre"), True))

    try:
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=4).close()
        checks.append(("Internet ........... OK", True))
    except Exception:
        checks.append(("Internet ........... sem conexão", True))

    print()
    any_fail = False
    for label, ok in checks:
        status = "OK" if ok else "FALHA"
        if not ok:
            any_fail = True
        print(f"  {label}")
    print("-" * 54)
    print("NEMO READY — pode iniciar com: python start_nemo.py" if not any_fail
          else "Alguns itens apresentam pendências — veja os avisos acima.")
    return 0


def _read_env_key() -> str:
    try:
        for line in (ROOT / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="NEMO IDE Launcher")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--check", action="store_true", help="roda o diagnóstico e encerra")
    args = parser.parse_args()

    if args.check:
        return diagnose()

    print_banner()
    problems = check_environment()
    for p in problems:
        print(f"  ⚠  {p}")
    if any("Dependências" in p or p.startswith("Python") for p in problems):
        print("  ✖ Instale as dependências antes de continuar.")
        return 1
    if any("Dashboard não compilado" in p for p in problems) and not build_dashboard():
        return 1
    print()

    url = f"http://{args.host}:{args.port}/"
    print(f"🚀 Iniciando NEMO IDE em {url}")
    env = dict(os.environ)
    env.setdefault("PORT", str(args.port))
    env["HOST"] = args.host
    proc = subprocess.Popen(
        [sys.executable, "nemo_server.py", "--host", args.host, "--port", str(args.port)],
        cwd=str(ROOT),
        env=env,
    )

    def _open_browser() -> None:
        for _ in range(60):
            try:
                import urllib.request
                urllib.request.urlopen(f"{url}api/nemo/health", timeout=2)
                break
            except Exception:
                time.sleep(1)
        time.sleep(1.5)
        webbrowser.open(url)

    if not args.no_browser:
        threading.Thread(target=_open_browser, daemon=True).start()

    print("Pressione Ctrl+C para encerrar o servidor.\n")
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n⏹ Encerrando NEMO IDE...")
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
    return proc.returncode or 0


if __name__ == "__main__":
    sys.exit(main())
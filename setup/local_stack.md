# Low-resource local stack

## Verified environment

- Windows 11, NVIDIA RTX 5060 Laptop GPU (8 GB)
- Ollama 0.33.3, Windows native
- Docker Desktop 4.88.1, Linux engine
- WSL2 Ubuntu 24.04 available
- Harbor 0.22.0 executed through `uvx`

The evaluation runner is serial. It uses a 4,096-token context, caps agent steps, and unloads each
Ollama model after a run. Observed post-run GPU allocation was 0 MiB; point temperatures during
these small runs remained in the low-to-mid 60s °C.

## Models used

```powershell
ollama pull llama3.2:3b-instruct-q4_K_M
ollama pull qwen3:4b
ollama pull granite3.3:2b
```

Do not load agent and judge models concurrently. Generate trajectories first, unload, then judge
saved trajectories.

## Python setup

```powershell
uv sync --extra dev
.\run_all.cmd
```

Linux/WSL:

```bash
uv sync --extra dev
./run_all.sh
```

## Harbor smoke

The verified low-resource command uses one task, one concurrent container, one CPU and 2 GB RAM:

```powershell
$env:UV_CACHE_DIR = "$PWD/.uv-cache-harbor"
uvx harbor run -d terminal-bench/terminal-bench-2 -a nop -l 1 -n 1 `
  --cpus limit --memory limit --override-cpus 1 --override-memory-mb 2048
uvx harbor run -d terminal-bench/terminal-bench-2 -a oracle -l 1 -n 1 `
  --cpus limit --memory limit --override-cpus 1 --override-memory-mb 2048
```

The first run may download dependencies and a container image. The model-free `nop` and `oracle`
controls validate the harness before paying the cost of an agent run.

# How to Use the RING-5 Docker Sandbox

To ensure a clean, isolated, and reproducible development environment, you can use the Docker sandbox. I have integrated this into the `Makefile` so you can choose your preferred mode seamlessly.

## 1. Installation options

You can "install" the project in either mode. **Both are fully supported.**

### Local Installation

```bash
make install
```

### Containerized Installation (Docker)

```bash
make install USE_DOCKER=true
```

## 2. Execution Modes

The `Makefile` now supports an optional `USE_DOCKER` flag for all common tasks.

### Basic Mode (Local Host)

```bash
make test
make run
```

### Containerized Mode (Docker Sandbox)

```bash
make test USE_DOCKER=true
make run USE_DOCKER=true
```

## 3. Live Changes & Hot-Reloading

The code is mounted as a volume. This means:

- **Hot-Reloading**: If you edit a file in your editor, the Streamlit app (running in Docker) will refresh instantly.
- **Persistent Data**: Any files generated inside the container will appear on your local machine instantly.

## 4. Port Exposure

The application is automatically exposed on **<http://localhost:8501>**, exactly like the local version.

## 5. Working with Paths

When running in Docker, the application sees `/home/researcher/workspace` as the project root.

- **Project Data**: If your gem5 stats are inside the project (e.g., `data/stats.txt`), simply use the relative path `data/` in the UI.
- **External Data**: To parse files outside the project, you should move/copy them into the project directory or update the `volumes` in `docker-compose.yml`.

## 6. Maintenance

- **Rebuild**: `make docker-rebuild`
- **Clean**: `make docker-down`
- **Shell**: `make docker-shell`

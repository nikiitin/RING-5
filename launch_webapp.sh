#!/usr/bin/env bash
# Resolve the checkout before looking up its environment or application.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if [[ ! -x python_venv/bin/python ]]; then
    echo "Run 'make dev' in this checkout before launching RING-5." >&2
    exit 1
fi

# Bound native runtimes before pandas/NumPy are imported.
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-2}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-2}"
export VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-2}"

exec python_venv/bin/python -m streamlit run app.py --server.headless true "$@"

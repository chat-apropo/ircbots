#!/usr/bin/env bash
set -ex -o pipefail

is_dev=false
if [ "$1" == "dev" ]; then
	# Install dev dependencies
	is_dev=true
fi

# Loop throught directories in bots/ and build a separate environment for each using requirements.txt
for bot in bots/*; do
	if [ -d "$bot" ]; then
		pushd "$bot"
    VENV_DIR="$(pwd)/.venv"
    mkdir -p "$VENV_DIR"
    python -m venv "$VENV_DIR"
		source "$VENV_DIR/bin/activate"

		if [ "$is_dev" = true ] && [ -f requirements-dev.txt ]; then
			pip install --no-cache-dir install -r requirements-dev.txt
		fi
		pip install --no-cache-dir install -r requirements.txt

    deactivate
		popd
	fi
done

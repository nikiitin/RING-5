#!/bin/bash

TEMPLATE_PATH="templates/.Rprofile-template"
TARGET_PATH=".Rprofile"
ROOT_PATH="$(pwd)"
GENERATED_CODE_PATH="ring_env\$root_dir <- \"$ROOT_PATH\""


if [ -f "$TEMPLATE_PATH" ]; then
    sed "s|# RINGGENERATED|$GENERATED_CODE_PATH|g" "$TEMPLATE_PATH" > "$TARGET_PATH"
    echo "Updated .Rprofile with the root path: $ROOT_PATH"
else
    echo "Template file does not exist: $TEMPLATE_PATH"
    exit 1
fi
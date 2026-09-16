#!/usr/bin/env bash
# Shared state resolution. Source-tree use prefers its pinned project runtime;
# a release extraction (which has no runtime) uses the company-local state.
if [[ -z "${PROJECT_ROOT:-}" ]]; then
  PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
fi
if [[ -z "${LOCALLE_STATE_DIR:-}" && -x "$PROJECT_ROOT/.n8n-runtime/node_modules/.bin/n8n" ]]; then
  STATE_DIR="$PROJECT_ROOT/.n8n-runtime"
else
  STATE_DIR=${LOCALLE_STATE_DIR:-"$HOME/.localle"}
fi
if [[ -n "${LOCALLE_N8N_RUNTIME:-}" ]]; then
  RUNTIME_DIR="$LOCALLE_N8N_RUNTIME"
elif [[ -x "$STATE_DIR/node_modules/.bin/n8n" ]]; then
  RUNTIME_DIR="$STATE_DIR"
else
  RUNTIME_DIR="$STATE_DIR/n8n-runtime"
fi
if [[ -n "${LOCALLE_N8N_USER_FOLDER:-}" ]]; then
  USER_FOLDER="$LOCALLE_N8N_USER_FOLDER"
elif [[ "$RUNTIME_DIR" == "$STATE_DIR" && -d "$STATE_DIR/user" ]]; then
  USER_FOLDER="$STATE_DIR/user"
else
  USER_FOLDER="$STATE_DIR/n8n-user"
fi
if [[ -n "${LOCALLE_WORKFLOW_FILE:-}" ]]; then
  WORKFLOW_FILE="$LOCALLE_WORKFLOW_FILE"
else
  WORKFLOW_FILE="$PROJECT_ROOT/n8n/Localle_Option_B_Reservation_Intake_FINAL.n8n.json"
fi

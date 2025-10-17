# No websockets needed: POST prompt -> poll /history -> fetch images via /view

import os
import uuid
import json
import time
import urllib.request
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

server_address = "192.168.100.143:8188"
client_id = str(uuid.uuid4())

WORKFLOWS_DIR = Path(__file__).parent / "workflows"
DEFAULT_WORKFLOW_NAME = "illustrious"


@dataclass(frozen=True)
class WorkflowConfig:
    """Lightweight descriptor for a workflow file and how to override key fields."""

    name: str
    filename: str
    field_paths: Dict[str, Tuple[str, ...]]

    @property
    def path(self) -> Path:
        return WORKFLOWS_DIR / self.filename


class WorkflowManager:
    """
    Handles loading workflow definitions and applying prompt overrides.
    Additional workflows only need to be registered in `WORKFLOW_CONFIGS`.
    """

    def __init__(self, configs: Dict[str, WorkflowConfig], default: str):
        self._configs = configs
        self._active = os.getenv("COMFY_ACTIVE_WORKFLOW", default)

    # --- workflow bookkeeping -------------------------------------------------
    def list_workflows(self) -> List[str]:
        return sorted(self._configs.keys())

    def set_active(self, name: str) -> None:
        if name not in self._configs:
            raise ValueError(f"Unknown workflow '{name}'. Available: {self.list_workflows()}")
        self._active = name

    def get_active(self) -> str:
        if self._active not in self._configs:
            if not self._configs:
                raise RuntimeError("No workflows configured.")
            self._active = self.list_workflows()[0]
        return self._active

    # --- loading and defaults -------------------------------------------------
    def _load(self, name: Optional[str] = None) -> Tuple[WorkflowConfig, Dict[str, Any]]:
        target = self.get_active() if name is None else name
        if target not in self._configs:
            raise ValueError(f"Unknown workflow '{target}'. Available: {self.list_workflows()}")
        config = self._configs[target]
        path = config.path
        if not path.exists():
            raise FileNotFoundError(f"Workflow file not found: {path}")
        with path.open("r", encoding="utf-8") as fh:
            return config, json.load(fh)

    def get_defaults(self, name: Optional[str] = None) -> Dict[str, Any]:
        config, workflow = self._load(name)
        return _extract_defaults(workflow, config.field_paths)

    # --- override application -------------------------------------------------
    def build_workflow(
        self,
        *,
        positive: Optional[str],
        negative: Optional[str],
        seed: Optional[int],
    ) -> Dict[str, Any]:
        config, workflow = self._load()
        defaults = _extract_defaults(workflow, config.field_paths)

        resolved = {
            "positive": positive if positive is not None else defaults.get("positive"),
            "negative": negative if negative is not None else defaults.get("negative"),
            "seed": seed if seed is not None else defaults.get("seed"),
        }

        if resolved["positive"] is None:
            raise ValueError(
                f"Positive text is required but no default exists for workflow '{config.name}'"
            )

        for field, value in resolved.items():
            if value is None:
                continue
            path = config.field_paths.get(field)
            if path:
                _set_by_path(workflow, path, value)

        return workflow


def _get_by_path(data: Dict[str, Any], path: Tuple[str, ...]) -> Any:
    node: Any = data
    for key in path:
        node = node[key]
    return node


def _has_path(data: Dict[str, Any], path: Tuple[str, ...]) -> bool:
    node: Any = data
    for key in path:
        if key not in node:
            return False
        node = node[key]
    return True


def _set_by_path(data: Dict[str, Any], path: Tuple[str, ...], value: Any) -> None:
    node: Any = data
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value


def _extract_defaults(workflow: Dict[str, Any], field_paths: Dict[str, Tuple[str, ...]]) -> Dict[str, Any]:
    defaults: Dict[str, Any] = {}
    for field, path in field_paths.items():
        if _has_path(workflow, path):
            defaults[field] = _get_by_path(workflow, path)
    return defaults


WORKFLOW_CONFIGS: Dict[str, WorkflowConfig] = {
    "illustrious": WorkflowConfig(
        name="illustrious",
        filename="illustrious.json",
        field_paths={
            "positive": ("12", "inputs", "text"),
            "negative": ("7", "inputs", "text"),
            "seed": ("3", "inputs", "seed"),
        },
    ),
}

workflow_manager = WorkflowManager(WORKFLOW_CONFIGS, DEFAULT_WORKFLOW_NAME)


def get_available_workflows() -> List[str]:
    """List the workflow names that are currently configured."""
    return workflow_manager.list_workflows()


def get_active_workflow() -> str:
    """Return the active workflow name."""
    return workflow_manager.get_active()


def set_active_workflow(workflow_name: str) -> None:
    """Switch the active workflow."""
    workflow_manager.set_active(workflow_name)


def get_workflow_defaults(name: Optional[str] = None) -> Dict[str, Any]:
    """Expose defaults for callers that need to inspect workflow parameters."""
    return workflow_manager.get_defaults(name)

# ---------- HTTP helpers ----------

def http_post_json(url: str, payload: dict, timeout: int = 120) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    # best-effort parse (ComfyUI returns JSON)
    return json.loads(body.decode("utf-8")) if body else {}

def http_get_json(url: str, timeout: int = 60) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        body = resp.read()
    return json.loads(body.decode("utf-8")) if body else {}

# ---------- ComfyUI-specific calls ----------

def queue_prompt(prompt: dict, prompt_id: str) -> None:
    """POST the workflow to /prompt (no websocket)."""
    url = f"http://{server_address}/prompt"
    payload = {"prompt": prompt, "client_id": client_id, "prompt_id": prompt_id}
    # We don't strictly need the response here, but parsing helps surface errors.
    _ = http_post_json(url, payload)

def get_history(prompt_id: str) -> dict:
    """Fetch /history/{prompt_id}."""
    url = f"http://{server_address}/history/{prompt_id}"
    return http_get_json(url)

def get_image(filename: str, subfolder: str, folder_type: str) -> bytes:
    """Fetch binary image data via /view."""
    params = urllib.parse.urlencode(
        {"filename": filename, "subfolder": subfolder, "type": folder_type}
    )
    url = f"http://{server_address}/view?{params}"
    with urllib.request.urlopen(url, timeout=120) as resp:
        return resp.read()

def wait_until_done(prompt_id: str, poll_interval: float = 1.0, max_wait: int = 600) -> dict:
    """
    Poll /history/{prompt_id} until execution is finished or timeout.
    Returns the history dict for this prompt_id.
    """
    start = time.time()
    last = None
    while True:
        # /history returns a dict keyed by prompt_id
        hist_all = get_history(prompt_id)
        if prompt_id in hist_all:
            last = hist_all[prompt_id]

            # Heuristics to detect completion:
            # - Many ComfyUI builds add status info, but a portable check is:
            #   outputs exist AND at least one node has "images".
            outputs = last.get("outputs", {})
            if outputs:
                any_images = any("images" in node for node in outputs.values())
                if any_images:
                    return last

            # Some installs include a finishing flag:
            # status = last.get("status", {})
            # if status.get("completed") is True: return last

        if time.time() - start > max_wait:
            raise TimeoutError(f"Prompt {prompt_id} did not finish within {max_wait}s")

        time.sleep(poll_interval)

# ---------- Your public API ----------

def update_workflow(
    positive_text: Optional[str],
    negative_text: Optional[str],
    seed: Optional[int],
) -> Dict[str, Any]:
    """Wrapper around workflow manager for backward compatibility."""
    return workflow_manager.build_workflow(
        positive=positive_text,
        negative=negative_text,
        seed=seed,
    )

def generate_images(
    positive_text,
    negative_text: Optional[str] = None,
    seed: Optional[int] = None
) -> Dict[str, List[bytes]]:
    """
    Submit the workflow, poll until done, then fetch images grouped by node_id.
    Returns: { node_id: [image_bytes, ...], ... }
    """

    workflow = update_workflow(
        positive_text=positive_text,
        negative_text=negative_text,
        seed=seed,
    )

    prompt_id = str(uuid.uuid4())
    queue_prompt(workflow, prompt_id)

    # Poll /history until finished
    history_entry = wait_until_done(prompt_id)

    # Download all produced images
    output_images: Dict[str, List[bytes]] = {}
    outputs = history_entry.get("outputs", {})
    for node_id, node_output in outputs.items():
        images_output: List[bytes] = []
        for image in node_output.get("images", []):
            img = get_image(image["filename"], image["subfolder"], image["type"])
            images_output.append(img)
        if images_output:
            output_images[node_id] = images_output

    return output_images

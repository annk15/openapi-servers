# No websockets needed: POST prompt -> poll /history -> fetch images via /view

import uuid
import json
import time
import urllib.request
import urllib.parse
from typing import Dict, List, Optional

server_address = "192.168.100.143:8188"
client_id = str(uuid.uuid4())

DEFAULT_PROMPT_TEXT = r"""
{
  "3": {
    "inputs": {
      "seed": 223279903950754,
      "steps": 20,
      "cfg": 5.5,
      "sampler_name": "res_2s",
      "scheduler": "beta57",
      "denoise": 1,
      "model": [
        "10",
        0
      ],
      "positive": [
        "6",
        0
      ],
      "negative": [
        "7",
        0
      ],
      "latent_image": [
        "5",
        0
      ]
    },
    "class_type": "KSampler",
    "_meta": {
      "title": "KSampler"
    }
  },
  "4": {
    "inputs": {
      "ckpt_name": "waiNSFWIllustrious_v150.safetensors"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "Load Checkpoint"
    }
  },
  "5": {
    "inputs": {
      "width": 832,
      "height": 1216,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage",
    "_meta": {
      "title": "Empty Latent Image"
    }
  },
  "6": {
    "inputs": {
      "text": [
        "15",
        0
      ],
      "clip": [
        "10",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "7": {
    "inputs": {
      "text": "embedding:lazyneg",
      "clip": [
        "10",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "8": {
    "inputs": {
      "samples": [
        "3",
        0
      ],
      "vae": [
        "4",
        2
      ]
    },
    "class_type": "VAEDecode",
    "_meta": {
      "title": "VAE Decode"
    }
  },
  "9": {
    "inputs": {
      "filename_prefix": "ComfyUI",
      "images": [
        "8",
        0
      ]
    },
    "class_type": "SaveImage",
    "_meta": {
      "title": "Save Image"
    }
  },
  "10": {
    "inputs": {
      "PowerLoraLoaderHeaderWidget": {
        "type": "PowerLoraLoaderHeaderWidget"
      },
      "lora_1": {
        "on": true,
        "lora": "ILLMythP0rtr4itStyle.safetensors",
        "strength": 0.9
      },
      "lora_2": {
        "on": true,
        "lora": "JMoxComix_style-12.safetensors",
        "strength": 0.8
      },
      "lora_3": {
        "on": true,
        "lora": "Dramatic Lighting Slider.safetensors",
        "strength": 2.2
      },
      "lora_4": {
        "on": false,
        "lora": "JAB_Illustrious_V1.5.safetensors",
        "strength": 0.4
      },
      "➕ Add Lora": "",
      "model": [
        "4",
        0
      ],
      "clip": [
        "4",
        1
      ]
    },
    "class_type": "Power Lora Loader (rgthree)",
    "_meta": {
      "title": "Power Lora Loader (rgthree)"
    }
  },
  "12": {
    "inputs": {
      "text": "Create an alluring illustration of a naked woman with feline-inspired features, including large, human-like paws. She should have pointed ears and a long, flowing tail, all accentuating her seductive and playful nature. The scene should be bathed in soft, warm lighting, highlighting her curves and the sensuality of her pose. The background should be minimalistic, allowing the focus to remain on her captivating form"
    },
    "class_type": "Text Multiline",
    "_meta": {
      "title": "dynamicInput"
    }
  },
  "13": {
    "inputs": {
      "text": "embedding:lazypos,JmoxComic,mythp0rt"
    },
    "class_type": "Text Multiline",
    "_meta": {
      "title": "staticInput"
    }
  },
  "15": {
    "inputs": {
      "delimiter": "comma",
      "text1": [
        "13",
        0
      ],
      "text2": [
        "12",
        0
      ]
    },
    "class_type": "Text Concatenate (JPS)",
    "_meta": {
      "title": "Text Concatenate (JPS)"
    }
  },
  "18": {
    "inputs": {
      "text": "embedding:lazypos,JmoxComic,mythp0rt, Create an alluring illustration of a naked woman with feline-inspired features, including large, human-like paws. She should have pointed ears and a long, flowing tail, all accentuating her seductive and playful nature. The scene should be bathed in soft, warm lighting, highlighting her curves and the sensuality of her pose. The background should be minimalistic, allowing the focus to remain on her captivating form",
      "anything": [
        "15",
        0
      ]
    },
    "class_type": "easy showAnything",
    "_meta": {
      "title": "Show Any"
    }
  }
}
"""

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

def update_workflow(positive_text: str, negative_text: str, seed: int) -> dict:
    """
    Return a prompt dictionary with optional overrides.
    (Modify below to actually apply your overrides if desired.)
    """
    workflow = json.loads(DEFAULT_PROMPT_TEXT)
    # Example if you want to override:
    workflow["12"]["inputs"]["text"] = positive_text
    workflow["7"]["inputs"]["text"] = negative_text
    workflow["3"]["inputs"]["seed"] = seed
    return workflow

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
        positive_text,
        negative_text if negative_text is not None else negative_default,
        seed if seed is not None else seed_default,
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

#This is an example that uses the websockets api to know when a prompt execution is done
#Once the prompt execution is done it downloads the images using the /history endpoint

import websocket  # NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import uuid
import json
import urllib.request
import urllib.parse
from typing import Dict, List, Optional

server_address = "192.168.100.143:8188"
client_id = str(uuid.uuid4())

DEFAULT_PROMPT_TEXT = """
{
  "3": {
    "inputs": {
      "seed": 305025891131221,
      "steps": 20,
      "cfg": 6,
      "sampler_name": "euler_ancestral",
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
      "ckpt_name": "waiNSFWIllustrious_v130.safetensors"
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
        "11",
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
      "text": "low quality, worst quality, lowres, username, sketch, censor, blurry, distorted, bad anatomy, signature, watermark, patreon logo, artist name",
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
        "strength": 0.7
      },
      "lora_3": {
        "on": true,
        "lora": "Dramatic Lighting Slider.safetensors",
        "strength": 2.2
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
  "11": {
    "inputs": {
      "separator": ",",
      "text_1": [
        "12",
        0
      ],
      "text_2": [
        "13",
        0
      ]
    },
    "class_type": "TextConcatenate",
    "_meta": {
      "title": "TextConcatenate"
    }
  },
  "12": {
    "inputs": {
      "text": "1girl, solo, succubus, demon girl, flirty, red eyes, medium breasts, black bikini, long black hair, small curved horns, bat wings, glowing purple aura, seductive gaze, tentacles, tentacle on breasts, tentacle between breasts, underwater, hentai style"
    },
    "class_type": "Text Multiline",
    "_meta": {
      "title": "dynamicInput"
    }
  },
  "13": {
    "inputs": {
      "text": "JmoxComic,mythp0rt, masterpiece, best quality, amazing quality, ultra-detailed, highly detailed\n\n"
    },
    "class_type": "Text Multiline",
    "_meta": {
      "title": "staticInput"
    }
  }
}
"""

def queue_prompt(prompt, prompt_id):
    p = {"prompt": prompt, "client_id": client_id, "prompt_id": prompt_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request("http://{}/prompt".format(server_address), data=data)
    urllib.request.urlopen(req).read()

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen("http://{}/view?{}".format(server_address, url_values)) as response:
        return response.read()

def get_history(prompt_id):
    with urllib.request.urlopen("http://{}/history/{}".format(server_address, prompt_id)) as response:
        return json.loads(response.read())

def get_images(ws, prompt):
    prompt_id = str(uuid.uuid4())
    queue_prompt(prompt, prompt_id)
    output_images = {}
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break #Execution is done
        else:
            # If you want to be able to decode the binary stream for latent previews, here is how you can do it:
            # bytesIO = BytesIO(out[8:])
            # preview_image = Image.open(bytesIO) # This is your preview in PIL image format, store it in a global
            continue #previews are binary data

    history = get_history(prompt_id)[prompt_id]
    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        images_output = []
        if 'images' in node_output:
            for image in node_output['images']:
                image_data = get_image(image['filename'], image['subfolder'], image['type'])
                images_output.append(image_data)
        output_images[node_id] = images_output

    return output_images

def build_prompt(positive_text: str = "masterpiece best quality man", seed: int = 5) -> dict:
    """Return a prompt dictionary with optional overrides."""
    prompt = json.loads(DEFAULT_PROMPT_TEXT)
    """prompt["6"]["inputs"]["text"] = positive_text
    prompt["3"]["inputs"]["seed"] = seed"""
    return prompt

def generate_images(positive_text: Optional[str] = None, seed: Optional[int] = None) -> Dict[str, List[bytes]]:
    """Trigger a prompt execution and return generated images grouped by node."""
    prompt = build_prompt(
        positive_text if positive_text is not None else "masterpiece best quality man",
        seed if seed is not None else 5,
    )
    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(server_address, client_id))
    try:
        images = get_images(ws, prompt)
    finally:
        ws.close()
    return images

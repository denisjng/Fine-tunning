# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["torch", "transformers>=4.57", "peft", "accelerate", "safetensors", "flash-linear-attention", "huggingface_hub"]
# ///
"""Réduit l'intensité d'un adapter (lora_B × s, config inchangée), pousse le résultat en privé puis lance le
vérificateur officiel dessus. Usage : ... scale_adapter.py /lora/<run>/lora <s> <nom_sortie>"""
import shutil, subprocess, sys
from pathlib import Path
from safetensors.torch import load_file, save_file
from huggingface_hub import HfApi

src, s, name = Path(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
out = Path("/tmp") / name
out.mkdir(parents=True, exist_ok=True)
w = load_file(src / "adapter_model.safetensors")
n = 0
for k in w:
    if "lora_B" in k:
        w[k] = (w[k].float() * s).to(w[k].dtype); n += 1
assert n and all("lora_" in k for k in w), "adapter inattendu"
save_file(w, out / "adapter_model.safetensors", metadata={"format": "pt"})
shutil.copy(src / "adapter_config.json", out / "adapter_config.json")
print(f"lora_B × {s} sur {n} tenseurs", flush=True)
HfApi().upload_folder(folder_path=str(out), repo_id="denisjng/hackathon-lora", path_in_repo=f"{name}/lora", commit_message=f"{src} × {s}")
r = subprocess.run([sys.executable, "/work/verifier_mon_lora.py", str(out)], capture_output=True, text=True)
print(r.stdout[-3000:], r.stderr[-1500:] if r.returncode else "", flush=True)
print("SCALE_DONE", name, "verif_exit", r.returncode)

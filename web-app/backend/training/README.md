# Training the THOTH vision models

These scripts reproduce the vision team's two final classifiers as **clean,
runnable Python** — no Colab glue, no manual uploads. Source notebooks live
in `image-processing/` and stay untouched (that folder is the team's
territory, same rule as `simulation/`).

Both architectures and hyperparameters mirror the team's notebooks exactly,
so when training finishes the saved weights drop straight into our backend
via `app/services/vision_service.py` without any "translation" layer.

| What | Source notebook | Architecture | Output file |
|---|---|---|---|
| Age (4 groups) | `image-processing/age-recognition/full project.ipynb` | ResNet50 (ImageNet) + 4-way head, head-only fine-tuning | `models/age_resnet50.pth` |
| Emotion (7 classes) | `image-processing/emotion-recognition/Code.ipynb` | EfficientNet-B0, `features[6:]` unfrozen, 7-way head | `models/emotion_efficientnet.pth` |

---

## 1. Prereqs (one-time)

### Kaggle API key
Both datasets come from Kaggle via `kagglehub`. You need an API token:

1. Sign in at <https://www.kaggle.com>
2. Account → **Create New API Token** — downloads `kaggle.json`
3. Put it where `kagglehub` looks for it:
   - Windows: `C:\Users\<you>\.kaggle\kaggle.json`
   - Linux/macOS: `~/.kaggle/kaggle.json` (then `chmod 600 ~/.kaggle/kaggle.json`)

### Python env (separate from the runtime backend venv)

The training stack is heavy and we don't want it in the runtime venv. Make
a fresh one:

**Windows (PowerShell):**
```powershell
cd web-app\backend
python -m venv .venv-train
.venv-train\Scripts\activate

# 1. PyTorch FIRST with the right CUDA build.
#    Pick ONE line based on your driver (check `nvidia-smi`):
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
# or CPU-only fallback:
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 2. Then the rest:
pip install -r training\requirements.txt
```

**Ubuntu:**
```bash
cd web-app/backend
python3 -m venv .venv-train
source .venv-train/bin/activate

pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r training/requirements.txt
```

Verify the GPU is visible:
```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else '-')"
```

---

## 2. Train

From `web-app/backend/` with the training venv active:

```bash
python -m training.train_age_resnet
python -m training.train_emotion_efficientnet
```

Each script:
1. Downloads its dataset (cached after first run — subsequent runs are instant)
2. Trains, prints per-epoch metrics, saves the best-validation weights
3. Evaluates on a held-out test split and prints final accuracy
4. Writes the `.pth` + a `.meta.json` (class names, input transforms) to `web-app/backend/models/`

### Expected runtimes (RTX/T4-class GPU)

| Script | Dataset | Epochs | GPU time | CPU time |
|---|---|---|---|---|
| `train_age_resnet` | UTKFace ~23k images | 20 | ~15 min | ~3 h |
| `train_emotion_efficientnet` | FER2013 ~36k images | up to 30 | ~30 min | ~6 h |

### Expected accuracy (rough — same as the team's notebooks)

- **Age**: val accuracy 70-78%, mostly limited by the Child vs Teen boundary
- **Emotion**: val accuracy 65-68% on FER2013 (this is the SOTA range for the FER2013 benchmark; the dataset itself is noisy)

If you see numbers significantly lower than that, something is off — open the
training script and check the dataset path / class counts printed during step
2-of-5.

---

## 3. What the scripts produce

After both finish, `web-app/backend/models/` looks like:

```
models/
├── age_resnet50.pth                  # ~94 MB
├── age_resnet50.meta.json
├── emotion_efficientnet.pth          # ~17 MB
└── emotion_efficientnet.meta.json
```

The `.pth` files are git-ignored (too large for the repo). They live only on
the machine that runs the backend — copy them when deploying to another host.

The `.meta.json` files are tiny and CAN be committed if you want to track
which version of the training produced which weights.

---

## 4. After training

Nothing else to do — when the backend boots,
`app/services/vision_service.py` will find these `.pth` files automatically
and start serving `/api/vision/analyze`. If a `.pth` is missing the vision
endpoints just return 503 instead of crashing the backend.

---

## 5. Re-training

Edit hyperparameters at the top of each script, delete the old `.pth`, and
re-run. Dataset stays cached in `~/.cache/kagglehub/` (Linux) or
`%LOCALAPPDATA%\kagglehub\` (Windows) so re-downloads are skipped.

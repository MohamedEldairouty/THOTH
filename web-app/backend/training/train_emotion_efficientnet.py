"""
Train the emotion classifier the way the vision team did in
image-processing/emotion-recognition/Code.ipynb — cleaned for local
execution, no Colab glue.

Architecture (matches the team's final tuned run):
  - EfficientNet-B0 backbone (ImageNet pretrained, from torchvision)
  - Freeze: features[0..5] frozen, features[6:] trainable
  - Head: Dropout(0.5) → Linear(in_features, 7)
  - Augmentation: random hflip, ±15° rotation, slight affine + color jitter
  - Optimizer: AdamW(lr=5e-5, weight_decay=1e-4)
  - Loss: CrossEntropyLoss with label_smoothing=0.1
  - Sampler: WeightedRandomSampler (inverse class frequency)
  - 30 epochs, early-stop patience=3 on best val acc

Dataset:
  - FER2013 (35,887 48×48 grayscale faces, 7 classes)
  - Downloaded via kagglehub from `msambare/fer2013`
  - FER2013 ships as class subfolders under `train/` and `test/` — we
    use train/ for train+val (split 85/15) and test/ for the held-out set.

Output:
  web-app/backend/models/emotion_efficientnet.pth        ← state_dict
  web-app/backend/models/emotion_efficientnet.meta.json  ← class names + transforms

Run from web-app/backend/:
    python -m training.train_emotion_efficientnet
"""
from __future__ import annotations

import json
import os
import time
from copy import deepcopy
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from PIL import Image
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision import models, transforms
from tqdm import tqdm

import kagglehub


# ─────────────────────────────────────────────────────────────────────────
# Config (matches team's "Final Tuned EfficientNet-B0" experiment)
# ─────────────────────────────────────────────────────────────────────────

SEED         = 42
IMG_SIZE     = 224
BATCH_SIZE   = 32
NUM_EPOCHS   = 30
LR           = 5e-5
WEIGHT_DECAY = 1e-4
DROPOUT      = 0.5
PATIENCE     = 3
NUM_CLASSES  = 7
VAL_SPLIT    = 0.15   # of the train folder
LABEL_SMOOTHING = 0.1

# FER2013 class labels, in the order used by the dataset (alphabetical by
# folder name = the order torchvision's ImageFolder would assign).
# IMPORTANT: this MUST match the order the trained weights' final Linear
# layer encodes — don't reorder.
CLASS_NAMES = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]

NORM_MEAN = [0.485, 0.456, 0.406]
NORM_STD  = [0.229, 0.224, 0.225]

BACKEND_DIR  = Path(__file__).resolve().parent.parent
MODELS_DIR   = BACKEND_DIR / "models"
WEIGHTS_PATH = MODELS_DIR / "emotion_efficientnet.pth"
META_PATH    = MODELS_DIR / "emotion_efficientnet.meta.json"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ─────────────────────────────────────────────────────────────────────────
# 1. Dataset — FER2013 from class subfolders
# ─────────────────────────────────────────────────────────────────────────

class FER2013FolderDataset(Dataset):
    """FER2013 as 7 class subfolders (Kaggle `msambare/fer2013` layout)."""

    def __init__(self, root: Path, class_to_idx: dict[str, int], transform):
        self.transform = transform
        self.samples: list[tuple[str, int]] = []
        for cls_name, idx in class_to_idx.items():
            cls_dir = root / cls_name
            if not cls_dir.is_dir():
                continue
            for fname in os.listdir(cls_dir):
                if fname.lower().endswith((".jpg", ".jpeg", ".png")):
                    self.samples.append((str(cls_dir / fname), idx))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("L")   # grayscale
        return self.transform(img), label


def build_transforms():
    train_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.Grayscale(num_output_channels=3),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(15),
        transforms.RandomAffine(degrees=0, translate=(0.08, 0.08), scale=(0.95, 1.05)),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize(NORM_MEAN, NORM_STD),
    ])
    eval_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.Grayscale(num_output_channels=3),
        transforms.ToTensor(),
        transforms.Normalize(NORM_MEAN, NORM_STD),
    ])
    return train_tf, eval_tf


# ─────────────────────────────────────────────────────────────────────────
# 2. Model — EfficientNet-B0 (features[6:] trainable, custom head)
# ─────────────────────────────────────────────────────────────────────────

def build_model() -> nn.Module:
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.IMAGENET1K_V1)
    # Freeze early blocks
    for p in model.parameters():
        p.requires_grad = False
    # Unfreeze the last feature block (features[6:])
    for p in model.features[6:].parameters():
        p.requires_grad = True
    # Custom head
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(DROPOUT),
        nn.Linear(in_features, NUM_CLASSES),
    )
    return model.to(DEVICE)


# ─────────────────────────────────────────────────────────────────────────
# 3. Training loop with early stopping + class-balanced sampler
# ─────────────────────────────────────────────────────────────────────────

def run_epoch(model, loader, criterion, optimizer=None):
    is_train = optimizer is not None
    model.train(is_train)
    total_loss, correct, total = 0.0, 0, 0
    for imgs, labels in tqdm(loader, leave=False,
                             desc="train" if is_train else "val"):
        imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
        if is_train:
            optimizer.zero_grad()
        with torch.set_grad_enabled(is_train):
            logits = model(imgs)
            loss   = criterion(logits, labels)
            if is_train:
                loss.backward()
                optimizer.step()
        total_loss += loss.item() * imgs.size(0)
        correct    += (logits.argmax(1) == labels).sum().item()
        total      += imgs.size(0)
    return total_loss / total, correct / total


def train(model, train_loader, val_loader):
    criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
    optimizer = optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LR, weight_decay=WEIGHT_DECAY,
    )

    best_acc   = 0.0
    best_state = None
    stale      = 0
    history    = []

    for epoch in range(1, NUM_EPOCHS + 1):
        t0 = time.time()
        tr_loss, tr_acc = run_epoch(model, train_loader, criterion, optimizer)
        vl_loss, vl_acc = run_epoch(model, val_loader,   criterion)
        history.append({"epoch": epoch, "train_loss": tr_loss, "train_acc": tr_acc,
                        "val_loss": vl_loss, "val_acc": vl_acc})
        print(f"Epoch {epoch:02d}/{NUM_EPOCHS}  "
              f"train_loss={tr_loss:.4f} train_acc={tr_acc:.4f}  |  "
              f"val_loss={vl_loss:.4f} val_acc={vl_acc:.4f}  "
              f"({time.time()-t0:.1f}s)")
        if vl_acc > best_acc:
            best_acc   = vl_acc
            best_state = deepcopy(model.state_dict())
            stale      = 0
            print(f"   ✓ new best val_acc={best_acc:.4f}")
        else:
            stale += 1
            if stale >= PATIENCE:
                print(f"   ⏹ early-stop after {PATIENCE} epochs without improvement")
                break

    return best_state, best_acc, history


# ─────────────────────────────────────────────────────────────────────────
# 4. Main
# ─────────────────────────────────────────────────────────────────────────

def main():
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    print(f"Device: {DEVICE}")
    if DEVICE.type == "cuda":
        print(f"GPU:    {torch.cuda.get_device_name(0)}")

    print("\n[1/5] Downloading FER2013 (cached after first run)…")
    dataset_root = Path(kagglehub.dataset_download("msambare/fer2013"))
    # Expect `train/` and `test/` subfolders
    train_root = dataset_root / "train"
    test_root  = dataset_root / "test"
    if not train_root.is_dir() or not test_root.is_dir():
        # Some snapshots nest under an extra folder; try to find it.
        for sub in dataset_root.iterdir():
            if (sub / "train").is_dir() and (sub / "test").is_dir():
                train_root = sub / "train"
                test_root  = sub / "test"
                break
    if not train_root.is_dir() or not test_root.is_dir():
        raise RuntimeError(
            f"Couldn't find train/ and test/ under {dataset_root}. "
            "Check the kaggle dataset layout."
        )
    print(f"   train_root = {train_root}")
    print(f"   test_root  = {test_root}")

    class_to_idx = {name: idx for idx, name in enumerate(CLASS_NAMES)}
    print(f"   class_to_idx = {class_to_idx}")

    print("\n[2/5] Building datasets…")
    train_tf, eval_tf = build_transforms()
    full_train_ds = FER2013FolderDataset(train_root, class_to_idx, train_tf)
    test_ds       = FER2013FolderDataset(test_root,  class_to_idx, eval_tf)

    # Stratified val split off the train folder
    indices = np.arange(len(full_train_ds))
    labels  = np.array([s[1] for s in full_train_ds.samples])
    rng     = np.random.default_rng(SEED)
    val_indices = []
    for c in range(NUM_CLASSES):
        cls_idx = indices[labels == c]
        n_val   = int(round(len(cls_idx) * VAL_SPLIT))
        chosen  = rng.choice(cls_idx, size=n_val, replace=False)
        val_indices.extend(chosen.tolist())
    val_mask  = np.zeros(len(full_train_ds), dtype=bool)
    val_mask[val_indices] = True

    # Build true train + val subsets (val uses eval_tf, not train_tf)
    train_samples = [s for i, s in enumerate(full_train_ds.samples) if not val_mask[i]]
    val_samples   = [s for i, s in enumerate(full_train_ds.samples) if val_mask[i]]

    class _SubsetDS(Dataset):
        def __init__(self, samples, transform):
            self.samples = samples
            self.transform = transform
        def __len__(self): return len(self.samples)
        def __getitem__(self, idx):
            path, label = self.samples[idx]
            return self.transform(Image.open(path).convert("L")), label

    train_ds = _SubsetDS(train_samples, train_tf)
    val_ds   = _SubsetDS(val_samples,   eval_tf)
    print(f"   train={len(train_ds)}  val={len(val_ds)}  test={len(test_ds)}")

    # Weighted sampler for class imbalance
    train_labels  = np.array([s[1] for s in train_samples])
    class_counts  = np.bincount(train_labels, minlength=NUM_CLASSES)
    class_weights = 1.0 / class_counts
    sample_weights = class_weights[train_labels]
    sampler = WeightedRandomSampler(
        weights=sample_weights.tolist(),
        num_samples=len(train_samples),
        replacement=True,
    )
    print(f"   class_counts = {class_counts.tolist()}")

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, sampler=sampler,
                              num_workers=2, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,
                              num_workers=2, pin_memory=True)
    test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False,
                              num_workers=2, pin_memory=True)

    print("\n[3/5] Building model (EfficientNet-B0, features[6:] unfrozen)…")
    model = build_model()
    n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    n_total = sum(p.numel() for p in model.parameters())
    print(f"   trainable params: {n_train:,} / {n_total:,}")

    print(f"\n[4/5] Training for up to {NUM_EPOCHS} epochs (patience={PATIENCE})…\n")
    best_state, best_val_acc, history = train(model, train_loader, val_loader)

    print("\n[5/5] Evaluating best weights on held-out test set…")
    model.load_state_dict(best_state)
    criterion = nn.CrossEntropyLoss()
    test_loss, test_acc = run_epoch(model, test_loader, criterion)
    print(f"   test_loss={test_loss:.4f}  test_acc={test_acc:.4f}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, WEIGHTS_PATH)
    META_PATH.write_text(json.dumps({
        "framework":        "pytorch",
        "architecture":     "torchvision/efficientnet_b0",
        "img_size":         IMG_SIZE,
        "num_classes":      NUM_CLASSES,
        "class_names":      CLASS_NAMES,
        "normalize_mean":   NORM_MEAN,
        "normalize_std":    NORM_STD,
        "input_channels":   3,
        "input_is_grayscale_upcast": True,
        "best_val_acc":     best_val_acc,
        "test_acc":         test_acc,
        "epochs_trained":   len(history),
        "training_history": history,
    }, indent=2))

    print(f"\n✓ Saved weights → {WEIGHTS_PATH}")
    print(f"✓ Saved meta    → {META_PATH}")
    print(f"  best val_acc  = {best_val_acc:.4f}")
    print(f"  test_acc      = {test_acc:.4f}")


if __name__ == "__main__":
    main()

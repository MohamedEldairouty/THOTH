"""
Train the age classifier the way the vision team did in
image-processing/age-recognition/full project.ipynb — but as a clean,
runnable Python script with no Colab-specific glue.

Architecture:
  - ResNet50 backbone (ImageNet-pretrained, from timm)
  - Head: Dropout(0.4) → Linear(2048, 4)
  - Freeze strategy: classifier_only (only the head trains)
  - Loss: CrossEntropyLoss with class weights
  - Optimizer: Adam, lr=1e-4
  - ReduceLROnPlateau (factor=0.5, patience=3)
  - 20 epochs, save best by val accuracy

Dataset:
  - UTKFace, downloaded via kagglehub (jangedoo/utkface-new)
  - Labels parsed from filename `{age}_{gender}_{race}_{timestamp}.jpg`
  - 4 age groups: 0=Child(0-12), 1=Teen(13-19), 2=Adult(20-50), 3=Elderly(51+)
  - 70/15/15 stratified split

Output:
  web-app/backend/models/age_resnet50.pth     ← state_dict
  web-app/backend/models/age_resnet50.meta.json ← class names + transform info

Run from web-app/backend/ with the training venv activated:
    python -m training.train_age_resnet
"""
from __future__ import annotations

import json
import os
import time
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from PIL import Image
from sklearn.model_selection import train_test_split
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from tqdm import tqdm

import timm
import kagglehub


# ─────────────────────────────────────────────────────────────────────────
# Config (matches the team's notebook)
# ─────────────────────────────────────────────────────────────────────────

SEED            = 42
IMG_SIZE        = 224
BATCH_SIZE      = 32
NUM_EPOCHS      = 20
LR              = 1e-4
DROPOUT         = 0.4
FREEZE_STRATEGY = "classifier_only"   # only head trains; matches team's pick
NUM_CLASSES     = 4
WEIGHT_DECAY    = 0.0                 # Adam without WD (team's choice)

# Label assignment — taken verbatim from full project.ipynb cell 2.
# Index = class id, value = human-readable label. The trained .pth file
# encodes this order in its final Linear layer, so DO NOT REORDER.
CLASS_NAMES = ["Child (0-12)", "Teenager (13-19)", "Adult (20-50)", "Elderly (51+)"]
# Maps each class id to the slug we use across the rest of the backend.
AGE_GROUP_SLUGS = ["child", "teen", "adult", "senior"]

# ImageNet normalisation — matches the team's val_transform in cell 16
# (the cell 3 mention of 0.5/0.5/0.5 was a typo per their own inference
# code which uses ImageNet stats).
NORM_MEAN = [0.485, 0.456, 0.406]
NORM_STD  = [0.229, 0.224, 0.225]

# Paths
BACKEND_DIR   = Path(__file__).resolve().parent.parent
MODELS_DIR    = BACKEND_DIR / "models"
WEIGHTS_PATH  = MODELS_DIR / "age_resnet50.pth"
META_PATH     = MODELS_DIR / "age_resnet50.meta.json"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ─────────────────────────────────────────────────────────────────────────
# 1. Dataset
# ─────────────────────────────────────────────────────────────────────────

def age_to_label(age: int) -> int:
    if age <= 12:   return 0   # Child
    if age <= 19:   return 1   # Teen
    if age <= 50:   return 2   # Adult
    return 3                   # Elderly


def index_utkface(dataset_root: Path) -> pd.DataFrame:
    """Walk the UTKFace folder and build a dataframe of {filepath, age, label}.
    UTKFace filenames look like `25_0_0_20170109150557335.jpg` — age first."""
    rows = []
    for fname in os.listdir(dataset_root):
        if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        try:
            age = int(fname.split("_")[0])
        except (ValueError, IndexError):
            continue
        if not (1 <= age <= 100):
            continue
        rows.append({
            "filepath": str(dataset_root / fname),
            "age":      age,
            "label":    age_to_label(age),
        })
    return pd.DataFrame(rows)


class UTKFaceDataset(Dataset):
    def __init__(self, df: pd.DataFrame, transform):
        self.df        = df.reset_index(drop=True)
        self.transform = transform

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row   = self.df.iloc[idx]
        img   = Image.open(row["filepath"]).convert("RGB")
        return self.transform(img), int(row["label"])


def build_transforms():
    train_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(10),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize(NORM_MEAN, NORM_STD),
    ])
    eval_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(NORM_MEAN, NORM_STD),
    ])
    return train_tf, eval_tf


# ─────────────────────────────────────────────────────────────────────────
# 2. Model — ResNet50 with frozen backbone (team's `classifier_only`)
# ─────────────────────────────────────────────────────────────────────────

def build_model() -> nn.Module:
    model = timm.create_model("resnet50", pretrained=True, num_classes=0)
    in_features = model.num_features  # 2048
    model.fc = nn.Sequential(
        nn.Dropout(p=DROPOUT),
        nn.Linear(in_features, NUM_CLASSES),
    )
    # Freeze everything except the classifier head
    for name, p in model.named_parameters():
        p.requires_grad = "fc" in name
    return model.to(DEVICE)


# ─────────────────────────────────────────────────────────────────────────
# 3. Training loop
# ─────────────────────────────────────────────────────────────────────────

def run_epoch(model, loader, criterion, optimizer=None):
    is_train = optimizer is not None
    model.train(is_train)
    total_loss, correct, total = 0.0, 0, 0
    iterator = tqdm(loader, leave=False, desc="train" if is_train else "val")
    for imgs, labels in iterator:
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


def train(model, train_loader, val_loader, class_weights):
    criterion = nn.CrossEntropyLoss(weight=class_weights.to(DEVICE))
    optimizer = optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LR, weight_decay=WEIGHT_DECAY,
    )
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=3,
    )

    best_acc = 0.0
    best_state = None
    history = []

    for epoch in range(1, NUM_EPOCHS + 1):
        t0 = time.time()
        tr_loss, tr_acc = run_epoch(model, train_loader, criterion, optimizer)
        vl_loss, vl_acc = run_epoch(model, val_loader,   criterion)
        scheduler.step(vl_acc)
        history.append({"epoch": epoch, "train_loss": tr_loss, "train_acc": tr_acc,
                        "val_loss": vl_loss, "val_acc": vl_acc})
        print(f"Epoch {epoch:02d}/{NUM_EPOCHS}  "
              f"train_loss={tr_loss:.4f} train_acc={tr_acc:.4f}  |  "
              f"val_loss={vl_loss:.4f} val_acc={vl_acc:.4f}  "
              f"({time.time()-t0:.1f}s)")
        if vl_acc > best_acc:
            best_acc = vl_acc
            best_state = deepcopy(model.state_dict())
            print(f"   ✓ new best val_acc={best_acc:.4f}")

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

    print("\n[1/5] Downloading UTKFace (cached after first run)…")
    dataset_root = Path(kagglehub.dataset_download("jangedoo/utkface-new"))
    # UTKFace typically extracts to a subfolder named `UTKFace`
    cand = dataset_root / "UTKFace"
    if cand.is_dir():
        dataset_root = cand
    print(f"   Dataset at: {dataset_root}")

    print("\n[2/5] Indexing images & building splits…")
    df = index_utkface(dataset_root)
    print(f"   Total valid images: {len(df)}")
    print(df["label"].value_counts().sort_index().to_string())

    train_df, temp_df = train_test_split(df, test_size=0.30,
                                         random_state=SEED, stratify=df["label"])
    val_df, test_df = train_test_split(temp_df, test_size=0.50,
                                       random_state=SEED, stratify=temp_df["label"])
    print(f"   train={len(train_df)}  val={len(val_df)}  test={len(test_df)}")

    print("\n[3/5] Building model (ResNet50, classifier_only freeze)…")
    train_tf, eval_tf = build_transforms()
    train_ds = UTKFaceDataset(train_df, train_tf)
    val_ds   = UTKFaceDataset(val_df,   eval_tf)
    test_ds  = UTKFaceDataset(test_df,  eval_tf)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE,
                              shuffle=True,  num_workers=2, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE,
                              shuffle=False, num_workers=2, pin_memory=True)
    test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE,
                              shuffle=False, num_workers=2, pin_memory=True)

    model = build_model()

    # Class weights — inverse frequency on training set
    counts = train_df["label"].value_counts().sort_index().values
    n      = len(train_df)
    class_weights = torch.tensor(
        [n / (NUM_CLASSES * c) for c in counts], dtype=torch.float32
    )
    print("   class_weights:", class_weights.tolist())

    print(f"\n[4/5] Training for {NUM_EPOCHS} epochs…\n")
    best_state, best_val_acc, history = train(
        model, train_loader, val_loader, class_weights
    )

    # Final test eval
    print("\n[5/5] Evaluating best weights on held-out test set…")
    model.load_state_dict(best_state)
    criterion = nn.CrossEntropyLoss()
    test_loss, test_acc = run_epoch(model, test_loader, criterion)
    print(f"   test_loss={test_loss:.4f}  test_acc={test_acc:.4f}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, WEIGHTS_PATH)
    META_PATH.write_text(json.dumps({
        "framework":        "pytorch",
        "architecture":     "timm/resnet50",
        "freeze_strategy":  FREEZE_STRATEGY,
        "img_size":         IMG_SIZE,
        "num_classes":      NUM_CLASSES,
        "class_names":      CLASS_NAMES,
        "age_group_slugs":  AGE_GROUP_SLUGS,
        "normalize_mean":   NORM_MEAN,
        "normalize_std":    NORM_STD,
        "best_val_acc":     best_val_acc,
        "test_acc":         test_acc,
        "epochs_trained":   NUM_EPOCHS,
        "training_history": history,
    }, indent=2))

    print(f"\n✓ Saved weights → {WEIGHTS_PATH}")
    print(f"✓ Saved meta    → {META_PATH}")
    print(f"  best val_acc  = {best_val_acc:.4f}")
    print(f"  test_acc      = {test_acc:.4f}")


if __name__ == "__main__":
    main()

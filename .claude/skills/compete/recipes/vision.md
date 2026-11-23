# Recipe: images (classification, detection, segmentation)

## Use when
Inputs are images; output is a class, several labels, boxes (detection) or masks (segmentation).

## Pick the model
- If the rules fix the base model, use it. Otherwise spend ≤15 min on a day-of check: search the Hugging Face Hub and recent leaderboards for a newer model of the same kind and size; switch only if it fits the GPU, its license is allowed, and it loads with the installed libraries. Else use the defaults below.
- Classification default: timm `convnext_tiny.fb_in22k_ft_in1k` (Hub: `timm/convnext_tiny.fb_in22k_ft_in1k`). Bigger lever: `timm/convnext_base.fb_in22k_ft_in1k`.
- Very little data (<1k images): frozen `facebook/dinov2-base` features + a linear head.
- Detection: `PekingU/rtdetr_r50vd` (transformers). YOLO-family only if its license (AGPL) is allowed by the rules.
- Segmentation: `nvidia/segformer-b0-finetuned-ade-512-512`.
- Smallest fallback: convnext_tiny at image size 160, head-only training.

## Starting hyperparameters
- Classification: image size 224; AdamW lr 1e-4 full fine-tune (1e-3 head-only), weight_decay 0.05; batch 32–64; 10–20 epochs, cosine, keep best epoch by val metric; mixed precision.
- Augmentation: RandomResizedCrop + horizontal flip (no flip if orientation matters: text, digits, medical laterality).
- Detection: image size 640, lr 1e-4 (backbone 1e-5), 30–50 epochs.
- Segmentation: image size 512, AdamW lr 6e-5, batch 8, 40–80 epochs, keep the best epoch by val mIoU or Dice.

## Script outline
- `timm.create_model(name, pretrained=True, num_classes=K)`; normalization from `timm.data.resolve_data_config`; torchvision transforms; plain PyTorch loop or HF `Trainer`.
- Images: `Image.open(p).convert("RGB")`.
- Predict probabilities on test; average over TTA views if used.
- Detection / segmentation: `AutoImageProcessor` + `AutoModelForObjectDetection` / `AutoModelForSemanticSegmentation` with `Trainer`; apply every augmentation to the image and its boxes or masks together.

## Levers
1. Check labels ↔ images alignment, correct normalization and resize.
2. lr and epochs.
3. Higher resolution 224 → 384.
4. Bigger backbone.
5. Stronger augmentation (RandAugment, mixup/cutmix) when train ≫ val score.
6. TTA: average original + flipped predictions.
7. Ensemble two backbones.

## Crashes
- OOM → smaller batch → smaller images → AMP + `channels_last`.
- Slow data loading → `num_workers` 4–8; pre-resize all images once into `data/derived/`.
- Val great, LB bad → leakage (same object/patient/source in train and val) → group split.
- Wrong channel count → `.convert("RGB")`.
- Segmentation masks turn into invalid class ids → resize masks with nearest-neighbour interpolation, never bilinear.

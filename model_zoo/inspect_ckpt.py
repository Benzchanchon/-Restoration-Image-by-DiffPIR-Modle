import torch

ckpt = torch.load("ema_0.9999_000150.pt", map_location="cpu")
print(ckpt.keys())

if 'args' in ckpt:
    print("\nModel args:")
    print(ckpt['args'])

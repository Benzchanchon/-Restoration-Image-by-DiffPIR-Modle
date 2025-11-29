import cv2
import numpy as np
import os
import tkinter as tk
from tkinter import filedialog

rectangles = []
temp_rect = None
ix, iy = -1, -1
drawing = False
mask_result = None
zoom_scale = 1.0
should_exit = False  # ป้องกัน Tkinter crash หลัง Save&Exit

# ---------- Utilities ----------
#กรองจุด noise เล็ก ๆ ออกจาก mask
def _cc_filter(mask, min_area=0, keep_small=True):
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8) #แยกวัตถุที่ติดกัน
    keep = np.zeros_like(mask)

    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA] # ถ้าพื้นที่ส่วนที่เสียหายมากกว่าส่วนที่เสียหายน้อย จะเก็บ ตำแหน่ง pixel
        if area >= min_area:
            keep[labels == i] = 255
        elif keep_small:  # เก็บจุดเล็กไว้ด้วยถ้าสั่ง
            keep[labels == i] = 255

    return keep

def box_to_mask_threshold(img, box, min_area=40):
    x1, y1, x2, y2 = map(int, box)
    x1, x2 = sorted([x1, x2]); y1, y2 = sorted([y1, y2])
    crop = img[y1:y2, x1:x2]
    if crop.size == 0: 
        return np.zeros(img.shape[:2], np.uint8)

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    if np.mean(gray[thr == 255]) < np.mean(gray[thr == 0]):
        thr = cv2.bitwise_not(thr)

    thr = _cc_filter(thr, min_area=min_area)

    full = np.zeros(img.shape[:2], np.uint8)
    full[y1:y2, x1:x2] = thr
    return full

def box_to_mask_grabcut_full(img, box, iters=10, min_area=40):
    h, w = img.shape[:2]
    x1, y1, x2, y2 = map(int, box)
    x1, x2 = sorted([max(0, x1), min(w-1, x2)])
    y1, y2 = sorted([max(0, y1), min(h-1, y2)])

    if x2 - x1 < 2 or y2 - y1 < 2:
        return np.zeros((h, w), np.uint8)

    mask = np.zeros((h, w), np.uint8)
    rect = (x1, y1, x2 - x1, y2 - y1)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)

    try:
        cv2.grabCut(img, mask, rect, bgdModel, fgdModel, iters, cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        return box_to_mask_threshold(img, box, min_area=min_area)

    out = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    out = _cc_filter(out, min_area=min_area)

    roi = np.zeros((h, w), np.uint8); roi[y1:y2, x1:x2] = 255
    out = cv2.bitwise_and(out, roi) #bitwise=รวม
    return out

def soften_mask_edges(mask, ksize=15):
    blur = cv2.GaussianBlur(mask, (ksize, ksize), 0)
    soft = (blur > 10).astype(np.uint8) * 255
    return soft

#ฟังชันหลักที่ใช้app.py
def multi_box_auto_mask(img, boxes):
    h, w = img.shape[:2]
    final_mask = np.zeros((h, w), np.uint8)

    for (x1, y1, x2, y2) in boxes:
        area = abs((x2 - x1) * (y2 - y1))
        if (x2 - x1 < 40) or (y2 - y1 < 40):
            local = box_to_mask_threshold(img, (x1, y1, x2, y2), min_area=5)
        elif area > 200 * 200:
            local = box_to_mask_threshold(img, (x1, y1, x2, y2), min_area=10)
        else:
            local = box_to_mask_grabcut_full(img, (x1, y1, x2, y2), min_area=10)

        final_mask = cv2.bitwise_or(final_mask, local)

    final_mask = soften_mask_edges(final_mask, ksize=15)

    #กลับสี → วัตถุ = ดำ, BG = ขาว
    final_mask = cv2.bitwise_not(final_mask)

    return final_mask


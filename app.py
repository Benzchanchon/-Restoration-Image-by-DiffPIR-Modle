import os, io, base64, shutil, subprocess, sys
from flask import Flask, request, jsonify, send_from_directory, Response
from PIL import Image
import numpy as np
import cv2
import glob
import re, time, json, threading
import warnings
import math 
warnings.filterwarnings("ignore", category=UserWarning)
from auto_mask import multi_box_auto_mask   # ✅ auto-mask

app = Flask(__name__, static_folder="static", static_url_path="")

SAVE_DIR = "runtime"
MODEL_TEST_DIR = "testsets/demo_test"
os.makedirs(SAVE_DIR, exist_ok=True)

# ---------- Utils ----------
#แปลงภาพที่ส่งมาจากหน้าเว็บในรูปแบบ Base64
def dataurl_to_pil(data_url: str) -> Image.Image:
    header, encoded = data_url.split(",", 1)
    raw = base64.b64decode(encoded)
    return Image.open(io.BytesIO(raw))

#ตัดภาพ
def save_patches(img_np, mask_np,
                 dir_img, dir_mask,
                 prefix="patch", size=256, stride=256):
    h, w = img_np.shape[:2] #เก็บตำแหน่งของรูปภาพ
    os.makedirs(dir_img, exist_ok=True) #เซฟลงไฟล์
    os.makedirs(dir_mask, exist_ok=True)
    count = 0
    for y in range(0, h, stride):
        for x in range(0, w, stride):
            #ตัดจากตำแหน่งเริ่มต้นถึงตำแหน่ง+size
            img_patch  = img_np[y:y+size, x:x+size]
            mask_patch = mask_np[y:y+size, x:x+size]
            ph, pw = img_patch.shape[:2]
            #phคือความสูงของภาพที่ตัดได้ pwคือความกว้างที่ตัดได้
            if ph < size or pw < size: #ถ้าได้น้อยกว่า256*256 จะถูกเติมสีดำในบริเวณที่ขาดไป
                #เติมสีดำเข้าไป
                padded_img  = np.zeros((size, size, 3), dtype=img_np.dtype)
                padded_mask = np.zeros((size, size), dtype=mask_np.dtype)
                padded_img[:ph, :pw]  = img_patch #วาง patch ไว้จากมุมซ้ายบน
                padded_mask[:ph, :pw] = mask_patch
                img_patch, mask_patch = padded_img, padded_mask #ปรับค่าให้เป็นimgที่ถูกเติมสีดำแล้ว
            cv2.imwrite(os.path.join(dir_img,  f"{prefix}_{count+1:03d}.png"), img_patch)  #เซฟลงไฟล์
            cv2.imwrite(os.path.join(dir_mask, f"{prefix}_{count+1:03d}.png"), mask_patch) 
            count += 1
    return count, (h, w)

#รวมภาพ
def reassemble_patches_with_blending(patch_dir, full_size, size=256, stride=256):
    H, W = full_size[:2]
    canvas = np.zeros((H, W, 3), np.float32)
    weight = np.zeros((H, W, 3), np.float32)

    patch_files = glob.glob(os.path.join(patch_dir, "*.png"))

    def get_index_from_name(path):
        name = os.path.basename(path)
        m = re.search(r'(?:patch|result)_(\d+)', name)
        if m:
            return int(m.group(1))
        # ถ้าไม่แมตช์เลย ให้โยนไปท้าย ๆ
        return 10**9

    patch_files = sorted(patch_files, key=get_index_from_name)

    print(f"[DEBUG] use result folder: {patch_dir}, total {len(patch_files)} patches")

    ny = math.ceil((H - size) / stride) + 1
    nx = math.ceil((W - size) / stride) + 1

    for idx, pf in enumerate(patch_files):
        patch = cv2.imread(pf, cv2.IMREAD_COLOR)
        if patch is None:
            print(f"[WARN] cannot read patch: {pf}")
            continue
        patch = patch.astype(np.float32)

        row = idx // nx
        col = idx % nx
        y = row * stride
        x = col * stride

        h, w = patch.shape[:2]
        y2 = min(y + h, H)
        x2 = min(x + w, W)

        canvas[y:y2, x:x2] += patch[:(y2-y), :(x2-x), :]
        weight[y:y2, x:x2] += 1.0

    weight[weight == 0] = 1.0
    out = (canvas / weight).clip(0, 255).astype(np.uint8)
    return out


#ล้างโฟลเดอร์เก่าใน testset แล้วคัดลอกไฟล์ใหม่เข้าไป
def clear_and_copy(src_dir, dst_dir):
    if os.path.exists(dst_dir):
        shutil.rmtree(dst_dir)
    os.makedirs(dst_dir, exist_ok=True)
    for f in os.listdir(src_dir):
        shutil.copy(os.path.join(src_dir, f), dst_dir)

# ใช้โมเดล
def run_test_py():
    try:
        # ชี้โฟลเดอร์ input ให้โมเดลใช้ทำงาน
        abs_testset_dir = os.path.abspath(os.path.join(MODEL_TEST_DIR, "demotest"))
        abs_mask_dir    = os.path.abspath(os.path.join(MODEL_TEST_DIR, "gt_keep_masks"))

        # เรียก old_inpaint.py ให้รันโมเดล
        result = subprocess.run(
            [
                sys.executable,
                "old_inpaint.py",
                "--testset_dir", abs_testset_dir,
                "--mask_path",   abs_mask_dir
            ],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ old_inpaint.py output:", result.stdout)

        base_results = os.path.abspath(os.path.join("results", "result_image"))
        print(f"[DEBUG] expecting results in: {base_results}")

        # เช็คว่ามีไฟล์ result_*.pngไหม
        pngs = glob.glob(os.path.join(base_results, "result_*.png"))
        if not pngs:
            raise FileNotFoundError(f"[ERROR] No result_*.png found in {base_results}")

        return base_results

    except subprocess.CalledProcessError as e:
        print("❌ old_inpaint.py error:", e.stderr)
        raise RuntimeError(e.stderr)



#เคลียไฟล์เก่าก่อนหน้าออก
def clear_dir(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)

#อัพเดทprocess bar
progress_data = {"progress": 0, "elapsed": 0, "message": "", "start_time": None}
def update_progress(percent, message=""):
    global progress_data
    if progress_data["start_time"] is None:
        progress_data["start_time"] = time.time()
    elapsed = time.time() - progress_data["start_time"]
    progress_data["progress"] = percent #เปอร์เซ็นต์การทำงาน
    progress_data["elapsed"] = elapsed  #เวลาที่ผ่านไป
    progress_data["message"] = message  #ข้อความสถานะปัจจุบัน

#วัดค่าPSNR
#มันจะหาค่าmseมาก่อนจากนั้นค่อยไปใช้คำนวณPSNR
def calculate_psnr(img1, img2):
    mse = np.mean((img1.astype(np.float32) - img2.astype(np.float32)) ** 2)
    if mse == 0:
        return float("inf")
    PIXEL_MAX = 255.0
    return 20 * np.log10(PIXEL_MAX / np.sqrt(mse))

#เรียงลำดับการทำงาน
def run_pipeline(image_dataurl, rectangles):
    try:
        update_progress(5, "")
        # เคลียไฟล์เก่าออกก่อน
        clear_dir(os.path.join(SAVE_DIR, "patches_img"))
        clear_dir(os.path.join(SAVE_DIR, "patches_mask"))
        clear_dir(os.path.join(MODEL_TEST_DIR, "demotest"))
        clear_dir(os.path.join(MODEL_TEST_DIR, "gt_keep_masks"))
        clear_dir(os.path.join(MODEL_TEST_DIR, "demotest_ip_DiffPIR_random_ema_0.9999_750450_sigma0.0_NFE20_eta0.0_zeta1.0_lambda1.0"))

        # แปลง Base64 → รูปภาพ
        update_progress(15, "")
        img_pil = dataurl_to_pil(image_dataurl).convert("RGB")
        img_np  = np.array(img_pil)
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

        # สร้าง mask จากสี่เหลี่ยมที่ผู้ใช้วาด
        boxes = []
        for r in rectangles:
            x1, y1 = int(r["x"]), int(r["y"])
            x2, y2 = x1 + int(r["width"]), y1 + int(r["height"])
            boxes.append((x1, y1, x2, y2))
        mask_np = multi_box_auto_mask(img_bgr, boxes)
        
        # บันทึกภาพต้นฉบับ + mask
        update_progress(30, "กำลังตัด patch...")
        cv2.imwrite(os.path.join(SAVE_DIR, "original.png"), img_bgr)
        cv2.imwrite(os.path.join(SAVE_DIR, "mask.png"), mask_np)

        # ตัดภาพเป็น patch ย่อย
        n_patches, full_size = save_patches(
            img_bgr, mask_np,
            os.path.join(SAVE_DIR, "patches_img"),
            os.path.join(SAVE_DIR, "patches_mask"),
            prefix="patch",
            size=256, stride=256
        )

        # ย้ายไฟล์จาก runtime ไปใส่ demotest เพื่อใช้กับโมเดล
        clear_and_copy(os.path.join(SAVE_DIR, "patches_img"),  os.path.join(MODEL_TEST_DIR, "demotest"))
        clear_and_copy(os.path.join(SAVE_DIR, "patches_mask"), os.path.join(MODEL_TEST_DIR, "gt_keep_masks"))

        # รันโมเดล DiffPIR
        update_progress(60, "")
        merged_dir = run_test_py()   # โฟลเดอร์ results/result_image ที่มี result_*.png

        #รวมรูปเป็นภาพใหญ่
        update_progress(80, "กำลังรวม patch...")
        result_img = reassemble_patches_with_blending(merged_dir, full_size, size=256, stride=256)

        debug_out_path = os.path.join(SAVE_DIR, "final_result.png")
        cv2.imwrite(debug_out_path, result_img)
        print(f"[DEBUG] Saved final assembled output to {debug_out_path}")

        #คำนวณ PSNR / LPIPS ทีละ patch
        patch_files = sorted(glob.glob(os.path.join(merged_dir, "result_*.png")))
        psnr_list, lpips_list, time_list = [], [], []

        import lpips
        loss_fn = lpips.LPIPS(net='vgg')

        for patch_path in patch_files:
            img_name = os.path.basename(patch_path)
            start_patch_time = time.time()

            restored_patch = cv2.imread(patch_path)
            original_patch_path = os.path.join(
                SAVE_DIR, "patches_img",
                img_name.replace("result_", "patch_")
            )
            if not os.path.exists(original_patch_path):
                print(f"[WARN] ไม่พบภาพต้นฉบับของ {img_name}")
                continue
            original_patch = cv2.imread(original_patch_path)

            # PSNR
            psnr_val = calculate_psnr(original_patch, restored_patch)
            psnr_list.append(psnr_val)

            # LPIPS
            t1 = lpips.im2tensor(original_patch)
            t2 = lpips.im2tensor(restored_patch)
            lpips_val = loss_fn(t1, t2).item()
            lpips_list.append(lpips_val)

            elapsed_patch_time = time.time() - start_patch_time
            time_list.append(elapsed_patch_time)

            print(f"📄 {img_name} | PSNR: {psnr_val:.2f} dB | LPIPS: {lpips_val:.4f} | Time: {elapsed_patch_time:.2f} s")

        if psnr_list:
            avg_psnr = sum(psnr_list) / len(psnr_list)
            avg_lpips = sum(lpips_list) / len(lpips_list)
            avg_time  = sum(time_list) / len(time_list)

            print(f"📈 Average PSNR: {avg_psnr:.4f} dB")
            print(f"📉 Average LPIPS: {avg_lpips:.4f}")
            print(f"⏱️ Average Time per patch: {avg_time:.2f} s")

        update_progress(100, "เสร็จสิ้น ✅")

        total_time = time.time() - progress_data["start_time"]
        print(f"🕒 เวลาที่ใช้ในการฟื้นฟูทั้งหมด: {total_time:.2f} วินาที")

        _, buf = cv2.imencode(".png", result_img)
        b64 = base64.b64encode(buf).decode("utf-8")
        progress_data["result"] = "data:image/png;base64," + b64

    except Exception as e:
        print(f"[ERROR in run_pipeline] {e}")
        update_progress(100, f"❌ error: {str(e)}")



# ---------- Routes ----------
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "home.html")

@app.route("/process", methods=["POST"])
def process():
    data = request.get_json()
    image_dataurl = data["image"] #รับภาพจากผู้ใช้
    rectangles    = data["rectangles"] #รับตำแหน่งกรอบสี่เหลี่ยมจากผู้ใช้

    global progress_data
    progress_data = {"progress": 0, "elapsed": 0, "message": "", "start_time": time.time(), "result": None}

    # สั่งทำงานแบบthrend
    thread = threading.Thread(target=run_pipeline, args=(image_dataurl, rectangles))
    thread.start()

    return jsonify({"success": True, "message": "เริ่มประมวลผลแล้ว"})

@app.route("/progress")
def progress():
    # ส่งข้อมูล progress ล่าสุดกลับไปเป็น JSON
    return jsonify(progress_data)


if __name__ == "__main__":
    app.run(debug=True)
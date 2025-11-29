let selectedFile = null;
let canvas = null;
let ctx = null;
let img = null;
let scale = 1;
let offsetX = 0;
let offsetY = 0;
let imgWidth = 0;
let imgHeight = 0;
let rectangles = [];
let isDrawing = false;
let startX, startY;
let currentRect = null;
let restoredImageData = null;
let isPanning = false;
let lastPanX, lastPanY;
let initialScale = 1;
let initialOffsetX = 0;
let initialOffsetY = 0;
let startTime = 0; //เวลา

// Initialize when page loadsstartProcessing
document.addEventListener('DOMContentLoaded', function () {
    initializeUpload();
    initializeCanvas();
});

function initializeUpload() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');

    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('drop', handleDrop);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    fileInput.addEventListener('change', handleFileSelect);
}

function handleDragOver(e) {
    e.preventDefault();
    document.getElementById('upload-area').classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    document.getElementById('upload-area').classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    document.getElementById('upload-area').classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        processFile(files[0]);
    }
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        processFile(file);
    }
}

function processFile(file) {
    if (!file.type.startsWith('image/')) {
        alert('กรุณาเลือกไฟล์ภาพเท่านั้น');
        return;
    }

    if (file.size > 50 * 1024 * 1024) {
        alert('ขนาดไฟล์ใหญ่เกินไป (สูงสุด 10MB)');
        return;
    }

    selectedFile = file;
    loadImageToCanvas(file);
}

function loadImageToCanvas(file) {
    const reader = new FileReader();
    reader.onload = function (e) {
        img = new Image();
        img.onload = function () {
            setupCanvas();
            document.getElementById('upload-section').style.display = 'none';
            document.getElementById('editor-section').style.display = 'block';
            document.getElementById('process-btn').style.display = 'inline-block';
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

function initializeCanvas() {
    canvas = document.getElementById('editor-canvas');
    ctx = canvas.getContext('2d');

    // Mouse events
    canvas.addEventListener('mousedown', handleMouseDown);
    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('mouseup', handleMouseUp);
    canvas.addEventListener('wheel', handleWheel);

    // Prevent default drag behavior
    canvas.addEventListener('dragstart', e => e.preventDefault());

    // Control buttons
    document.getElementById('zoom-in-btn').addEventListener('click', zoomIn);
    document.getElementById('zoom-out-btn').addEventListener('click', zoomOut);
    document.getElementById('reset-zoom-btn').addEventListener('click', resetZoom);
    document.getElementById('undo-btn').addEventListener('click', undoLastRectangle);
    document.getElementById('clear-btn').addEventListener('click', clearAllRectangles);
}

function setupCanvas() {
    const maxWidth = 800;
    const maxHeight = 500;

    // Store original image dimensions
    imgWidth = img.width;
    imgHeight = img.height;

    // Calculate display size
    let displayWidth = imgWidth;
    let displayHeight = imgHeight;

    if (displayWidth > maxWidth) {
        displayHeight = (displayHeight * maxWidth) / displayWidth;
        displayWidth = maxWidth;
    }

    if (displayHeight > maxHeight) {
        displayWidth = (displayWidth * maxHeight) / displayHeight;
        displayHeight = maxHeight;
    }

    // Set canvas size
    canvas.width = maxWidth;
    canvas.height = maxHeight;

    // Calculate initial scale and offset to center image
    scale = Math.max(canvas.width / imgWidth, canvas.height / imgHeight);
    offsetX = (canvas.width - imgWidth * scale) / 2;
    offsetY = (canvas.height - imgHeight * scale) / 2;

    // Store initial values for reset
    initialScale = scale;
    initialOffsetX = offsetX;
    initialOffsetY = offsetY;

    drawCanvas();
}
function resetZoom() {
    scale = initialScale;
    offsetX = initialOffsetX;
    offsetY = initialOffsetY;
    drawCanvas();
}
function zoomAtPoint(centerX, centerY, factor) {
    const imgX = (centerX - offsetX) / scale;
    const imgY = (centerY - offsetY) / scale;
    const newScale = Math.max(0.1, Math.min(10, scale * factor));
    if (newScale !== scale) {
        scale = newScale;
        offsetX = centerX - imgX * scale;
        offsetY = centerY - imgY * scale;
        drawCanvas();
    }
}

function zoomIn() {
    zoomAtPoint(canvas.width / 2, canvas.height / 2, 1.2);
}

function zoomOut() {
    zoomAtPoint(canvas.width / 2, canvas.height / 2, 0.8);
}
function drawCanvas() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw background
    ctx.fillStyle = '#f8f9fa';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw image with current scale and offset
    const drawWidth = imgWidth * scale;
    const drawHeight = imgHeight * scale;
    ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight);

    // Draw rectangles
    ctx.strokeStyle = '#FF6B35';
    ctx.lineWidth = 3;
    ctx.setLineDash([5, 5]);

    rectangles.forEach(rect => {
        const x = rect.x * scale + offsetX;
        const y = rect.y * scale + offsetY;
        const width = rect.width * scale;
        const height = rect.height * scale;
        ctx.strokeRect(x, y, width, height);
    });

    // Draw current rectangle if drawing
    if (currentRect) {
        const x = currentRect.x * scale + offsetX;
        const y = currentRect.y * scale + offsetY;
        const width = currentRect.width * scale;
        const height = currentRect.height * scale;
        ctx.strokeRect(x, y, width, height);
    }
}

function handleMouseDown(e) {
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // Check if Ctrl/Cmd is pressed for panning
    if (e.ctrlKey || e.metaKey) {
        isPanning = true;
        lastPanX = mouseX;
        lastPanY = mouseY;
        canvas.style.cursor = 'grabbing';
        return;
    }

    // Check if click is within image bounds for drawing
    const drawWidth = imgWidth * scale;
    const drawHeight = imgHeight * scale;

    if (mouseX < offsetX || mouseX > offsetX + drawWidth ||
        mouseY < offsetY || mouseY > offsetY + drawHeight) {
        return; // Click outside image
    }

    isDrawing = true;
    canvas.style.cursor = 'crosshair';

    // Convert canvas coordinates to image coordinates
    startX = (mouseX - offsetX) / scale;
    startY = (mouseY - offsetY) / scale;
    currentRect = null;
}

function handleMouseMove(e) {
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const drawWidth = imgWidth * scale;
    const drawHeight = imgHeight * scale;
    const insideImage = (
        mouseX >= offsetX && mouseX <= offsetX + drawWidth &&
        mouseY >= offsetY && mouseY <= offsetY + drawHeight
    );
    // Update cursor based on modifier keys
    if (e.ctrlKey || e.metaKey) {
        canvas.style.cursor = isPanning ? 'grabbing' : 'grab';
    } else if (isDrawing) {
        canvas.style.cursor = 'crosshair';
    } else if (insideImage) {
        canvas.style.cursor = 'crosshair';   // 👈 อยู่บนรูป ให้เป็น crosshair
    } else {
        canvas.style.cursor = 'default';     // นอกกรอบรูป เป็น default
    }

    if (isPanning) {
        // Pan the image
        const deltaX = mouseX - lastPanX;
        const deltaY = mouseY - lastPanY;

        offsetX += deltaX;
        offsetY += deltaY;

        lastPanX = mouseX;
        lastPanY = mouseY;

        drawCanvas();
        return;
    }

    if (!isDrawing) return;

    // Convert canvas coordinates to image coordinates
    const imgMouseX = (mouseX - offsetX) / scale;
    const imgMouseY = (mouseY - offsetY) / scale;

    // Clamp to image boundaries
    const clampedX = Math.max(0, Math.min(imgWidth, imgMouseX));
    const clampedY = Math.max(0, Math.min(imgHeight, imgMouseY));

    currentRect = {
        x: Math.min(startX, clampedX),
        y: Math.min(startY, clampedY),
        width: Math.abs(clampedX - startX),
        height: Math.abs(clampedY - startY)
    };

    drawCanvas();
}

function handleMouseUp(e) {
    if (isPanning) {
        isPanning = false;
        canvas.style.cursor = e.ctrlKey || e.metaKey ? 'grab' : 'default';
        return;
    }

    if (!isDrawing) return;

    isDrawing = false;
    canvas.style.cursor = 'default';

    if (currentRect && currentRect.width > 5 && currentRect.height > 5) {
        rectangles.push({ ...currentRect });
        updateControlButtons();
    }
    currentRect = null;
    drawCanvas();
}

function handleWheel(e) {
    e.preventDefault();

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // Calculate zoom point in image coordinates before zoom
    const imgMouseX = (mouseX - offsetX) / scale;
    const imgMouseY = (mouseY - offsetY) / scale;

    // Zoom in or out
    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(0.1, Math.min(10, scale * zoomFactor));

    if (newScale !== scale) {
        scale = newScale;

        // Adjust offset to keep mouse position stable
        offsetX = mouseX - imgMouseX * scale;
        offsetY = mouseY - imgMouseY * scale;

        drawCanvas();
    }
}

function zoomIn() {
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    zoomAtPoint(centerX, centerY, 1.2);
}

function zoomOut() {
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    zoomAtPoint(centerX, centerY, 0.8);
}

function undoLastRectangle() {
    if (rectangles.length > 0) {
        rectangles.pop();
        updateControlButtons();
        drawCanvas();
    }
}

function clearAllRectangles() {
    rectangles = [];
    updateControlButtons();
    drawCanvas();
}

function updateControlButtons() {
    const processBtn = document.getElementById("process-btn");
    const undoBtn = document.getElementById("undo-btn");
    const clearBtn = document.getElementById("clear-btn");

    if (rectangles.length > 0) {
        // ✅ มีการวาด mask แล้ว
        processBtn.disabled = false;
        processBtn.style.display = "inline-block";

        // ✅ เปิดให้ปุ่ม undo / clear ใช้งานได้
        undoBtn.disabled = false;
        clearBtn.disabled = false;
    } else {
        // ❌ ยังไม่มี mask
        processBtn.disabled = true;
        processBtn.style.display = "inline-block";

        // ❌ ปิดการใช้งาน undo / clear
        undoBtn.disabled = true;
        clearBtn.disabled = true;
    }
}
async function startProcessing() {
    if (rectangles.length === 0) {
        alert("กรุณาเลือกพื้นที่ที่ต้องการฟื้นฟูก่อน");
        return;
    }
    startTime = performance.now();
    const tempCanvas = document.createElement("canvas");
    tempCanvas.width = img.width;
    tempCanvas.height = img.height;
    const tempCtx = tempCanvas.getContext("2d");
    tempCtx.drawImage(img, 0, 0);
    const originalImageDataUrl = tempCanvas.toDataURL("image/png");

    const payload = { image: originalImageDataUrl, rectangles: rectangles };
    const progressSection = document.getElementById("progress-section");
    const progressFill = document.getElementById("progress-fill");
    const progressText = document.getElementById("progress-text");

    progressSection.style.display = "block";
    document.getElementById("process-btn").style.display = "none";

    let currentProgress = 0;
    let polling = true;

    // ✅ สั่งให้ backend เริ่มทำงานก่อน
    try {
        const res = await fetch("/process", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!data.success) {
            alert("❌ เกิดข้อผิดพลาด: " + data.message);
            return;
        }
        // ✅ เริ่ม polling หลังจาก backend เริ่มแล้ว
        pollProgress();
    } catch (err) {
        console.error("❌ Error:", err);
        alert("เกิดข้อผิดพลาดที่ backend");
        return;
    }

    async function pollProgress() {
        if (!polling) return;
        try {
            const res = await fetch("/progress"); // หรือ /status ให้ตรง backend
            const data = await res.json();

            let target = data.progress;
            

            // ✅ animate การไหลของ progress
            let step = setInterval(() => {
                if (currentProgress >= target) {
                    clearInterval(step);
                } else {
                    currentProgress++;
                    progressFill.style.width = currentProgress + "%";
                    progressText.textContent =
                        `กำลังประมวลผล... ${currentProgress}%`;
                }
            }, 40);

            if (target >= 100) {
                polling = false;
                if (data.result) showResult(data.result); // แสดงภาพเมื่อเสร็จ
            } else {
                setTimeout(pollProgress, 1000);
            }
        } catch (err) {
            console.error("Error polling progress:", err);
        }
    }
}

function showResult(resultBase64) {
    const resultContainer = document.getElementById("result-section");
    const resultImg = document.getElementById("restored-result");
    const downloadBtn = document.querySelector(".download-btn");

    resultContainer.style.display = "block";
    resultImg.src = resultBase64;
    downloadBtn.setAttribute("data-download", resultBase64);

    // ✅ ซ่อน progress bar เมื่อเสร็จสิ้น
    const progressSection = document.getElementById("progress-section");
    progressSection.style.display = "none";


    // ✅ แสดงเวลาใน console
    const endTime = performance.now();
    if (typeof startTime !== "undefined" && startTime > 0) {
        const elapsed = ((endTime - startTime) / 1000).toFixed(2);
        console.log(`เวลาที่ใช้ในการฟื้นฟู: ${elapsed} วินาที`);
    } else {
        console.log("⚠️ ไม่พบค่า startTime (อาจยังไม่ได้เริ่มจับเวลา)");
    }

    const newImg = new Image();
    newImg.onload = function () {
        img = newImg;
        setupCanvas();
        rectangles = [];
        updateControlButtons();
    };
    newImg.src = resultBase64;
}

function downloadResult() {
    const restoredResult = document.getElementById("restored-result");
    if (!restoredResult.src) return;

    const link = document.createElement("a");
    link.href = restoredResult.src;
    link.download = "restored_mural.png";
    link.click();
}
function changeImage() {
    // Reset all states
    selectedFile = null;
    rectangles = [];
    scale = 1;
    offsetX = 0;
    offsetY = 0;
    img = null;
    restoredImageData = null;

    // Clear canvas
    if (canvas && ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    // Reset file input
    document.getElementById('file-input').value = '';

    // Reset upload area display
    const uploadArea = document.getElementById('upload-area');
    uploadArea.innerHTML = `
                <div class="upload-icon">📷</div>
                <div class="upload-text">ลากไฟล์ภาพมาวางที่นี่ หรือคลิกเพื่อเลือกไฟล์</div>
                <div class="upload-subtext">รองรับไฟล์: JPG, PNG, JPEG (ขนาดไม่เกิน 50MB)</div>
            `;

    // Hide all sections except upload
    document.getElementById('upload-section').style.display = 'block';
    document.getElementById('editor-section').style.display = 'none';
    document.getElementById('progress-section').style.display = 'none';
    document.getElementById('result-section').style.display = 'none';

    // Reset control buttons
    updateControlButtons();

    // Show success message
    const changeBtn = document.getElementById('change-image-btn');
    const originalText = changeBtn.innerHTML;
    changeBtn.innerHTML = '✅ พร้อมอัพโหลดรูปใหม่';
    changeBtn.style.background = 'linear-gradient(145deg, #28a745, #34ce57)';

    setTimeout(() => {
        changeBtn.innerHTML = originalText;
        changeBtn.style.background = '';
    }, 2000);
}
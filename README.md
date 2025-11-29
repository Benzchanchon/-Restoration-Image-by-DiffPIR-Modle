# Thai Mural Image Restoration using DiffPIR Model
การบูรณะภาพจิตรกรรมฝาผนังไทยด้วยโมเดลDiffPIR

# Project Overview | ภาพรวมของโครงการ
This project aims to restore and enhance damaged Thai mural paintings using deep learning–based inpainting techniques.<br>
We fine-tuned and extended the DiffPIR model for Thai mural restoration, developed a Flask web interface, and created a custom dataset for real-world applications.<br>
โครงการนี้เป็นระบบฟื้นฟูภาพจิตรกรรมฝาผนังไทยโดยใช้โมเดลDiffPIR Model<br>
ซึ่งเป็นเทคนิคการประมวลผลภาพด้วยโมเดล Diffusion ที่ช่วยซ่อมแซมรายละเอียดของภาพที่เสียหายและถูกลบเลือนได้อย่างมีประสิทธิภาพให้เหมาะสมกับภาพจิตรกรรมไทย<br>
พร้อมทั้งพัฒนา Web Application เพื่อใช้งานจริง

# Model & Methodology | โมเดลและกระบวนการ
1.Mask Generation – สร้างมาสก์อัตโนมัติระบุบริเวณที่ชำรุด<br>
2.DiffPIR Restoration – ใช้การประมวลผลภาพแบบ diffusion ในการเติมเต็มส่วนที่หายไป

# System Overview | สถาปัตยกรรมระบบ
Input → Auto Mask → DiffPIR Inpainting → Output

| ส่วนประกอบ              | รายละเอียด                                      |
|-------------------------|--------------------------------------------------|
| Frontend (Flask Web UI) | ระบบอัปโหลด/แสดงผลภาพแบบเรียลไทม์             |
| Backend (Python)        | ประมวลผลภาพ, รันโมเดล, รวมภาพหลังบูรณะ        |
| Model (DiffPIR)         | โมเดล Diffusion สำหรับการฟื้นฟูและเติมเต็มภาพ   |

# Installation | การติดตั้ง
git clone https://github.com/Benzchanchon/-Restoration-Image-by-DiffPIR-Modle<br>
cd Restoration-Image-by-DiffPIR-Modle<br>
python -m venv venv<br>
venv\Scripts\activate<br>
pip install -r requirements.txt<br>
python app.py<br>
แล้วเปิดเว็บที่ http://127.0.0.1:5000/<br>

Evaluation Metrics<br>
Metric	Description<br>
PSNR	วัดความเหมือนของภาพที่บูรณะกับต้นฉบับ<br>
LPIPS	วัดคุณภาพเชิงการรับรู้ (Perceptual similarity)<br>

เนื่องจากไฟล์น้ำหนักโมเดล (Pretrained Weights)มีขนาดใหญ่เกินกว่าที่ GitHub จะรองรับได้ ผู้ใช้งานสามารถดาวน์โหลดไฟล์ทั้งหมดได้ผ่าน Google Drive ตามลิงก์ด้านล่างนี้<br>
Because the pretrained model weights are too large to be stored directly on GitHub, all required files can be downloaded via the Google Drive link below:<br>
https://drive.google.com/file/d/1fqbSCxD_XIibrSaiXxj9ilN2P9ovyea4/view?usp=sharing<br>
ให้นำไฟล์น้ำหนักโมเดล (.pt) ที่ดาวน์โหลดมา<br>
ไปวางไว้ในโฟลเดอร์ model_zoo/<br>
เพื่อให้ระบบสามารถโหลดโมเดลได้อย่างถูกต้องระหว่างการประมวลผล<br>
Place the downloaded .pt model weight files into the<br>
model_zoo/ directory<br>
so the system can correctly load the models during inference<br>

Developer<br>
Chanchon Rit-in<br>
Faculty of Information Technology, Silpakorn University<br>
Advisor: Asst. Prof. Dr. Sunisa Pongpinijpinyo<br>

Email: chanchon1150@gmail.com<br>
GitHub: @Benzchanchon<br>

This project is based on the original DiffPIR implementation by<br>
yuanzhi-zhu/DiffPIR<br>

We have fine-tuned and expanded it for Thai mural restoration,<br>
with additional dataset preparation, automatic mask generation,<br>
and a web-based interface for real-world use.



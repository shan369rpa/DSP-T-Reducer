# 🎓 DSP Learning: Giảm Âm Gắt "T" Trong Tiếng Việt

> **Mục tiêu duy nhất**: Hiểu và xử lý âm "t" đầu âm tiết trong: **tu, thì, ta, trong, trên**

---

## 🎯 Vấn Đề Cần Giải Quyết

Trong thu âm giọng nói tiếng Việt, các từ bắt đầu bằng **t, th, tr** thường tạo ra âm "gắt" (harsh) do:
- **Burst energy** đột ngột khi phát âm
- **Aspiration** (hơi thở) sau khi thả âm
- **Transient** quá mạnh so với nguyên âm theo sau

---

## 🚀 Quick Start

```bash
# 1. Cài đặt
pip install -r requirements.txt

# 2. Chạy module (mặc định 50% reduction)
uv run python src/t_reducer/t_reducer.py input.mp3 output.mp3

# 3. Tùy chỉnh mức giảm
uv run python src/t_reducer/t_reducer.py input.mp3 output.mp3 --reduction 70
```

---

## ✨ Tính Năng v3.0 (Phase 0 Audit Improvements)

### 🔹 Tổng Quan

| Tính Năng | Mô Tả | Mặc Định |
|-----------|-------|----------|
| **ZCR Detection** | Phân biệt âm vô thanh (t,s) với âm hữu thanh (a,e) | BẬT |
| **Pre-emphasis** | Khuếch đại tần số cao trước khi phân tích | BẬT |
| **Lookahead** | Bắt đầu xử lý TRƯỚC KHI âm T xảy ra | 5ms |

---

## 📚 Giải Thích Chi Tiết Các Tính Năng

### 1️⃣ Zero Crossing Rate (ZCR) - Tỉ Lệ Cắt Ngang Trục 0

#### 🤔 ZCR Là Gì?

Hãy tưởng tượng sóng âm thanh như một đường gợn sóng lên xuống:

```
     +1 ┌───────╮       ╭───────╮
        │       │       │       │
      0 ┼───────┼───────┼───────┼───────→ thời gian
        │       │       │       │
     -1 └───────╯       ╰───────╯
              ↑               ↑
         "Cắt ngang 0"   "Cắt ngang 0"
```

**ZCR = Số lần sóng âm cắt ngang đường 0 trong 1 giây**

#### 🎯 Tại Sao ZCR Quan Trọng?

| Loại Âm | ZCR | Ví Dụ |
|---------|-----|-------|
| **Âm hữu thanh** (dây thanh rung) | THẤP (~50-100) | a, e, i, o, u, m, n |
| **Âm vô thanh** (không rung dây thanh) | CAO (~300-500) | **t**, s, ch, p, k |

**Ví dụ dễ hiểu:**
- Khi bạn nói "aaaaaa" → sóng âm mượt, ít cắt ngang 0 → ZCR thấp
- Khi bạn nói "ttttttt" → sóng âm nhiễu loạn, cắt ngang 0 liên tục → ZCR cao

#### 💡 Module Dùng ZCR Như Thế Nào?

```
Bước 1: Tính ZCR cho từng đoạn nhỏ (frame) của audio
Bước 2: Nếu ZCR > 0.15 → Đây có thể là âm T (vô thanh)
Bước 3: Chỉ xử lý những đoạn có ZCR cao
Bước 4: Bỏ qua những đoạn có ZCR thấp (nguyên âm, giữ nguyên)
```

**Kết quả:** Module chỉ "đụng" vào đúng âm T, không ảnh hưởng đến nguyên âm!

---

### 2️⃣ Pre-emphasis Filter - Bộ Lọc Khuếch Đại Tần Số Cao

#### 🤔 Pre-emphasis Là Gì?

Đây là một "bộ lọc" làm **tăng cường tần số cao** trước khi module bắt đầu phân tích.

**Công thức toán học:**
```
y[n] = x[n] - 0.97 × x[n-1]
```

**Giải thích đơn giản:**
- Lấy mẫu âm thanh hiện tại
- Trừ đi 97% mẫu trước đó
- Kết quả: Tần số cao được "boost" lên, tần số thấp bị "nhấn chìm"

#### 🎯 Tại Sao Cần Pre-emphasis?

**VẤN ĐỀ:** Âm T có năng lượng tập trung ở tần số cao (4-10kHz), nhưng năng lượng này nhỏ hơn nhiều so với nguyên âm (tần số thấp).

```
Trước Pre-emphasis:
Năng lượng ▲
    100% │████████████████  (Nguyên âm "a" - tần số thấp)
         │
     20% │███                (Âm "t" - tần số cao)
         └────────────────────────────→ Tần số

Sau Pre-emphasis:
Năng lượng ▲
     80% │████████████████  (Nguyên âm - giảm xuống)
         │
     60% │████████████      (Âm "t" - tăng lên, DỄ PHÁT HIỆN HƠN!)
         └────────────────────────────→ Tần số
```

#### 💡 Lợi Ích Thực Tế

- **Trước:** Module có thể BỎ SÓT âm T yếu (ví dụ khi người nói nhẹ nhàng)
- **Sau:** Module PHÁT HIỆN ĐƯỢC CẢ âm T yếu nhờ pre-emphasis boost lên

---

### 3️⃣ Lookahead Buffer - Bộ Đệm "Nhìn Trước"

#### 🤔 Lookahead Là Gì?

Lookahead có nghĩa là **"nhìn trước"**. Module sẽ bắt đầu xử lý (giảm volume) **TRƯỚC KHI** âm T thực sự xảy ra.

#### 🎯 Tại Sao Cần Lookahead?

**VẤN ĐỀ:** Âm T là một "cú đấm" âm thanh cực nhanh (~5ms). Nếu bạn giảm volume SAU KHI cú đấm đã xảy ra, thì đã quá muộn!

```
KHÔNG CÓ LOOKAHEAD (XẤU):
                    ↓ Module phát hiện âm T
    ────────────┌───┴───┐─────────────
                │ BURST │  ← Vẫn nghe thấy tiếng "bộp"!
    ────────────└───────┘─────────────
                        ↑ 
                Bắt đầu giảm (QUÁ MUỘN!)

CÓ LOOKAHEAD 5ms (TỐT):
            ↓ Bắt đầu giảm TRƯỚC 5ms
    ────────┬───────────────────────────
            │   ↓ Module phát hiện âm T
    ────────┴───┌───┴───┐─────────────
                │ BURST │  ← Đã được giảm volume ngay từ đầu!
    ────────────└───────┘─────────────
```

#### 💡 Ví Dụ Dễ Hiểu

Hãy tưởng tượng bạn đang chạy xe và thấy ổ gà phía trước:
- **Không có lookahead:** Bạn chỉ phanh SAU KHI đã đâm vào ổ gà → Trễ!
- **Có lookahead:** Bạn phanh TRƯỚC KHI đến ổ gà → Mượt!

**Trong audio:**
- Lookahead 5ms = Module "nhìn thấy" âm T sắp đến từ 5 miligiây trước
- Bắt đầu giảm volume từ lúc đó → Không có "click" hay "pop" ở đầu burst

---

## 📖 Hướng Dẫn CLI (Command Line)

### Cú Pháp

```bash
uv run python src/t_reducer/t_reducer.py <input> <output> [options]
```

### Các Options

| Option | Mặc Định | Mô Tả |
|--------|----------|-------|
| `--reduction` | 50 | Mức giảm (0-100%). **-1** = MUTE (Tắt tiếng hoàn toàn) |
| `--fps` | 30 | Frame rate của video (cho Timecode chính xác) |
| `--no-zcr` | False | Tắt ZCR (nhanh hơn nhưng kém chính xác) |
| `--no-preemphasis` | False | Tắt Pre-emphasis |
| `--no-wavelet` | False | Tắt Wavelet detection (dùng logic cũ) |
| `--lookahead` | 5 | Thời gian lookahead (ms) - Bắt đầu sớm hơn |
| `--release` | 15 | Thời gian release (ms) - Kéo dài vết cắt |

### Ví Dụ

```bash
# Mặc định (Hybrid Wavelet Mode)
uv run python src/t_reducer/t_reducer.py input.mp3 output.mp3

# Tùy chỉnh độ dài vết cắt (Release 30ms cho âm TH/TR dài)
uv run python src/t_reducer/t_reducer.py input.mp3 output.mp3 --release 30

# CHẾ ĐỘ KIỂM TRA: Tắt tiếng hoàn toàn (-1) để soi waveform
uv run python src/t_reducer/t_reducer.py input.mp3 output.mp3 --reduction -1

# Giảm mạnh 100% (-99dB)
uv run python src/t_reducer/t_reducer.py input.mp3 output.mp3 --reduction 100

# Project 24fps (cho phim)
uv run python src/t_reducer/t_reducer.py input.wav output.wav --fps 24
```

> **Note**: Từ v4.0, module tự động **Auto-Match Volume** để output không bị nhỏ hơn input.

---

## 📁 Output Files

Sau khi chạy, bạn nhận được **2 files**:

1. **`output.mp3`**: Audio đã xử lý
2. **`output.csv`**: Log chi tiết với các cột:

| Cột | Ý Nghĩa |
|-----|---------|
| FCP Timecode | Timecode chuẩn Final Cut Pro (HH:MM:SS:FF.SF) |
| Start Time (s) | Thời gian bắt đầu (giây) |
| Duration (ms) | Độ dài của burst (miligiây) |
| Centroid (Hz) | Tần số trung tâm của âm T |
| Avg ZCR | Giá trị ZCR trung bình (cao = vô thanh) |
| Reduction (dB) | Mức giảm đã áp dụng |

---

## 📚 Tham Khảo

- [Technical Audit Report](docs/TECHNICAL_AUDIT_REPORT.md)
- [iZotope DSP Principles](docs/izotope_dsp_principles.md)
- [T Sound Analysis](docs/t_sound_analysis.md)

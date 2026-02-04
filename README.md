# 🎓 DSP Learning: Giảm Âm Gắt "T" Trong Tiếng Việt

> **Mục tiêu duy nhất**: Hiểu và xử lý âm "t" đầu âm tiết trong: **tu, thì, ta, trong, trên**

---

## 🎯 Vấn Đề Cần Giải Quyết

Trong thu âm giọng nói tiếng Việt, các từ bắt đầu bằng **t, th, tr** thường tạo ra âm "gắt" (harsh) do:
- **Burst energy** đột ngột khi phát âm
- **Aspiration** (hơi thở) sau khi thả âm
- **Transient** quá mạnh so với nguyên âm theo sau

**Ví dụ cụ thể**:
- "**t**u" - âm t + u
- "**th**ì" - âm th + ì
- "**t**a" - âm t + a
- "**tr**ong" - âm tr + ong
- "**tr**ên" - âm tr + ên

---

## 📊 Đặc Tính Acoustic Của Âm T Tiếng Việt

### 3 Loại Âm T Cần Xử Lý

| Âm | IPA | Đặc Điểm | Tần Số Burst | VOT |
|----|-----|----------|--------------|-----|
| **t** | /t̪/ | Unaspirated, denti-alveolar | >4kHz | ~0ms |
| **th** | /t̪ʰ/ | Aspirated, có hơi thở | >4kHz | 40-80ms |
| **tr** | /ʈ͡ʂ/ | Retroflex affricate | 2-4kHz | ~0ms |

### Cấu Trúc Thời Gian

```
Âm "t" trong "ta":
|--Silence--|--Burst--|--Vowel "a"--|
     ↓          ↓           ↓
   0-50ms    ~10ms     rest of syllable

Âm "th" trong "thì":
|--Silence--|--Burst--|--Aspiration--|--Vowel "ì"--|
     ↓          ↓           ↓              ↓
   0-50ms    ~10ms      40-80ms      rest of syllable

Âm "tr" trong "trong":
|--Silence--|--Burst--|--Frication--|--Vowel "ong"--|
     ↓          ↓           ↓              ↓
   0-50ms    ~10ms       ~30ms       rest of syllable
```

---

## ✨ Tính Năng Professional (v2.0)

Phiên bản mới (v2.0) đã được nâng cấp dựa trên DSP Audit:

1. **Adaptive Detection**: Tự động thích nghi với volumn to/nhỏ của file (dùng Moving Average Threshold).
2. **Frequency Tracking**: Tự động tìm vị trí tần số của âm T (Spectral Centroid) thay vì cắt mò ở 4-8kHz.
3. **Smart Targeting**: Chỉ xử lý vùng tần số có vấn đề, giữ nguyên các dải tần khác.
4. **Natural Sound**: Giảm gắt mượt mà, tránh hiện tượng "robot" hoặc "nghẹt mũi".
5. **Detailed Logging**: Xuất file CSV báo cáo chi tiết từng vị trí detected (Timecode, Duration, Frequency, Reduction).

## 📁 Cấu Trúc Dự Án

```
DSP (Digital Signal Processor)/
├── README.md                    ← Bạn đang đây
├── requirements.txt             
│
├── docs/
│   └── t_sound_analysis.md      ← Phân tích chi tiết âm T
│
└── src/
    └── t_reducer/
        └── t_reducer.py         ← Module giảm âm T
```

---

## 🚀 Quick Start

# 1. Cài đặt
pip install -r requirements.txt

# 2. Chạy module
python src/t_reducer/t_reducer.py '/Users/sonpc/Downloads/Mẫu/DSP(T only)/TEST AI.m4a' '/Users/sonpc/Downloads/Mẫu/DSP(T only)/TEST AI_output.m4a' --reduction 50

### 1. Nguyên Lý DSP từ iZotope Modules (docs/izotope_dsp_principles.md)
- **De-plosive**: Bandpass filter + Envelope detection + Selective reduction
- **De-click**: Spectral flux → Transient detection
- **Deconstruct**: HPSS separation (tonal/noise/transient)
- **Áp dụng cho âm T**: Kết hợp 3 modules cho tiếng Việt

### 2. Phân Tích Âm T (docs/t_sound_analysis.md)
- FFT/STFT cơ bản
- Cách detect âm T trên spectrogram
- Đặc tính tần số của t, th, tr

### 3. Implementation (src/t_reducer/)
- Algorithm detect âm T
- Giảm burst energy
- Làm mềm aspiration

---

## 🎯 Mục Tiêu Kỹ Thuật

**Input**: Audio có nhiều từ bắt đầu bằng t, th, tr  

**Output**: Audio với âm T giảm 30-50% harshness

### Giải Thích Chi Tiết Output

Khi module xử lý xong, bạn sẽ nhận được:

#### 1. File Audio Đã Xử Lý
- **Format**: Giống input (WAV, FLAC, MP3)
- **Sample rate**: Giữ nguyên (thường 44100Hz)
- **Độ dài**: Giống input (không thay đổi thời lượng)

#### 2. Sự Khác Biệt Nghe Được

**Trước xử lý** (input):
```
"Tôi thì trong trên ta"
 ↑   ↑    ↑     ↑    ↑
 Âm T nghe GẮT, có cảm giác "bộp" hoặc "xẹt"
```

**Sau xử lý** (output):
```
"Tôi thì trong trên ta"
 ↑   ↑    ↑     ↑    ↑
 Âm T nghe MỀM hơn, tự nhiên hơn, nhưng VẪN RÕ
```

#### 3. Thay Đổi Kỹ Thuật

| Khía Cạnh | Trước | Sau (50% reduction) | Ghi Chú |
|-----------|-------|---------------------|---------|
| **Burst energy (4-8kHz)** | 100% | ~50% | Giảm "xẹt" high-freq |
| **Low-freq thump (20-300Hz)** | 100% | ~50% | Giảm "bộp" low-freq |
| **Nguyên âm sau T** | 100% | 100% | Không đổi |
| **Clarity của âm T** | Rõ | Vẫn rõ | Không bị mất âm |

#### 4. Mức Độ Giảm (Reduction Levels)

```bash
--reduction 30  # Nhẹ nhàng (3dB)
├─ Giảm 30% energy
├─ Vẫn nghe thấy một chút "gắt"
└─ Phù hợp: Audio chất lượng cao, chỉ cần polish nhẹ

--reduction 40  # Trung bình (4.5dB)
├─ Giảm 40% energy
├─ Cân bằng giữa natural và smooth
└─ Phù hợp: Hầu hết trường hợp thu âm thông thường

--reduction 50  # Mạnh (6dB)
├─ Giảm 50% energy
├─ Âm T rất mềm mại
└─ Phù hợp: Audio có nhiều âm T gắt, cần xử lý mạnh
```

#### 5. Ví Dụ Thực Tế

**Use case**: Podcast tiếng Việt
```
Input:  "Tôi thích trong trường này"
        ↑ Âm T gây khó chịu khi nghe lâu

Output: "Tôi thích trong trường này"
        ↑ Âm T tự nhiên, nghe thoải mái
        
Kết quả: Listener có thể nghe podcast 1 giờ mà không mỏi tai
```

**Không ảnh hưởng**: Các âm khác trong câu nói

Module chỉ xử lý:
- ✅ Âm T (t, th, tr) ở đầu âm tiết
- ❌ KHÔNG xử lý: nguyên âm (a, e, i, o, u)
- ❌ KHÔNG xử lý: phụ âm khác (n, m, l, v, etc.)
- ❌ KHÔNG xử lý: âm T ở cuối từ (như "mát", "học")

**Ví dụ**:
```
Input:  "Tôi ăn cơm trong nhà"
         ↑       ↑     ↑
       Xử lý   Giữ   Xử lý
       
Output: Chỉ "T" và "tr" được làm mềm,
        "ăn", "cơm", "nhà" giữ nguyên 100%
```

---

## 📚 Tham Khảo

- Vietnamese Phonetics - Wikipedia
- Acoustic characteristics of Vietnamese consonants
- iZotope De-plosive algorithm (tham khảo)

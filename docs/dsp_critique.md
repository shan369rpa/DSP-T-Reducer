# 📉 DSP Critique: Phân Tích Kỹ Thuật Module T-Reducer Basic

> **Mục tiêu**: Phân tích thẳng thắn các giới hạn của thuật toán hiện tại dưới góc độ Professional DSP

---

## 1. Phase Coherence & Transient Smearing

### Vấn đề: Linear Phase Destruction
Module hiện tại sử dụng STFT (Short-Time Fourier Transform) để can thiệp vào magnitude spectrum và reconstruct lại bằng phase gốc:
```python
stft_reduced = magnitude_reduced * np.exp(1j * phase)
processed = librosa.istft(stft_reduced)
```

**Tại sao đây là bad practice cho transients (âm T):**
- Transients (âm nổ) được định hình bởi mối quan hệ pha cực kỳ chính xác giữa các tần số.
- Khi bạn giảm magnitude của một dải tần (4-8kHz) một cách đột ngột trong Frequency Domain mà **không điều chỉnh Phase tương ứng**, bạn tạo ra sự lệch pha.
- **Hậu quả**: Cú "burst" sắc nét của âm T bị "bôi nhòe" (smearing) trong miền thời gian. Nghe sẽ thấy âm T bị "thiếu lực" (weak) hoặc có cảm giác "xẹt xẹt" không tự nhiên (pre-echo artifacts).

### Professional Approach
- Sử dụng **Minimum Phase filters** hoặc **Linear Phase EQ** nếu muốn clean.
- Hoặc tốt hơn: Chỉ dùng FFT để *detect*, sau đó dùng Time-Domain Filters (như IIR Bi-quad filters) để xử lý tín hiệu. Điều này bảo toàn độ chặt chẽ của transient.

---

## 2. Threshold Detection: The "Gain Staging" Problem

### Vấn đề: Hardcoded Absolute Thresholds
```python
self.flux_threshold = 0.4
t_mask = (flux_norm > self.flux_threshold)
```
Code hiện tại dùng ngưỡng tuyệt đối (`0.4`). Flux phụ thuộc vào biên độ tín hiệu.

**Hệ quả:**
- File thu âm nhỏ (-20dB): Flux sẽ rất bé → **Không detect được gì (False Negative)**.
- File thu âm lớn (-3dB): Flux sẽ rất lớn → **Detect nhầm lung tung (False Positive)**.
- User buộc phải chuẩn hóa (Normalize) audio đầu vào thủ công mới dùng được tool.

### Professional Approach
- **Adaptive Threshold**: Ngưỡng phải là tương đối (Relative). Ví dụ: "Flux phải lớn hơn trung bình động (Moving Average) 10dB".
- **Input Normalization**: Tự động đo độ lớn đầu vào (LUFS/RMS) và scale threshold theo đó.

---

## 3. Frequency Targeting: "One Size Fits None"

### Vấn đề: Hardcoded 4kHz - 8kHz Range
```python
self.t_freq_low = 4000
self.t_freq_high = 8000
```
Giả định rằng mọi âm T của mọi người đều nằm ở đây là sai lầm.

**Thực tế:**
- **Giọng nam trầm (Deep male)**: Burst có thể xuống tới **2.5kHz**. Nếu chỉ cắt từ 4kHz, bạn bỏ lỡ phần năng lượng chính → Giảm không hiệu quả.
- **Giọng nữ/trẻ em**: Burst có thể lên tới **10-12kHz**. Cắt ở 8kHz là vô nghĩa.
- **Âm "Tr" vs "Th"**: "Tr" thường thấp hơn "T". Hardcode tần số làm mất khả năng xử lý tinh tế từng loại âm.

### Professional Approach
- **Spectral Centroid / Peak Tracking**: Thuật toán tự tìm "đỉnh" (peak) năng lượng của từng cú burst.
- Nếu detect được burst ở 3kHz, tự động dời filter xuống 3kHz.

---

## 4. Envelope Smoothing: The "Robotic" Feel

### Vấn đề: Linear Smoothing & Block Processing
```python
# Block processing theo từng frame STFT (nhảy cóc 11ms mỗi lần)
uniform_filter1d(gain_reduction)
```

**Hệ quả:**
- **Grainy sound**: Vì xử lý theo từng cục (frame), sự thay đổi gain không liên tục từng sample.
- **Linear release**: Âm thanh tự nhiên tắt dần theo hàm mũ (Logarithmic). Dùng linear smoothing nghe rất gượng ép.

### Professional Approach
- **Sample-accurate processing**: Nếu có thể, tính toán gain cho từng sample (hoặc upsample control signal).
- **Logarithmic Attack/Release**: Mô phỏng behavior của thiết bị Analog (Opto/FET compressors).

---

## 🚀 Kết luận
Phiên bản Basic chỉ là "Proof of Concept". Để dùng cho production (phim, broadcast), cần viết lại v2.0 focus vào:
1. **Adaptive Detection** (Tự thích nghi gain).
2. **Frequency Tracking** (Tự tìm tần số).
3. **Natural Smoothing** (Xử lý mượt mà).

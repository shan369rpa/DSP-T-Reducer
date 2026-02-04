# 🔬 Technical Audit Report: T-Reducer DSP Module

> **Auditor Role**: Senior DSP Engineer  
> **Date**: 2026-02-04  
> **Subject**: Gap Analysis giữa Implementation hiện tại và Industry/Academic Standards

---

## 📋 Executive Summary

Dự án `t_reducer.py` hiện tại đang ở mức **Proof-of-Concept (PoC)** với nhiều giới hạn kỹ thuật nghiêm trọng khi so sánh với các chuẩn công nghiệp (iZotope RX11) và các thuật toán học thuật (Wavelet, HMM). Báo cáo này phân tích chi tiết các GAP và đề xuất lộ trình nâng cấp.

---

## 🔴 CRITICAL GAPS (Lỗi Nghiêm Trọng)

### Gap 1: Sử Dụng STFT Thuần Túy - Thiếu Wavelet Analysis

| Khía cạnh | Implementation Hiện Tại | Chuẩn Công Nghiệp (RX/Academic) |
|-----------|-------------------------|----------------------------------|
| **Transform** | STFT (`librosa.stft`) | Wavelet Transform (DWT/CWT) |
| **Time Resolution** | Cố định (~11ms/frame với hop=512) | Thích ứng (cao ở high-freq, thấp ở low-freq) |
| **Transient Localization** | Kém (bị windowing blur) | Xuất sắc (multi-resolution) |

**Tại sao đây là vấn đề?**

Theo nguồn `plusk01/ecen671-book-matlab`, Wavelet Transform cho phép phân tích **multi-resolution**:
- High frequencies → High time resolution (cần cho transient như "t")
- Low frequencies → High frequency resolution

Code hiện tại dùng STFT với window size cố định 2048 samples (~46ms tại 44.1kHz). Điều này tạo ra **temporal smearing** cho các transient ngắn như âm "t" chỉ kéo dài 5-20ms.

**Hậu quả thực tế:**
- Detection bị trễ (late detection)
- Reduction áp dụng lên cả phần nguyên âm sau "t"
- Âm thanh nghe "nghẹt" hoặc "bóp"

---

### Gap 2: Detection Dựa Trên Spectral Flux - Thiếu Zero Crossing Rate (ZCR)

| Khía cạnh | Implementation Hiện Tại | Chuẩn (nuniz/speech-audio-ml) |
|-----------|-------------------------|-------------------------------|
| **Detection Method** | Spectral Flux + Energy Ratio | ZCR + Energy + Spectral Features |
| **Voiced/Unvoiced Classification** | Không có | Có (ZCR là key feature) |
| **Robustness** | Thấp (dễ false positive) | Cao (kết hợp nhiều features) |

**Phân tích kỹ thuật:**

Âm "t" là **âm vô thanh (unvoiced)**. Đặc trưng quan trọng nhất để phân biệt nó với các âm khác là **Zero Crossing Rate (ZCR)** cực cao.

```
Ví dụ ZCR:
- Nguyên âm "a": ZCR ~50-100 crossings/frame
- Âm "t": ZCR ~300-500 crossings/frame (CAO)
- Âm "s": ZCR ~400-600 crossings/frame (RẤT CAO)
```

Code hiện tại **KHÔNG** tính ZCR, dẫn đến:
- Không phân biệt được âm "t" với các transient khác (như tiếng gõ bàn)
- Không phân biệt được "t" với "s" (cả hai đều có high-freq burst)

---

### Gap 3: Không Có Mô Hình Ngữ Âm - Thiếu HMM/Viterbi

| Khía cạnh | Implementation Hiện Tại | Chuẩn Học Thuật (HMM) |
|-----------|-------------------------|------------------------|
| **Context Awareness** | Không (xử lý từng frame độc lập) | Có (xem xét chuỗi frames) |
| **Phoneme Modeling** | Không | Có (mô hình trạng thái cho /t/) |
| **False Positive Handling** | Kém | Tốt (probabilistic filtering) |

**Tại sao HMM quan trọng?**

Theo nguồn `plusk01/ecen671-book-matlab`, Hidden Markov Models cho phép:
1. **Mô hình hóa cấu trúc thời gian** của âm "t": Silence → Burst → Aspiration → Vowel
2. **Giảm false positives** bằng xác suất chuyển đổi trạng thái
3. **Xử lý context** (âm "t" sau "s" khác với "t" sau "a")

Code hiện tại xử lý từng frame **độc lập**, không có "bộ nhớ" về các frames trước/sau.

---

## 🟡 MODERATE GAPS (Cần Cải Thiện)

### Gap 4: Gain Reduction Không Có Lookahead

De-click của RX sử dụng **lookahead buffer** (~5-10ms) để bắt đầu giảm gain TRƯỚC KHI transient xảy ra. Code hiện tại không có tính năng này.

### Gap 5: Thiếu Interpolation/Inpainting

De-click của RX không chỉ "giảm volume" mà còn **nội suy (interpolate)** lại tín hiệu bị hư bằng các kỹ thuật như:
- Cubic spline interpolation
- AR (Autoregressive) prediction
- Spectral inpainting

Code hiện tại chỉ đơn thuần nhân magnitude với hệ số < 1, không có reconstruction.

### Gap 6: Thiếu Pre-emphasis Filter

Theo `minthanthtoo/signal-processing-roadmap`, pre-emphasis filter (`y[n] = x[n] - α*x[n-1]`) giúp boost high-frequency trước khi analysis, cải thiện detection cho các âm như "t", "s".

---

## 🟢 ĐIỂM MẠNH HIỆN TẠI

1. **Adaptive Thresholding**: Đã implement (tốt hơn fixed threshold).
2. **Spectral Centroid Tracking**: Đã implement (tốt hơn fixed frequency band).
3. **FCP Timecode Export**: Feature hữu ích cho workflow video.
4. **Modular Python Code**: Dễ mở rộng.

---

## 📊 PRIORITY MATRIX

| Improvement | Impact | Effort | Priority |
|-------------|--------|--------|----------|
| Add ZCR feature | HIGH | LOW | **P0** |
| Implement Wavelet Detection | HIGH | HIGH | **P1** |
| Add Lookahead Buffer | MEDIUM | LOW | **P1** |
| Pre-emphasis Filter | MEDIUM | LOW | **P2** |
| HMM/Viterbi (Full Phoneme Model) | HIGH | VERY HIGH | **P3** (Future) |
| Spectral Inpainting | MEDIUM | HIGH | **P3** (Future) |

---

## 🚀 RECOMMENDED ROADMAP

### Phase 1: Quick Wins (1-2 ngày)
- [ ] Thêm ZCR vào detection logic (tách voiced/unvoiced)
- [ ] Thêm Pre-emphasis filter trước STFT
- [ ] Implement Lookahead buffer (5ms)

### Phase 2: Core Upgrade (1 tuần)
- [ ] Thay thế STFT bằng DWT (Discrete Wavelet Transform) cho detection
- [ ] Giữ STFT cho processing (hoặc chuyển sang time-domain filtering)

### Phase 3: Advanced (Tương lai)
- [ ] Tích hợp HMM cho phoneme-aware detection
- [ ] Spectral inpainting thay vì gain reduction

---

## 📚 Tài Liệu Tham Khảo

1. [plusk01/ecen671-book-matlab](https://github.com/plusk01/ecen671-book-matlab) - Wavelet, HMM, Viterbi
2. [nuniz/speech-audio-ml-interview](https://github.com/nuniz/speech-audio-ml-interview) - ZCR, MFCC, Speech Features
3. [BillyDM/awesome-audio-dsp](https://github.com/BillyDM/awesome-audio-dsp) - Curated DSP resources
4. [openlists/DSPResources](https://github.com/openlists/DSPResources) - Open DSP learning
5. [minthanthtoo/signal-processing-roadmap](https://github.com/minthanthtoo/signal-processing-roadmap) - Python signal processing
6. [ampl/gsl](https://github.com/ampl/gsl) - GNU Scientific Library (FFT, Wavelets)

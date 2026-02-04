# 🔬 Phân Tích Âm "T" Tiếng Việt - Chi Tiết DSP

> **Focus duy nhất**: Âm **t, th, tr** đầu âm tiết trong: tu, thì, ta, trong, trên

---

## 📊 Phần 1: Đặc Tính Ngữ Âm Của Âm T

### 1.1. Ba Biến Thể Của Âm T Trong Tiếng Việt

| Chữ | Phiên Âm IPA | Tên Gọi | Ví Dụ |
|-----|--------------|---------|-------|
| **t** | /t̪/ | Voiceless unaspirated denti-alveolar plosive | tu, ta |
| **th** | /t̪ʰ/ | Voiceless aspirated denti-alveolar plosive | thì, thầy |
| **tr** | /ʈ͡ʂ/ | Voiceless retroflex affricate | trong, trên |

### 1.2. Cách Phát Âm

```
Âm "t" (tu, ta):
┌──────────────────────────────────┐
│ 1. Đầu lưỡi chạm vào phía sau    │
│    răng trên (denti-alveolar)    │
│ 2. Tích áp suất trong miệng      │
│ 3. Thả đột ngột → BURST          │
│ 4. KHÔNG có hơi thở sau burst    │
└──────────────────────────────────┘

Âm "th" (thì, thầy):
┌──────────────────────────────────┐
│ 1. Giống như "t"                 │
│ 2. SAU burst có ASPIRATION       │
│    (hơi thở mạnh ~40-80ms)       │
│ 3. Rồi mới đến nguyên âm         │
└──────────────────────────────────┘

Âm "tr" (trong, trên):
┌──────────────────────────────────┐
│ 1. Đầu lưỡi cuộn lên (retroflex) │
│ 2. Burst + FRICATION (kéo dài)   │
│ 3. Giống âm "ch" + "r" gộp       │
└──────────────────────────────────┘
```

---

## 📈 Phần 2: Đặc Tính Tần Số (Frequency Characteristics)

### 2.1. Tại Sao Âm T Nghe "Gắt"?

Âm T có **burst energy tập trung ở high frequency** (>4kHz), đúng vùng tai người nhạy cảm nhất:

```
Frequency (Hz)
    8k |   ******* ← Burst energy của /t/
    6k |  *********
    4k | ***********
    2k |************
    1k |************ ← Formant của vowel sau
   500 |************
       |____________
         Burst | Vowel
```

### 2.2. Phân Biệt T, TH, TR Trên Spectrogram

```
╔═══════════════════════════════════════════════════════════╗
║              SPECTROGRAM PATTERNS                          ║
╠═══════════════════════════════════════════════════════════╣
║                                                            ║
║  "ta" (/t̪a/):                                             ║
║  |     |                                                   ║
║  |BURST|----Vowel "a" formants------                       ║
║  |  ↓  |                                                   ║
║  [Spike][Periodic waves]                                   ║
║                                                            ║
║  "thì" (/t̪ʰì/):                                           ║
║  |     |        |                                          ║
║  |BURST|ASPIRATION|----Vowel "ì"----                       ║
║  |  ↓  |   ↓    |                                          ║
║  [Spike][Noise  ][Periodic waves]                          ║
║         ~40-80ms                                           ║
║                                                            ║
║  "trong" (/ʈ͡ʂoŋ/):                                        ║
║  |     |           |                                       ║
║  |BURST|FRICATION  |----Vowel "ong"----                    ║
║  |  ↓  |    ↓     |                                        ║
║  [Spike][Noise    ][Periodic waves]                        ║
║         (kéo dài, lower freq than "th")                    ║
║                                                            ║
╚═══════════════════════════════════════════════════════════╝
```

### 2.3. Frequency Ranges Cụ Thể

| Component | Frequency Range | Duration | Đặc Điểm |
|-----------|-----------------|----------|----------|
| **Burst (t, th, tr)** | 4,000 - 8,000 Hz | 5-15 ms | Spike đột ngột |
| **Aspiration (th)** | 2,000 - 6,000 Hz | 40-80 ms | Noise after burst |
| **Frication (tr)** | 2,000 - 4,000 Hz | 20-40 ms | Lower freq than "th" |

---

## 🔧 Phần 3: DSP Detection Algorithm

### 3.1. Thuật Toán Detect Âm T

```
ALGORITHM: Detect_T_Sound(audio)

INPUT: audio signal
OUTPUT: list of (start_time, end_time, type) tuples

1. STFT(audio) → spectrogram
2. For each frame:
   a. Calculate spectral_flux (rate of change)
   b. Calculate high_freq_energy (>4kHz) / total_energy
   
3. Detect BURST:
   - spectral_flux > threshold_flux AND
   - high_freq_ratio > threshold_ratio AND
   - preceded by low energy (silence/low amplitude)
   
4. Classify Type:
   - If aspiration_energy > threshold → "th"
   - If frication_duration > threshold → "tr"  
   - Else → "t"
   
5. Return detected events
```

### 3.2. Python Code

```python
import numpy as np
import librosa

def detect_t_sounds(audio, sr):
    """
    Detect T sounds (t, th, tr) in Vietnamese speech
    
    Returns:
        List of (start_frame, end_frame, type) tuples
    """
    # STFT
    n_fft = 2048
    hop_length = 512
    stft = librosa.stft(audio, n_fft=n_fft, hop_length=hop_length)
    magnitude = np.abs(stft)
    
    # Frequency bins
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    
    # High-freq mask (>4kHz for T burst)
    high_mask = freqs > 4000
    
    # Calculate features per frame
    high_energy = np.sum(magnitude[high_mask, :] ** 2, axis=0)
    total_energy = np.sum(magnitude ** 2, axis=0) + 1e-10
    high_ratio = high_energy / total_energy
    
    # Spectral flux (change between frames)
    flux = np.sum(np.abs(np.diff(magnitude, axis=1)), axis=0)
    flux = np.concatenate([[0], flux])  # Pad
    flux_norm = flux / (np.max(flux) + 1e-10)
    
    # Detect bursts
    burst_threshold = 0.5
    ratio_threshold = 0.3
    
    burst_frames = (flux_norm > burst_threshold) & (high_ratio > ratio_threshold)
    
    # Find burst positions
    t_sounds = []
    for i, is_burst in enumerate(burst_frames):
        if is_burst:
            t_sounds.append({
                'frame': i,
                'time': i * hop_length / sr,
                'high_ratio': high_ratio[i],
                'flux': flux_norm[i]
            })
    
    return t_sounds
```

---

## 📉 Phần 4: Reduction Algorithm

### 4.1. Chiến Lược Giảm Âm T

```
STRATEGY: Reduce_T_Harshness

Mục tiêu: Giảm "gắt" 30-50% MÀ vẫn nghe rõ âm T

Cách tiếp cận:
1. Detect burst frames của âm T
2. Trong burst frames, GIẢM energy ở vùng 4-8kHz
3. KHÔNG giảm toàn bộ energy (sẽ mất âm T)
4. Smooth transition để tránh artifacts

Tham số:
- reduction_db: 3-6 dB (tương đương 30-50%)
- freq_range: 4000-8000 Hz
- transition_frames: 2-3 frames
```

### 4.2. Python Implementation

```python
def reduce_t_harshness(audio, sr, reduction_percent=50):
    """
    Reduce harshness of T sounds (t, th, tr)
    
    Args:
        audio: Input audio
        sr: Sample rate
        reduction_percent: 30, 40, or 50
        
    Returns:
        Processed audio
    """
    # Convert percent to dB
    reduction_db = reduction_percent / 10 * 1.2  # 50% → 6dB
    
    # STFT
    n_fft = 2048
    hop_length = 512
    stft = librosa.stft(audio, n_fft=n_fft, hop_length=hop_length)
    magnitude = np.abs(stft)
    phase = np.angle(stft)
    
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    
    # T-burst frequency range
    t_freq_mask = (freqs >= 4000) & (freqs <= 8000)
    
    # Detect T sounds
    t_sounds = detect_t_sounds(audio, sr)
    
    # Create gain reduction mask
    magnitude_reduced = magnitude.copy()
    reduction_linear = 10 ** (-reduction_db / 20)
    
    for t in t_sounds:
        frame = t['frame']
        
        # Apply reduction to burst frequencies
        # With smooth transition
        for offset in [-1, 0, 1]:
            f = frame + offset
            if 0 <= f < magnitude.shape[1]:
                # Reduce high-freq energy
                weight = 1.0 if offset == 0 else 0.5  # Center frame gets full reduction
                gain = 1 - weight * (1 - reduction_linear)
                magnitude_reduced[t_freq_mask, f] *= gain
    
    # Reconstruct
    stft_reduced = magnitude_reduced * np.exp(1j * phase)
    processed = librosa.istft(stft_reduced, hop_length=hop_length, length=len(audio))
    
    return processed
```

---

## 🎯 Phần 5: Voice Onset Time (VOT) - Phân Biệt T, TH, TR

### 5.1. VOT Là Gì?

**Voice Onset Time** = Thời gian từ BURST đến khi dây thanh rung (vowel bắt đầu)

```
Timeline:
        BURST         VOWEL STARTS
          ↓               ↓
──────────|───────────────|──────────
          |←───── VOT ────→|
          
/t/:  VOT ≈ 0-20 ms  (ngắn, voicing gần như ngay sau burst)
/th/: VOT ≈ 40-80 ms (dài, có aspiration ở giữa)
/tr/: VOT ≈ 20-40 ms (có frication ở giữa)
```

### 5.2. Detect VOT Để Classify

```python
def classify_t_type(audio, sr, burst_frame):
    """
    Classify T sound as 't', 'th', or 'tr' based on VOT
    """
    n_fft = 2048
    hop_length = 512
    
    stft = librosa.stft(audio, n_fft=n_fft, hop_length=hop_length)
    magnitude = np.abs(stft)
    
    # Measure energy in frames after burst
    post_burst_frames = 5  # ~58ms at hop=512, sr=44100
    
    # Aspiration/frication detection
    mid_freq_mask = (freqs >= 2000) & (freqs <= 6000)
    low_freq_mask = freqs < 500  # Voicing energy
    
    aspiration_scores = []
    voicing_scores = []
    
    for i in range(post_burst_frames):
        frame = burst_frame + i + 1
        if frame < magnitude.shape[1]:
            aspiration_scores.append(np.mean(magnitude[mid_freq_mask, frame]))
            voicing_scores.append(np.mean(magnitude[low_freq_mask, frame]))
    
    # Find when voicing starts (VOT)
    voicing_threshold = np.max(voicing_scores) * 0.5
    vot_frames = 0
    for i, v in enumerate(voicing_scores):
        if v > voicing_threshold:
            vot_frames = i
            break
    
    vot_ms = vot_frames * hop_length / sr * 1000
    
    # Classify
    if vot_ms > 50:
        return 'th'  # Long VOT = aspirated
    elif vot_ms > 25:
        return 'tr'  # Medium VOT = affricate
    else:
        return 't'   # Short VOT = unaspirated
```

---

## 📊 Phần 6: Visualization & Debugging

### 6.1. Plot Spectrogram Với T Detection

```python
import matplotlib.pyplot as plt

def visualize_t_detection(audio, sr, t_sounds):
    """Visualize T sound detection on spectrogram"""
    
    stft = librosa.stft(audio)
    mag_db = librosa.amplitude_to_db(np.abs(stft))
    
    plt.figure(figsize=(14, 6))
    
    # Spectrogram
    librosa.display.specshow(mag_db, sr=sr, x_axis='time', y_axis='hz')
    plt.colorbar(label='dB')
    
    # Mark T sounds
    for t in t_sounds:
        plt.axvline(x=t['time'], color='red', linestyle='--', alpha=0.7)
        plt.text(t['time'], 8000, 'T', color='red', fontsize=12)
    
    # Highlight T-burst frequency range
    plt.axhspan(4000, 8000, alpha=0.1, color='red', label='T-burst range')
    
    plt.ylim(0, 10000)
    plt.title('Spectrogram với T Sound Detection')
    plt.legend()
    plt.tight_layout()
    plt.savefig('t_detection.png', dpi=150)
    plt.show()
```

---

## 🏃 Phần 7: Bài Tập Thực Hành

### Bài 1: Record và Phân Tích

```
1. Record câu: "Tôi thì trong trên ta"
2. Load vào Python
3. Chạy detect_t_sounds()
4. Visualize kết quả
5. So sánh với manual annotation
```

### Bài 2: Test Reduction

```
1. Record câu có nhiều âm T
2. Chạy reduce_t_harshness() với reduction=50
3. Nghe so sánh trước/sau
4. Điều chỉnh parameters nếu cần
```

### Bài 3: Classify T Types

```
1. Record "ta" (t), "thì" (th), "trong" (tr)
2. Detect và classify mỗi âm
3. Verify kết quả
4. Điều chỉnh thresholds nếu sai
```

---

## 📚 Tham Khảo

- [Vietnamese Phonology - Wikipedia](https://en.wikipedia.org/wiki/Vietnamese_phonology)
- [Acoustic Phonetics - EdUHK](https://www.eduhk.hk/)
- [Librosa Documentation](https://librosa.org/)

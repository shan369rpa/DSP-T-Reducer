# 🔬 Nguyên Lý DSP Của iZotope RX Áp Dụng Cho Âm T

> **Mục tiêu**: Hiểu cách các module iZotope (De-click, De-plosive, Deconstruct) hoạt động và áp dụng cho âm T tiếng Việt

---

## 📖 Tổng Quan

iZotope RX sử dụng các thuật toán DSP phức tạp để xử lý audio. Tài liệu này phân tích **nguyên lý hoạt động** của 3 modules liên quan đến âm T:

| Module | Mục Đích Gốc | Áp Dụng Cho Âm T |
|--------|--------------|------------------|
| **De-plosive** | Giảm pop/thump từ p,b,t,d,k,g | ✅ Trực tiếp - core module |
| **De-click** | Loại bỏ clicks/pops | ⚡ Gián tiếp - detect transients |
| **Deconstruct** | Tách tonal/noise/transient | ⚡ Gián tiếp - isolate burst |

---

## 🎚️ Module 1: De-plosive

### Nguyên Lý Hoạt Động

```
De-plosive = DETECTION + SELECTIVE ATTENUATION

┌─────────────────────────────────────────────────────────────┐
│                    DE-PLOSIVE ALGORITHM                      │
└─────────────────────────────────────────────────────────────┘

Input Audio
    ↓
┌─────────────────────┐
│ 1. BAND-PASS FILTER │  ← Isolate 20-300Hz (plosive range)
│    20Hz - 300Hz     │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ 2. ENVELOPE FOLLOWER│  ← Track amplitude over time
│    Attack: fast     │
│    Release: slow    │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ 3. THRESHOLD DETECT │  ← If envelope > threshold → plosive
│    Sensitivity ctrl │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ 4. GAIN REDUCTION   │  ← Apply attenuation
│    Strength control │
│    Only to detected │
└─────────────────────┘
    ↓
Output Audio (plosive reduced)
```

### DSP Chi Tiết

#### Bước 1: Band-pass Filter (Lọc Dải Tần)

```python
from scipy import signal

def bandpass_filter(audio, sr, low_freq=20, high_freq=300):
    """
    Lọc lấy vùng tần số plosive (20-300Hz)
    
    Plosive /t/ có energy burst ở low-freq này
    khi phát âm, air pressure tạo ra "thump"
    """
    nyquist = sr / 2
    low = low_freq / nyquist
    high = high_freq / nyquist
    
    # Butterworth bandpass filter
    b, a = signal.butter(4, [low, high], btype='band')
    filtered = signal.filtfilt(b, a, audio)
    
    return filtered
```

**Tại sao 20-300Hz?**
- Plosive burst tạo ra **low-frequency "thump"**
- Microphone bị "hit" bởi air pressure
- Energy tập trung ở vùng này gây ra cảm giác "gắt"

#### Bước 2: Envelope Follower

```python
import numpy as np

def envelope_follower(audio, sr, attack_ms=1, release_ms=50):
    """
    Theo dõi biên độ theo thời gian
    
    Attack nhanh: phát hiện transient ngay lập tức
    Release chậm: smooth out để không bị "pumping"
    """
    # Convert ms to samples
    attack_samples = int(attack_ms / 1000 * sr)
    release_samples = int(release_ms / 1000 * sr)
    
    # Compute envelope
    abs_audio = np.abs(audio)
    envelope = np.zeros_like(abs_audio)
    
    for i in range(1, len(abs_audio)):
        if abs_audio[i] > envelope[i-1]:
            # Attack: ramp up quickly
            alpha = 1 - np.exp(-1 / attack_samples)
            envelope[i] = envelope[i-1] + alpha * (abs_audio[i] - envelope[i-1])
        else:
            # Release: ramp down slowly
            alpha = 1 - np.exp(-1 / release_samples)
            envelope[i] = envelope[i-1] + alpha * (abs_audio[i] - envelope[i-1])
    
    return envelope
```

#### Bước 3: Threshold Detection

```python
def detect_plosives(envelope, threshold=0.5):
    """
    Phát hiện plosive dựa trên envelope vượt threshold
    
    iZotope gọi parameter này là "Sensitivity"
    - Cao hơn = detect nhiều hơn (có thể false positives)
    - Thấp hơn = chỉ detect strong plosives
    """
    plosive_mask = envelope > threshold * np.max(envelope)
    return plosive_mask
```

#### Bước 4: Selective Gain Reduction

```python
def apply_reduction(audio, plosive_mask, reduction_db=6):
    """
    Chỉ giảm gain ở những nơi detect được plosive
    
    iZotope gọi parameter này là "Strength"
    """
    reduction_linear = 10 ** (-reduction_db / 20)
    
    output = audio.copy()
    output[plosive_mask] *= reduction_linear
    
    return output
```

### Áp Dụng Cho Âm T Tiếng Việt

```
Âm T tiếng Việt có 2 components cần xử lý:

1. LOW-FREQ THUMP (20-300Hz):
   - De-plosive xử lý trực tiếp phần này
   - Giảm cảm giác "bồm bộp" khi phát âm t,th,tr
   
2. HIGH-FREQ BURST (4-8kHz):
   - De-plosive KHÔNG xử lý phần này
   - Cần module bổ sung (xem phần Custom Implementation)
```

---

## 🔊 Module 2: De-click

### Nguyên Lý Hoạt Động

```
De-click = TRANSIENT DETECTION + INTERPOLATION REPAIR

┌─────────────────────────────────────────────────────────────┐
│                    DE-CLICK ALGORITHM                        │
└─────────────────────────────────────────────────────────────┘

Input Audio
    ↓
┌─────────────────────┐
│ 1. DERIVATIVE       │  ← Tính đạo hàm (rate of change)
│    d(sample)/dt     │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ 2. PEAK DETECTION   │  ← Tìm sudden spikes
│    Threshold based  │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ 3. WIDTH ANALYSIS   │  ← Phân biệt click vs. legitimate sound
│    Click = very short│
└─────────────────────┘
    ↓
┌─────────────────────┐
│ 4. INTERPOLATION    │  ← Thay thế click bằng interpolated value
│    Cubic spline     │
└─────────────────────┘
    ↓
Output Audio (click removed)
```

### DSP Chi Tiết

#### Transient Detection Bằng Spectral Flux

```python
import librosa
import numpy as np

def detect_transients_spectral_flux(audio, sr):
    """
    Spectral Flux = Đo sự thay đổi phổ tần giữa các frames
    
    Transient (như T burst) → Spectral flux CAO
    Steady sound (nguyên âm) → Spectral flux THẤP
    """
    # STFT
    stft = librosa.stft(audio, n_fft=2048, hop_length=512)
    magnitude = np.abs(stft)
    
    # Spectral flux = sum of positive differences
    flux = np.zeros(magnitude.shape[1])
    for i in range(1, magnitude.shape[1]):
        diff = magnitude[:, i] - magnitude[:, i-1]
        flux[i] = np.sum(np.maximum(diff, 0))
    
    # Normalize
    flux_norm = flux / (np.max(flux) + 1e-10)
    
    return flux_norm
```

#### Áp Dụng Cho Âm T

```
De-click có thể GIÚP trong việc DETECT âm T:

1. BURST của /t/ = transient
   → Spectral flux cao tại điểm này
   → Dùng để LOCATE position của T sound
   
2. KHÔNG dùng để REMOVE burst
   → Vì burst là phần essential của âm T
   → Chỉ dùng để biết "đây là chỗ có T"
```

---

## 🎛️ Module 3: Deconstruct

### Nguyên Lý Hoạt Động

```
Deconstruct = FFT-BASED TONAL/NOISE SEPARATION

┌─────────────────────────────────────────────────────────────┐
│                   DECONSTRUCT ALGORITHM                      │
└─────────────────────────────────────────────────────────────┘

Input Audio
    ↓
┌─────────────────────┐
│ 1. STFT             │  ← Chuyển sang frequency domain
│    (Short-Time FFT) │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ 2. HARMONIC ANALYSIS│  ← Tìm harmonic patterns
│    Track pitch      │     (có pitch = tonal)
│    Track harmonics  │     (random = noise)
└─────────────────────┘
    ↓
┌─────────────────────┐
│ 3. SEPARATION       │  ← Chia thành 3 layers:
│    Tonal layer      │     - Tonal (pitched: vowels)
│    Noise layer      │     - Noise (unpitched: /s/, /t/ burst)
│    Transient layer  │     - Transient (sudden: /t/ attack)
└─────────────────────┘
    ↓
┌─────────────────────┐
│ 4. GAIN CONTROL     │  ← Điều chỉnh từng layer
│    Tonal Gain       │
│    Noise Gain       │
│    Transient Gain   │
└─────────────────────┘
    ↓
Output = Tonal + Noise + Transient (với gains mới)
```

### DSP Chi Tiết

#### Harmonic/Percussive Separation

```python
import librosa

def separate_harmonic_percussive(audio, sr):
    """
    librosa có sẵn HPSS (Harmonic-Percussive Source Separation)
    
    - Harmonic = tonal content (vowels, steady sounds)
    - Percussive = transient content (T burst!)
    """
    # Compute spectrogram
    stft = librosa.stft(audio)
    
    # Separate
    harmonic, percussive = librosa.decompose.hpss(stft)
    
    # Convert back to audio
    audio_harmonic = librosa.istft(harmonic)
    audio_percussive = librosa.istft(percussive)
    
    return audio_harmonic, audio_percussive
```

#### Áp Dụng Cho Âm T

```
Deconstruct rất HỮU ÍCH cho âm T:

1. T BURST nằm trong PERCUSSIVE layer
   → Giảm percussive gain = giảm burst energy
   
2. VOWEL sau T nằm trong HARMONIC layer
   → Giữ nguyên harmonic = preserve speech quality
   
3. WORKFLOW:
   audio → HPSS → reduce percussive 30-50% → combine → output
```

```python
def reduce_t_using_hpss(audio, sr, reduction_percent=50):
    """
    Giảm T burst bằng HPSS từ lý thuyết Deconstruct
    """
    stft = librosa.stft(audio)
    harmonic, percussive = librosa.decompose.hpss(stft)
    
    # Giảm percussive (chứa T burst)
    reduction = reduction_percent / 100
    percussive_reduced = percussive * (1 - reduction)
    
    # Combine
    stft_reduced = harmonic + percussive_reduced
    audio_reduced = librosa.istft(stft_reduced, length=len(audio))
    
    return audio_reduced
```

---

## 🔧 Tổng Hợp: Custom T-Reducer Dựa Trên 3 Modules

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              CUSTOM T-REDUCER ARCHITECTURE                   │
│         (Kết hợp nguyên lý từ 3 iZotope modules)            │
└─────────────────────────────────────────────────────────────┘

Input Audio
    ↓
╔═══════════════════════════════════════════════════════════╗
║ STAGE 1: DETECTION (từ De-click)                          ║
║ - Spectral flux → locate T burst positions                ║
║ - High-freq ratio → confirm T sound                       ║
╚═══════════════════════════════════════════════════════════╝
    ↓
╔═══════════════════════════════════════════════════════════╗
║ STAGE 2: LOW-FREQ REDUCTION (từ De-plosive)               ║
║ - Bandpass 20-300Hz                                        ║
║ - Envelope detection                                       ║
║ - Selective gain reduction                                 ║
╚═══════════════════════════════════════════════════════════╝
    ↓
╔═══════════════════════════════════════════════════════════╗
║ STAGE 3: HIGH-FREQ REDUCTION (từ Deconstruct concept)     ║
║ - STFT                                                     ║
║ - Target 4-8kHz at detected positions                      ║
║ - Reduce burst energy                                      ║
╚═══════════════════════════════════════════════════════════╝
    ↓
Output Audio (T harshness reduced 30-50%)
```

### Complete Implementation

```python
import numpy as np
import librosa
from scipy import signal

class TReducerWithModulePrinciples:
    """
    T-Reducer sử dụng nguyên lý từ:
    - De-click: Transient detection
    - De-plosive: Low-freq reduction
    - Deconstruct: Spectral separation
    """
    
    def __init__(self, sr=44100, reduction_percent=50):
        self.sr = sr
        self.reduction_db = reduction_percent / 10 * 1.2
    
    # === STAGE 1: Detection (De-click principle) ===
    def detect_t_positions(self, audio):
        """Dùng spectral flux như De-click"""
        stft = librosa.stft(audio, n_fft=2048, hop_length=512)
        magnitude = np.abs(stft)
        
        # Spectral flux
        flux = np.sum(np.abs(np.diff(magnitude, axis=1)), axis=0)
        flux = np.concatenate([[0], flux])
        flux_norm = flux / (np.max(flux) + 1e-10)
        
        # High-freq ratio để confirm
        freqs = librosa.fft_frequencies(sr=self.sr, n_fft=2048)
        high_mask = freqs > 4000
        high_energy = np.sum(magnitude[high_mask, :], axis=0)
        total_energy = np.sum(magnitude, axis=0) + 1e-10
        high_ratio = high_energy / total_energy
        
        # Combined detection
        t_mask = (flux_norm > 0.4) & (high_ratio > 0.2)
        t_frames = np.where(t_mask)[0]
        
        return t_frames
    
    # === STAGE 2: Low-freq reduction (De-plosive principle) ===
    def reduce_low_freq_thump(self, audio, t_frames):
        """Dùng bandpass + envelope như De-plosive"""
        # Bandpass filter 20-300Hz
        nyquist = self.sr / 2
        b, a = signal.butter(4, [20/nyquist, 300/nyquist], btype='band')
        low_freq = signal.filtfilt(b, a, audio)
        
        # Envelope
        envelope = np.abs(low_freq)
        
        # Reduce at T positions
        hop_length = 512
        window_samples = hop_length * 3  # 3 frames window
        reduction = 10 ** (-self.reduction_db / 20)
        
        audio_out = audio.copy()
        for frame in t_frames:
            center = frame * hop_length
            start = max(0, center - window_samples // 2)
            end = min(len(audio), center + window_samples // 2)
            
            # Smooth reduction window
            window = np.hanning(end - start)
            gain = 1 - window * (1 - reduction)
            
            # Apply to low-freq component only
            audio_out[start:end] -= low_freq[start:end] * (1 - gain)
        
        return audio_out
    
    # === STAGE 3: High-freq reduction (Deconstruct principle) ===
    def reduce_high_freq_burst(self, audio, t_frames):
        """Dùng STFT targeting như Deconstruct"""
        stft = librosa.stft(audio, n_fft=2048, hop_length=512)
        magnitude = np.abs(stft)
        phase = np.angle(stft)
        
        freqs = librosa.fft_frequencies(sr=self.sr, n_fft=2048)
        high_mask = (freqs >= 4000) & (freqs <= 8000)
        
        reduction = 10 ** (-self.reduction_db / 20)
        
        # Reduce at T positions
        for frame in t_frames:
            for offset in [-1, 0, 1]:
                f = frame + offset
                if 0 <= f < magnitude.shape[1]:
                    weight = 1.0 if offset == 0 else 0.5
                    magnitude[high_mask, f] *= 1 - weight * (1 - reduction)
        
        # Reconstruct
        stft_reduced = magnitude * np.exp(1j * phase)
        audio_out = librosa.istft(stft_reduced, length=len(audio))
        
        return audio_out
    
    # === MAIN PROCESS ===
    def process(self, audio):
        """
        Full pipeline combining all 3 module principles
        """
        # Stage 1: Detect
        t_frames = self.detect_t_positions(audio)
        print(f"Detected {len(t_frames)} T sounds")
        
        # Stage 2: Low-freq reduction (De-plosive)
        audio = self.reduce_low_freq_thump(audio, t_frames)
        
        # Stage 3: High-freq reduction (Deconstruct)
        audio = self.reduce_high_freq_burst(audio, t_frames)
        
        return audio
```

---

## 📊 So Sánh: iZotope Modules vs Custom Implementation

| Khía Cạnh | iZotope De-plosive | Custom T-Reducer |
|-----------|--------------------|--------------------|
| **Target** | All plosives (p,b,t,d,k,g) | Only T (t, th, tr) |
| **Freq range** | 20-300Hz only | 20-300Hz + 4-8kHz |
| **Detection** | Envelope-based | Spectral flux + ratio |
| **Language** | Universal | Vietnamese-optimized |
| **Control** | Sensitivity, Strength | reduction_percent |

---

## 🎯 Kết Luận

### Nguyên Lý DSP Đã Học

1. **De-plosive**: Bandpass filter + Envelope + Threshold → Selective reduction
2. **De-click**: Spectral flux → Transient detection
3. **Deconstruct**: HPSS → Separate harmonic/percussive

### Áp Dụng Cho Âm T

- **Low-freq thump (20-300Hz)**: Dùng De-plosive approach
- **High-freq burst (4-8kHz)**: Dùng Deconstruct approach (STFT reduction)
- **Detection**: Dùng De-click approach (spectral flux)

### Next Steps

1. Chạy `t_reducer.py` với sample audio
2. Compare với iZotope De-plosive (nếu có)
3. Fine-tune thresholds cho tiếng Việt

---

## 📚 Tham Khảo

- [iZotope RX Documentation](https://www.izotope.com/en/products/rx.html)
- [Librosa HPSS](https://librosa.org/doc/latest/generated/librosa.decompose.hpss.html)
- [DSPGuide - Digital Signal Processing](http://www.dspguide.com/)

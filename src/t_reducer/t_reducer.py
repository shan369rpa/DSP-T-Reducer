import pywt
import numpy as np
import librosa
import soundfile as sf
import scipy.signal as signal
from scipy.ndimage import gaussian_filter1d
import argparse
from pathlib import Path
import warnings
import csv

# Suppress warnings
warnings.filterwarnings("ignore")

class WaveletDetector:
    """
    Wavelet-based Transient Detection (Vietnamese Optimized).
    
    Why Wavelet?
    - Provides multi-resolution analysis.
    - Captures high-frequency transients (like 't' burst) with high time precision.
    - Avoids the fixed window blur of STFT.
    
    Vietnamese Optimization:
    - Uses 'db4' or 'sym4' wavelet which resembles the shape of a transient burst.
    - Focuses on Detail coefficients (cD1, cD2) where 't' energy lives (High Freqs).
    """
    
    def __init__(self, wavelet='db4', level=4, sr=44100):
        self.wavelet = wavelet
        self.level = level
        self.sr = sr
        
    def detect_transients(self, audio, sensitivity=3.0):
        """
        Detect transients using Discrete Wavelet Transform.
        
        Args:
            audio: Time-domain audio signal
            sensitivity: Threshold multiplier (higher = less sensitive)
            
        Returns:
            is_transient: Boolean mask of the same length as audio
        """
        # 1. Decompose audio
        # coeffs = [cA4, cD4, cD3, cD2, cD1]
        # cD1: Nyquist/2 -> Nyquist (e.g., 11k-22k) - High air noise
        # cD2: Nyquist/4 -> Nyquist/2 (e.g., 5.5k-11k) - T Burst core energy
        coeffs = pywt.wavedec(audio, self.wavelet, level=self.level)
        
        # 2. Reconstruct transient signal from High Frequency details only
        # We assume 't' sound is mostly in cD1 and cD2
        # Setup zero coeffs for reconstruction
        coeffs_rec = [np.zeros_like(coeffs[0])] # Zero out Approximation (Low freq)
        
        # Keep details cD1 and cD2, zero out others (cD3, cD4 are mids/low-mids)
        # Note: wavedec returns [cA, cD_level, cD_level-1, ..., cD1]
        # Index: 0=cA, 1=cD4, 2=cD3, 3=cD2, 4=cD1
        for i in range(1, len(coeffs)):
            if i >= len(coeffs) - 2: # Keep last 2 details (cD2, cD1)
                coeffs_rec.append(coeffs[i])
            else:
                coeffs_rec.append(np.zeros_like(coeffs[i]))
                
        # 3. Inverse DWT to get time-domain transient signal
        # Use 'mode'='period' to match length logic roughly, but slicing is safer
        transient_signal = pywt.waverec(coeffs_rec, self.wavelet)
        
        # Length matching (reconstruction might be slightly longer)
        if len(transient_signal) > len(audio):
            transient_signal = transient_signal[:len(audio)]
        elif len(transient_signal) < len(audio):
             transient_signal = np.pad(transient_signal, (0, len(audio) - len(transient_signal)))
            
        # 4. Energy Envelope
        transient_energy = transient_signal ** 2
        
        # 5. Adaptive Thresholding on Wavelet Energy
        # Use a local window to find spikes against background
        window_size = int(self.sr * 0.05) # 50ms window
        kernel = np.ones(window_size) / window_size
        background_floor = np.convolve(transient_energy, kernel, mode='same')
        
        # Avoid division by zero
        background_floor = np.maximum(background_floor, 1e-9)
        
        # Ratio of Instant Energy / Background
        energy_ratio = transient_energy / background_floor
        
        # Thresholding
        is_transient = energy_ratio > sensitivity
        
        return is_transient

# ============================================================
# PHASE 0 UTILS (RETAINED)
# ============================================================

def calculate_zcr(audio, frame_length=2048, hop_length=512):
    return librosa.feature.zero_crossing_rate(audio, frame_length=frame_length, hop_length=hop_length)[0]

def apply_preemphasis(audio, coeff=0.97):
    return np.append(audio[0], audio[1:] - coeff * audio[:-1])

def create_lookahead_envelope(detection_mask, lookahead_frames=5):
    extended_mask = detection_mask.copy()
    for i in range(len(detection_mask)):
        if detection_mask[i]:
            start = max(0, i - lookahead_frames)
            extended_mask[start:i] = True
    return extended_mask

# ============================================================
# CORE CLASSES
# ============================================================

class AdaptiveDetector:
    """Legacy STFT-based detector (used for freq verification)."""
    def __init__(self, sr, hop_length, frame_length=2048):
        self.sr = sr
        self.hop_length = hop_length
    
    def calculate_spectral_flux(self, magnitude):
        flux = np.sum(np.abs(np.diff(magnitude, axis=1)), axis=0)
        flux = np.concatenate([[0], flux])
        return flux

    def get_adaptive_threshold(self, metric_array, window_size=50, sensitivity=3.0):
        kernel = np.ones(window_size) / window_size
        moving_avg = np.convolve(metric_array, kernel, mode='same')
        adaptive_thresh = moving_avg * sensitivity
        adaptive_thresh = np.maximum(adaptive_thresh, np.max(metric_array) * 0.05)
        return adaptive_thresh
    
    def detect_unvoiced_regions(self, zcr, threshold=0.15):
        return zcr > threshold

class TReducerPro:
    """
    T-Reducer v4.0 (Phase 1).
    Now uses Hybrid Detection: Wavelet (Time) + STFT (Freq/Energy) + ZCR (Voicing).
    """
    
    def __init__(self, sr=44100, reduction_percent=50, fps=30, 
                 use_zcr=True, use_preemphasis=True, use_wavelet=True, lookahead_ms=5):
        self.sr = sr
        self.n_fft = 2048
        self.hop_length = 512
        self.reduction_percent = reduction_percent
        self.fps = fps
        
        # Flags
        self.use_zcr = use_zcr
        self.use_preemphasis = use_preemphasis
        self.use_wavelet = use_wavelet
        self.lookahead_frames = int(lookahead_ms / 1000 * sr / self.hop_length)
        
        # Reduction mapping
        # FIXED: Special MUTE mode
        if reduction_percent == -1:
             self.target_reduction_db = -200.0 # Silence
        elif reduction_percent >= 100:
            self.target_reduction_db = -99.0
        else:
            self.target_reduction_db = (reduction_percent / 100.0) * -99.0
            
        self.detector = AdaptiveDetector(sr, self.hop_length, self.n_fft)
        self.wavelet_detector = WaveletDetector(sr=sr)
        self.freqs = librosa.fft_frequencies(sr=sr, n_fft=self.n_fft)

    def seconds_to_timecode(self, total_seconds):
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        fraction_sec = total_seconds - int(total_seconds)
        total_frames = fraction_sec * self.fps
        frames = int(total_frames)
        fraction_frame = total_frames - frames
        subframes = int(fraction_frame * 80)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}.{subframes:02d}"

    def process_file(self, input_path, output_path):
        print(f"🔄 Loading: {Path(input_path).name}")
        # Keep native samplerate and do NOT normalize if possible, or track peak
        audio, _ = librosa.load(input_path, sr=self.sr)
        
        # Track Max Amplitude of Input to restore volume later
        input_peak = np.max(np.abs(audio))
        
        # 1. Pre-emphasis
        if self.use_preemphasis:
            print("  📈 Pre-emphasis: ON")
            audio_processed = apply_preemphasis(audio)
        else:
            audio_processed = audio
            
        # 2. Wavelet Analysis (Time Domain)
        wavelet_mask = None
        if self.use_wavelet:
            print("  🌊 Wavelet Analysis: ON (db4)")
            # FIXED: Increased sensitivity threshold to avoid capturing background noise
            # Was 5.0, now 8.0 for clearer, stronger transient detection
            wavelet_mask_sample = self.wavelet_detector.detect_transients(audio_processed, sensitivity=8.0)
            
            # Convert sample mask to frame mask to match STFT
            # Resample mask? Or just check if frame contains transient samples
            n_frames = 1 + len(audio) // self.hop_length
            wavelet_mask_frame = np.zeros(n_frames, dtype=bool)
            
            # Simple mapping: If enough samples in a frame are transient, mark frame
            # This is "downsampling" the mask
            # Optimized way: Reshape or loop with stride
            for i in range(n_frames):
                start = i * self.hop_length
                end = min(len(audio), start + self.n_fft) # Look at full window
                if np.any(wavelet_mask_sample[start:end]):
                    wavelet_mask_frame[i] = True
            
            wavelet_mask = wavelet_mask_frame
            print(f"     -> Found {np.sum(wavelet_mask)} frames with transients")
        
        # 3. Processing
        processed_audio, stats, logs = self.process_audio(audio, audio_processed, wavelet_mask)
        
        # FIXED: Volume Matching
        output_peak = np.max(np.abs(processed_audio))
        if output_peak > 0:
            # Normalize to match input peak
            processed_audio = processed_audio * (input_peak / output_peak)
            print(f"  🔊 Volume Matched: Peak restored to {input_peak:.2f}")

        sf.write(output_path, processed_audio, self.sr)
        print(f"✅ Audio saved to: {Path(output_path).name}")
        
        log_path = str(Path(output_path).with_suffix('.csv'))
        self.save_logs(logs, log_path)
        print(f"📝 Log saved to: {Path(log_path).name}")
        print(f"📊 Stats: Detected {stats['count']} events.")
        
        return stats

    def save_logs(self, logs, log_path):
        with open(log_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['FCP Timecode', 'Start(s)', 'Dur(ms)', 'Freq(Hz)', 'ZCR', 'Red(dB)'])
            for log in logs:
                writer.writerow([
                    log['timecode'],
                    f"{log['start_time']:.3f}",
                    f"{log['duration_ms']:.1f}",
                    f"{log['centroid']:.0f}",
                    f"{log.get('avg_zcr', 0):.3f}",
                    f"{log['reduction_db']:.1f}"
                ])

    def process_audio(self, audio_original, audio_analyzed, wavelet_mask=None):
        # STFT Analysis
        stft = librosa.stft(audio_analyzed, n_fft=self.n_fft, hop_length=self.hop_length)
        mag = np.abs(stft)
        
        # Original STFT for reconstruction
        stft_orig = librosa.stft(audio_original, n_fft=self.n_fft, hop_length=self.hop_length)
        mag_orig = np.abs(stft_orig)
        phase_orig = np.angle(stft_orig)
        
        n_frames = mag.shape[1]
        
        # 1. ZCR
        if self.use_zcr:
            zcr = calculate_zcr(audio_analyzed, self.n_fft, self.hop_length)
            is_unvoiced = self.detector.detect_unvoiced_regions(zcr, threshold=0.15)
        else:
            zcr = np.zeros(n_frames)
            is_unvoiced = np.ones(n_frames, dtype=bool)
            
        # 2. STFT Spectral Detection (Legacy/Secondary)
        t_band_mask = (self.freqs >= 2000) & (self.freqs <= 10000)
        t_band_energy = np.mean(mag[t_band_mask, :], axis=0)
        flux = self.detector.calculate_spectral_flux(mag)
        adaptive_thresh = self.detector.get_adaptive_threshold(t_band_energy, sensitivity=3.5)
        is_spectral_event = (t_band_energy > adaptive_thresh) & (flux > np.mean(flux)*1.5)
        
        # 3. HYBRID MERGE
        # Logic: 
        # - Wavelet finds "when it starts" (Precision)
        # - ZCR confirms "it is unvoiced" (Validation)
        # - Spectral confirms "it has high freq energy" (Validation)
        
        final_mask = np.zeros(n_frames, dtype=bool)
        
        if self.use_wavelet and wavelet_mask is not None:
            # If Wavelet says YES, and (ZCR says YES OR Spectral says YES)
            # We relax spectral requirements because Wavelet is more trusty for transients
            
            # Ensure wavelet mask matches length (padding issues)
            if len(wavelet_mask) < n_frames:
                wavelet_mask = np.pad(wavelet_mask, (0, n_frames - len(wavelet_mask)))
            elif len(wavelet_mask) > n_frames:
                wavelet_mask = wavelet_mask[:n_frames]
                
            # PRIMARY: Wavelet + ZCR
            # "Is Transient" AND "Is Unvoiced"
            final_mask = wavelet_mask & is_unvoiced
            
            # FALLBACK: If ZCR misses (some T's are subtle), check Spectral
            # final_mask = final_mask | (wavelet_mask & is_spectral_event)
        else:
            # Fallback to pure STFT logic if Wavelet disabled
            if self.use_zcr:
                final_mask = is_spectral_event & is_unvoiced
            else:
                final_mask = is_spectral_event
        
        # 4. Lookahead
        if self.lookahead_frames > 0:
            final_mask = create_lookahead_envelope(final_mask, self.lookahead_frames)
            
        # Grouping & Reduction (Same as before)
        events_indices = np.where(final_mask)[0]
        grouped_events = []
        if len(events_indices) > 0:
            current_group = [events_indices[0]]
            for i in range(1, len(events_indices)):
                if events_indices[i] == events_indices[i-1] + 1:
                    current_group.append(events_indices[i])
                else:
                    grouped_events.append(current_group)
                    current_group = [events_indices[i]]
            grouped_events.append(current_group)

        # Processing Loop
        mag_processed = mag_orig.copy()
        centroids = librosa.feature.spectral_centroid(S=mag, sr=self.sr)[0]
        logs = []
        total_freq = 0
        
        for group in grouped_events:
            start_frame = group[0]
            duration_frames = len(group)
            duration_ms = (duration_frames * self.hop_length / self.sr) * 1000
            start_time = start_frame * self.hop_length / self.sr
            timecode = self.seconds_to_timecode(start_time)
            
            avg_centroid = np.mean(centroids[group])
            avg_zcr = np.mean(zcr[group]) if self.use_zcr else 0
            total_freq += avg_centroid
            
            # Vietnamese Adaptive Duration Logic could be here
            # For now, relying on mask provided by Wavelet/ZCR which should naturally cover duration
            
            for frame_idx in group:
                f_cent = centroids[frame_idx]
                # Broadband High-end + Thump
                target_low = max(1000, f_cent - 2000)
                main_mask = (self.freqs >= target_low) & (self.freqs <= self.sr/2)
                thump_mask = (self.freqs >= 50) & (self.freqs <= 300)
                
                reduction = 10 ** (self.target_reduction_db / 20.0)
                mag_processed[main_mask | thump_mask, frame_idx] *= reduction
                
            logs.append({
                'timecode': timecode,
                'start_time': start_time,
                'duration_ms': duration_ms,
                'centroid': avg_centroid,
                'avg_zcr': avg_zcr,
                'reduction_db': self.target_reduction_db
            })
            
        # Reconstruction
        stft_new = mag_processed * np.exp(1j * phase_orig)
        audio_out = librosa.istft(stft_new, hop_length=self.hop_length, length=len(audio_original))
        
        stats = {'count': len(logs), 'avg_freq': total_freq/len(logs) if logs else 0}
        return audio_out, stats, logs

def main():
    parser = argparse.ArgumentParser(description="T-Reducer Pro v4.0 (Phase 1: Wavelet)")
    parser.add_argument('input', help="Input file")
    parser.add_argument('output', help="Output file")
    parser.add_argument('--reduction', type=int, default=50)
    parser.add_argument('--fps', type=int, default=30)
    parser.add_argument('--no-zcr', action='store_true')
    parser.add_argument('--no-preemphasis', action='store_true')
    parser.add_argument('--no-wavelet', action='store_true', help="Disable Wavelet detection (use legacy STFT)")
    parser.add_argument('--lookahead', type=int, default=5)
    
    args = parser.parse_args()
    if not Path(args.input).exists():
        print("❌ Input not found"); return
        
    print("🌊 T-Reducer Pro v4.0 - Wavelet Edition")
    reducer = TReducerPro(
        reduction_percent=args.reduction, fps=args.fps,
        use_zcr=not args.no_zcr, use_preemphasis=not args.no_preemphasis,
        use_wavelet=not args.no_wavelet, lookahead_ms=args.lookahead
    )
    reducer.process_file(args.input, args.output)

if __name__ == "__main__":
    main()

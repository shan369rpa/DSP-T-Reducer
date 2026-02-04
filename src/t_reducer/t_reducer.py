#!/usr/bin/env python3
"""
T-Reducer Professional (v3.0) - Phase 0 Audit Improvements
Advanced Adaptive DSP for Vietnamese T-Sound Reduction

New Features (Based on Technical Audit):
- Zero Crossing Rate (ZCR) for voiced/unvoiced classification
- Pre-emphasis filter for improved high-freq detection
- Lookahead buffer for transient-aware processing
- FCP Subframe Timecode logging

Author: DSP Learning Project
"""

import numpy as np
import librosa
import soundfile as sf
import scipy.signal as signal
from scipy.ndimage import gaussian_filter1d
import argparse
from pathlib import Path
import warnings
import csv

# Suppress warnings for cleaner CLI output
warnings.filterwarnings("ignore")

# ============================================================
# PHASE 0 IMPROVEMENTS: ZCR, Pre-emphasis, Lookahead
# ============================================================

def calculate_zcr(audio, frame_length=2048, hop_length=512):
    """
    Zero Crossing Rate - Key feature for voiced/unvoiced classification.
    
    Âm "t" (unvoiced) có ZCR cao (~300-500)
    Nguyên âm (voiced) có ZCR thấp (~50-100)
    
    Returns:
        zcr: Array of ZCR values per frame
    """
    # librosa có sẵn ZCR calculation
    zcr = librosa.feature.zero_crossing_rate(
        audio, 
        frame_length=frame_length, 
        hop_length=hop_length
    )[0]
    return zcr

def apply_preemphasis(audio, coeff=0.97):
    """
    Pre-emphasis filter: y[n] = x[n] - α*x[n-1]
    
    Boosts high frequencies before analysis.
    Helps detect consonants like "t", "s", "ch" better.
    
    Args:
        audio: Input audio signal
        coeff: Pre-emphasis coefficient (default 0.97)
    
    Returns:
        emphasized: Pre-emphasized audio
    """
    emphasized = np.append(audio[0], audio[1:] - coeff * audio[:-1])
    return emphasized

def create_lookahead_envelope(detection_mask, lookahead_frames=5):
    """
    Lookahead: Start reduction BEFORE the transient hits.
    
    This prevents clicks at the start of reduction.
    
    Args:
        detection_mask: Boolean array of detected events
        lookahead_frames: Number of frames to look ahead (default 5 = ~5ms at 44.1kHz/hop512)
    
    Returns:
        extended_mask: Mask with lookahead applied
    """
    extended_mask = detection_mask.copy()
    
    # Extend each detection backwards by lookahead_frames
    for i in range(len(detection_mask)):
        if detection_mask[i]:
            start = max(0, i - lookahead_frames)
            extended_mask[start:i] = True
    
    return extended_mask

# ============================================================
# CORE CLASSES
# ============================================================

class AdaptiveDetector:
    """Enhanced detection with ZCR and Pre-emphasis."""
    
    def __init__(self, sr, hop_length, frame_length=2048):
        self.sr = sr
        self.hop_length = hop_length
        self.frame_length = frame_length
        
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
        """
        Detect unvoiced regions based on ZCR.
        High ZCR = unvoiced (t, s, ch, etc.)
        """
        return zcr > threshold

class TReducerPro:
    """T-Reducer v3.0 with Phase 0 Audit Improvements."""
    
    def __init__(self, sr=44100, reduction_percent=50, fps=30, 
                 use_zcr=True, use_preemphasis=True, lookahead_ms=5):
        self.sr = sr
        self.n_fft = 2048
        self.hop_length = 512
        self.reduction_percent = reduction_percent
        self.fps = fps
        
        # Phase 0 feature flags
        self.use_zcr = use_zcr
        self.use_preemphasis = use_preemphasis
        self.lookahead_frames = int(lookahead_ms / 1000 * sr / self.hop_length)
        
        # Reduction mapping: 100% = -99dB
        if reduction_percent >= 100:
            self.target_reduction_db = -99.0
        else:
            self.target_reduction_db = (reduction_percent / 100.0) * -99.0
            
        self.detector = AdaptiveDetector(sr, self.hop_length, self.n_fft)
        self.freqs = librosa.fft_frequencies(sr=sr, n_fft=self.n_fft)

    def seconds_to_timecode(self, total_seconds):
        """Convert seconds to FCP Timecode: HH:MM:SS:FF.SF"""
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
        audio, _ = librosa.load(input_path, sr=self.sr)
        
        # === PHASE 0: Pre-emphasis ===
        if self.use_preemphasis:
            print("  📈 Applying pre-emphasis filter...")
            audio_processed = apply_preemphasis(audio)
        else:
            audio_processed = audio
        
        # Processing
        processed_audio, stats, logs = self.process_audio(audio, audio_processed)
        
        # Saving Audio
        sf.write(output_path, processed_audio, self.sr)
        print(f"✅ Audio saved to: {Path(output_path).name}")
        
        # Saving Logs
        log_path = str(Path(output_path).with_suffix('.csv'))
        self.save_logs(logs, log_path)
        print(f"📝 Log saved to: {Path(log_path).name}")
        
        print(f"📊 Stats: Detected {stats['count']} events. Avg Freq: {stats['avg_freq']:.0f}Hz")
        if self.use_zcr:
            print(f"  🎚️ ZCR-based unvoiced detection: ENABLED")
        
        return stats

    def save_logs(self, logs, log_path):
        with open(log_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['FCP Timecode (HH:MM:SS:FF.SF)', 'Start Time (s)', 'Duration (ms)', 
                           'Centroid (Hz)', 'Avg ZCR', 'Reduction (dB)', 'Reduction (%)'])
            for log in logs:
                writer.writerow([
                    log['timecode'],
                    f"{log['start_time']:.3f}",
                    f"{log['duration_ms']:.1f}",
                    f"{log['centroid']:.0f}",
                    f"{log.get('avg_zcr', 0):.3f}",
                    f"{log['reduction_db']:.1f}",
                    f"{log['reduction_percent']}%"
                ])

    def process_audio(self, audio_original, audio_analyzed):
        """
        Process audio with Phase 0 improvements.
        
        Args:
            audio_original: Original audio (for output)
            audio_analyzed: Pre-emphasized audio (for analysis)
        """
        # === STAGE 1: ANALYSIS (on pre-emphasized audio) ===
        stft = librosa.stft(audio_analyzed, n_fft=self.n_fft, hop_length=self.hop_length)
        mag = np.abs(stft)
        
        # Get magnitude from ORIGINAL audio for processing
        stft_orig = librosa.stft(audio_original, n_fft=self.n_fft, hop_length=self.hop_length)
        mag_orig = np.abs(stft_orig)
        phase_orig = np.angle(stft_orig)
        
        # === STAGE 2: ZCR CALCULATION ===
        if self.use_zcr:
            zcr = calculate_zcr(audio_analyzed, self.n_fft, self.hop_length)
            is_unvoiced = self.detector.detect_unvoiced_regions(zcr, threshold=0.15)
            print(f"  🔍 ZCR: {np.sum(is_unvoiced)} unvoiced frames detected")
        else:
            zcr = np.zeros(mag.shape[1])
            is_unvoiced = np.ones(mag.shape[1], dtype=bool)
        
        # === STAGE 3: ADAPTIVE DETECTION ===
        t_band_mask = (self.freqs >= 2000) & (self.freqs <= 10000)
        t_band_energy = np.mean(mag[t_band_mask, :], axis=0)
        flux = self.detector.calculate_spectral_flux(mag)
        adaptive_thresh = self.detector.get_adaptive_threshold(t_band_energy, sensitivity=3.5)
        
        # Combined detection: Energy spike + Flux spike + Unvoiced (if ZCR enabled)
        is_event = (t_band_energy > adaptive_thresh) & (flux > np.mean(flux)*1.5)
        if self.use_zcr:
            is_event = is_event & is_unvoiced
        
        # === STAGE 4: LOOKAHEAD ===
        if self.lookahead_frames > 0:
            is_event = create_lookahead_envelope(is_event, self.lookahead_frames)
            print(f"  ⏪ Lookahead: {self.lookahead_frames} frames applied")
        
        # Group contiguous frames
        events_indices = np.where(is_event)[0]
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
        
        # === STAGE 5: TRACKING & REDUCTION ===
        mag_processed = mag_orig.copy()
        centroids = librosa.feature.spectral_centroid(S=mag, sr=self.sr)[0]
        
        logs = []
        total_freq = 0
        
        for group in grouped_events:
            start_frame = group[0]
            
            # Duration & Timing
            duration_frames = len(group)
            duration_sec = duration_frames * self.hop_length / self.sr
            duration_ms = duration_sec * 1000
            start_time = start_frame * self.hop_length / self.sr
            timecode = self.seconds_to_timecode(start_time)
            
            # Centroid & ZCR for this event
            group_centroids = centroids[group]
            avg_centroid = np.mean(group_centroids)
            avg_zcr = np.mean(zcr[group]) if self.use_zcr else 0
            total_freq += avg_centroid
            
            # Apply Reduction
            for frame_idx in group:
                event_centroid = centroids[frame_idx]
                
                # Broadband reduction (based on Audit)
                target_low = max(1000, event_centroid - 2000)
                target_high = self.sr / 2
                main_freq_mask = (self.freqs >= target_low) & (self.freqs <= target_high)
                
                # Low-end thump
                thump_mask = (self.freqs >= 50) & (self.freqs <= 300)
                total_mask = main_freq_mask | thump_mask
                
                reduction_linear = 10 ** (self.target_reduction_db / 20.0)
                mag_processed[total_mask, frame_idx] *= reduction_linear
            
            logs.append({
                'timecode': timecode,
                'start_time': start_time,
                'duration_ms': duration_ms,
                'centroid': avg_centroid,
                'avg_zcr': avg_zcr,
                'reduction_db': self.target_reduction_db,
                'reduction_percent': self.reduction_percent
            })

        # === STAGE 6: RECONSTRUCTION ===
        stft_new = mag_processed * np.exp(1j * phase_orig)
        audio_out = librosa.istft(stft_new, hop_length=self.hop_length, length=len(audio_original))
        
        stats = {
            'count': len(logs),
            'avg_freq': total_freq / len(logs) if logs else 0
        }
        
        return audio_out, stats, logs

def main():
    parser = argparse.ArgumentParser(
        description="T-Reducer Pro v3.0 - Phase 0 Audit Improvements (ZCR, Pre-emphasis, Lookahead)"
    )
    parser.add_argument('input', help="Input audio file")
    parser.add_argument('output', help="Output audio file")
    parser.add_argument('--reduction', type=int, default=50, help="Reduction percent (0-100)")
    parser.add_argument('--fps', type=int, default=30, help="Project Framerate (default: 30)")
    parser.add_argument('--no-zcr', action='store_true', help="Disable ZCR detection")
    parser.add_argument('--no-preemphasis', action='store_true', help="Disable pre-emphasis filter")
    parser.add_argument('--lookahead', type=int, default=5, help="Lookahead in ms (default: 5)")
    
    args = parser.parse_args()
    
    if not Path(args.input).exists():
        print("❌ Error: Input file not found.")
        return
    
    print("=" * 60)
    print("🎵 T-Reducer Pro v3.0 - Phase 0 Audit Improvements")
    print("=" * 60)
    
    reducer = TReducerPro(
        reduction_percent=args.reduction, 
        fps=args.fps,
        use_zcr=not args.no_zcr,
        use_preemphasis=not args.no_preemphasis,
        lookahead_ms=args.lookahead
    )
    reducer.process_file(args.input, args.output)
    
    print("=" * 60)
    print("✅ Done!")
    print("=" * 60)

if __name__ == "__main__":
    main()

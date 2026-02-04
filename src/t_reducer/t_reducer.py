#!/usr/bin/env python3
"""
T-Reducer Professional (v2.1)
Advanced Adaptive DSP for Vietnamese T-Sound Reduction
With Detailed CSV Logging

Features:
- Adaptive Thresholding
- Spectral Centroid Tracking
- Soft-knee Gain Staging
- Detailed CSV Logging (Timecode, Duration, Freq, Reduction)

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
import datetime

# Suppress warnings for cleaner CLI output
warnings.filterwarnings("ignore")

class AdaptiveDetector:
    """Intelligent detection system that adapts to signal floor."""
    def __init__(self, sr, hop_length):
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

class TReducerPro:
    def __init__(self, sr=44100, reduction_percent=50, fps=30):
        self.sr = sr
        self.n_fft = 2048
        self.hop_length = 512
        self.reduction_percent = reduction_percent
        self.fps = fps
        # Human-readable percent to internal gain factor
        # 0% -> 0dB
        # 100% -> -99dB (effectively mute the band)
        if reduction_percent >= 100:
            self.target_reduction_db = -99.0
        else:
            self.target_reduction_db = (reduction_percent / 100.0) * -99.0
            
        self.detector = AdaptiveDetector(sr, self.hop_length)
        self.freqs = librosa.fft_frequencies(sr=sr, n_fft=self.n_fft)

    def seconds_to_timecode(self, total_seconds):
        """
        Convert seconds to FCP Timecode: HH:MM:SS:FF.SF
        - FPS: self.fps
        - SF (Subframe): 1/80 of a frame
        """
        # 1. Calculate Hours, Minutes, Seconds
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        
        # 2. Calculate Video Frames
        # Fraction of a second remaining
        fraction_sec = total_seconds - int(total_seconds)
        total_frames = fraction_sec * self.fps
        frames = int(total_frames)
        
        # 3. Calculate Subframes (0-79)
        # Fraction of a frame remaining
        fraction_frame = total_frames - frames
        subframes = int(fraction_frame * 80)
        
        # Format: HH:MM:SS:FF.SF (using dot for subframe visualization in CSV)
        # Note: FCP usually displays HH:MM:SS:FF (then subframes if toggled)
        # We output full format for clarity
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}.{subframes:02d}"

    def process_file(self, input_path, output_path):
        print(f"🔄 Loading: {Path(input_path).name}")
        audio, _ = librosa.load(input_path, sr=self.sr)
        
        # 1. Processing
        processed_audio, stats, logs = self.process_audio(audio)
        
        # 2. Saving Audio
        sf.write(output_path, processed_audio, self.sr)
        print(f"✅ Audio saved to: {Path(output_path).name}")
        
        # 3. Saving Logs
        log_path = str(Path(output_path).with_suffix('.csv'))
        self.save_logs(logs, log_path)
        print(f"📝 Log saved to: {Path(log_path).name}")
        
        print(f"📊 Stats: Detected {stats['count']} events. Avg Freq: {stats['avg_freq']:.0f}Hz")
        
        return stats

    def save_logs(self, logs, log_path):
        """Save event logs to CSV"""
        with open(log_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Header
            writer.writerow(['FCP Timecode (HH:MM:SS:FF.SF)', 'Start Time (s)', 'Duration (ms)', 'Centroid (Hz)', 'Reduction (dB)', 'Reduction (%)'])
            # Rows
            for log in logs:
                writer.writerow([
                    log['timecode'],
                    f"{log['start_time']:.3f}",
                    f"{log['duration_ms']:.1f}",
                    f"{log['centroid']:.0f}",
                    f"{log['reduction_db']:.1f}",
                    f"{log['reduction_percent']}%"
                ])

    def process_audio(self, audio):
        # --- STAGE 1: ANALYSIS ---
        stft = librosa.stft(audio, n_fft=self.n_fft, hop_length=self.hop_length)
        mag = np.abs(stft)
        phase = np.angle(stft)
        
        # --- STAGE 2: ADAPTIVE DETECTION ---
        t_band_mask = (self.freqs >= 2000) & (self.freqs <= 10000)
        t_band_energy = np.mean(mag[t_band_mask, :], axis=0)
        flux = self.detector.calculate_spectral_flux(mag)
        adaptive_thresh = self.detector.get_adaptive_threshold(t_band_energy, sensitivity=3.5)
        
        # Create Boolean Mask
        is_event = (t_band_energy > adaptive_thresh) & (flux > np.mean(flux)*1.5)
        
        # Group contiguous frames into events (to calculate duration)
        # Use scipy.ndimage.label logic manually for pure python feel
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
            
        
        # --- STAGE 3 & 4: TRACKING & REDUCTION ---
        mag_processed = mag.copy()
        centroids = librosa.feature.spectral_centroid(S=mag, sr=self.sr)[0]
        
        logs = []
        total_freq = 0
        
        for group in grouped_events:
            # Stats for this group (event)
            start_frame = group[0]
            end_frame = group[-1]
            
            # Duration
            duration_frames = len(group)
            duration_sec = duration_frames * self.hop_length / self.sr
            duration_ms = duration_sec * 1000
            
            # Start Time
            start_time = start_frame * self.hop_length / self.sr
            timecode = self.seconds_to_timecode(start_time)
            
            # Average Centroid for this event
            group_centroids = centroids[group]
            avg_centroid = np.mean(group_centroids)
            total_freq += avg_centroid
            
            # Apply Reduction to each frame in group
            for frame_idx in group:
                event_centroid = centroids[frame_idx]
                
                # 1. Main Burst Reduction (High Mids & Highs)
                # T-sound has broad broadband noise. 
                # We should cut from slightly below centroid up to Nyquist to remove "air" harshness
                target_low = max(1000, event_centroid - 2000) # Lowered floor to 1000Hz
                target_high = self.sr / 2 # Up to Nyquist (High-end air)
                
                main_freq_mask = (self.freqs >= target_low) & (self.freqs <= target_high)
                
                # 2. Low-end Thump Reduction (Optional but effective for "Pop")
                # Plosive thump is usually 50-300Hz
                thump_mask = (self.freqs >= 50) & (self.freqs <= 300)
                
                # Combine masks
                total_mask = main_freq_mask | thump_mask
                
                reduction_linear = 10 ** (self.target_reduction_db / 20.0)
                mag_processed[total_mask, frame_idx] *= reduction_linear
            
            # Log this event
            logs.append({
                'timecode': timecode,
                'start_time': start_time,
                'duration_ms': duration_ms,
                'centroid': avg_centroid,
                'reduction_db': self.target_reduction_db,
                'reduction_percent': self.reduction_percent
            })

        # --- STAGE 5: RECONSTRUCTION ---
        stft_new = mag_processed * np.exp(1j * phase)
        audio_out = librosa.istft(stft_new, hop_length=self.hop_length, length=len(audio))
        
        stats = {
            'count': len(logs),
            'avg_freq': total_freq / len(logs) if logs else 0
        }
        
        return audio_out, stats, logs

def main():
    parser = argparse.ArgumentParser(description="Professional T-Sound Reducer (v2.2) with FCP Subframe Logging")
    parser.add_argument('input', help="Input audio file")
    parser.add_argument('output', help="Output audio file")
    parser.add_argument('--reduction', type=int, default=50, help="Reduction percent (0-100)")
    parser.add_argument('--fps', type=int, default=30, help="Project Framerate (default: 30)")
    
    args = parser.parse_args()
    
    if not Path(args.input).exists():
        print("❌ Error: Input file not found.")
        return
        
    reducer = TReducerPro(reduction_percent=args.reduction, fps=args.fps)
    reducer.process_file(args.input, args.output)

if __name__ == "__main__":
    main()

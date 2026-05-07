import numpy as np
from gnuradio import gr

class blk(gr.sync_block):
    def __init__(self, fft_size=1024, fs_beat=50000.0, chirp_bw=20e6, chirp_period=1e-3):
        gr.sync_block.__init__(
            self,
            name='Presence Detector',
            in_sig=[(np.float32, fft_size)],
            out_sig=[np.float32]
        )

        self.fft_size = fft_size
        self.fs_beat = fs_beat
        self.chirp_bw = chirp_bw
        self.chirp_period = chirp_period

        self.c = 3e8
        self.slope = chirp_bw / chirp_period

        self.noise_vals = []
        self.cal_count = 0
        self.cal_frames = 20

        self.th_on = None
        self.th_off = None

        self.state = 0
        self.detect_count = 0
        self.clear_count = 0

        self.track_bin = None
        self.track_miss = 0
        self.max_track_miss = 5

        self.last_print_range = -1.0

    def bin_to_range(self, k_est, mid):
        fb = ((k_est - mid) * self.fs_beat) / self.fft_size
        dist_m = (self.c * abs(fb)) / (2.0 * self.slope)
        return fb, dist_m

    def interp_peak(self, vec, k):
        if 1 <= k < self.fft_size - 1:
            y1 = vec[k - 1]
            y2 = vec[k]
            y3 = vec[k + 1]
            denom = 2.0 * (2.0 * y2 - y1 - y3)
            if abs(denom) > 1e-12:
                delta = (y3 - y1) / denom
                delta = max(min(delta, 0.5), -0.5)
                return k + delta
        return float(k)

    def work(self, input_items, output_items):
        vec = input_items[0][0].copy()
        mid = self.fft_size // 2

        guard_bins = 24
        vec[mid-guard_bins:mid+guard_bins] = 0

        start_bin = mid + guard_bins
        stop_bin = min(mid + 220, self.fft_size - 2)
        band = vec[start_bin:stop_bin]

        if len(band) < 5:
            output_items[0][0] = np.float32(0.0)
            return 1

        # Global peak for initial detection
        k_local = int(np.argmax(band))
        peak = float(band[k_local])
        k_global = start_bin + k_local

        # Calibration
        if self.cal_count < self.cal_frames:
            self.noise_vals.append(peak)
            self.cal_count += 1
            output_items[0][0] = np.float32(0.0)
            return 1

        if self.th_on is None:
            nf = float(np.mean(self.noise_vals))
            self.th_on = nf * 2.5
            self.th_off = nf * 1.5
            print(f"[Radar] Noise floor linear: {nf:.6f}")
            print(f"[Radar] Detect threshold: {self.th_on:.6f}")
            print(f"[Radar] Clear threshold: {self.th_off:.6f}")

        # Detection state machine
        if self.state == 0:
            if peak > self.th_on:
                self.detect_count += 1
            else:
                self.detect_count = 0

            if self.detect_count >= 3:
                self.state = 1
                self.detect_count = 0
                self.clear_count = 0
                self.track_bin = k_global
                self.track_miss = 0
                print("Detected")

        else:
            # Track near previous bin instead of jumping anywhere
            if self.track_bin is not None:
                k0 = int(round(self.track_bin))
                w = 6
                left = max(start_bin, k0 - w)
                right = min(stop_bin, k0 + w + 1)

                local_band = vec[left:right]
                if len(local_band) > 0:
                    local_idx = int(np.argmax(local_band))
                    local_peak = float(local_band[local_idx])
                    k_tracked = left + local_idx
                else:
                    local_peak = 0.0
                    k_tracked = k_global

                if local_peak > self.th_off:
                    k_use = k_tracked
                    peak_use = local_peak
                    self.track_bin = k_tracked
                    self.track_miss = 0
                else:
                    self.track_miss += 1
                    k_use = k_global
                    peak_use = peak
                    if peak > self.th_on:
                        self.track_bin = k_global

                if self.track_miss >= self.max_track_miss:
                    self.state = 0
                    self.clear_count = 0
                    self.detect_count = 0
                    self.track_bin = None
                    self.track_miss = 0
                    self.last_print_range = -1.0
                    print("Not Detected")
                    output_items[0][0] = np.float32(0.0)
                    return 1
            else:
                k_use = k_global
                peak_use = peak
                self.track_bin = k_global

            if peak_use < self.th_off:
                self.clear_count += 1
            else:
                self.clear_count = 0

            if self.clear_count >= 8:
                self.state = 0
                self.clear_count = 0
                self.detect_count = 0
                self.track_bin = None
                self.track_miss = 0
                self.last_print_range = -1.0
                print("Not Detected")
                output_items[0][0] = np.float32(0.0)
                return 1

            k_est = self.interp_peak(vec, k_use)
            fb, dist_m = self.bin_to_range(k_est, mid)

            if self.last_print_range < 0 or abs(dist_m - self.last_print_range) > 0.20:
                print(f"Detected | Coarse Range Estimate: {dist_m:.2f} m | Beat: {fb:.1f} Hz | Bin: {k_est:.2f}")
                self.last_print_range = dist_m

        output_items[0][0] = np.float32(self.state)
        return 1

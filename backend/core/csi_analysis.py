"""
Pure-Python CSI signal analysis (no numpy / scipy dependency).

Turns a stream of raw CSI subcarrier amplitude vectors into *real*, physically
grounded metrics:

  * motion detection  -> temporal variance of the amplitudes
  * breathing rate    -> dominant periodicity in the 0.1-0.6 Hz band
  * heart rate        -> dominant periodicity in the 0.8-2.0 Hz band

These work on whatever amplitudes are fed in (real Nexmon/iwlwifi CSI or the
synthetic fallback), so the dashboard shows derived-from-signal values instead
of hard-coded fakes. The keystroke / radar / DensePose decoders are research
grade and are NOT inferred here — callers should label them as simulated.
"""

import math
import time
from collections import deque, defaultdict


# --- analysis tuning -------------------------------------------------------
WINDOW_SECONDS = 18.0          # rolling history kept per node
MOTION_WINDOW = 1.2            # seconds used for the motion estimate
MIN_VITALS_SECONDS = 10.0      # need this much history before estimating vitals
RESAMPLE_FS = 10.0             # uniform grid (Hz) for the vitals FFT/Goertzel

BREATHING_BAND = (0.1, 0.6)    # Hz  (6 - 36 breaths / min)
HEART_BAND = (0.8, 2.0)        # Hz  (48 - 120 beats / min)

# motion score (mean per-subcarrier std over MOTION_WINDOW) above this => motion
MOTION_THRESHOLD = 1.5
MOTION_FULLSCALE = 12.0        # score mapped to motion_level == 1.0


class _NodeBuffer:
    __slots__ = ("times", "amps", "means")

    def __init__(self):
        self.times = deque()
        self.amps = deque()
        self.means = deque()

    def append(self, t, amplitudes):
        self.times.append(t)
        self.amps.append(amplitudes)
        self.means.append(sum(amplitudes) / len(amplitudes) if amplitudes else 0.0)
        # drop anything older than the window
        cutoff = t - WINDOW_SECONDS
        while self.times and self.times[0] < cutoff:
            self.times.popleft()
            self.amps.popleft()
            self.means.popleft()


def _goertzel_power(samples, fs, freq):
    """Squared magnitude of `samples` at `freq` (Hz), sampled at `fs` Hz."""
    n = len(samples)
    if n == 0 or fs <= 0:
        return 0.0
    w = 2.0 * math.pi * freq / fs
    coeff = 2.0 * math.cos(w)
    s_prev = 0.0
    s_prev2 = 0.0
    for x in samples:
        s = x + coeff * s_prev - s_prev2
        s_prev2 = s_prev
        s_prev = s
    return s_prev2 * s_prev2 + s_prev * s_prev - coeff * s_prev * s_prev2


def _detrend_window(samples):
    """Remove linear trend + DC, then apply a Hann window (reduces leakage)."""
    n = len(samples)
    if n < 2:
        return list(samples)
    # least-squares linear fit: y = a*x + b
    xs = range(n)
    sx = sum(xs)
    sy = sum(samples)
    sxx = sum(i * i for i in xs)
    sxy = sum(i * samples[i] for i in xs)
    denom = n * sxx - sx * sx
    if denom == 0:
        a, b = 0.0, sy / n
    else:
        a = (n * sxy - sx * sy) / denom
        b = (sy - a * sx) / n
    out = []
    for i in range(n):
        detr = samples[i] - (a * i + b)
        # Hann window
        win = 0.5 - 0.5 * math.cos(2.0 * math.pi * i / (n - 1))
        out.append(detr * win)
    return out


def _resample_uniform(times, values, fs):
    """Linear-interpolate an irregular (times, values) series onto a fs-Hz grid."""
    if len(times) < 2:
        return []
    t0, t1 = times[0], times[-1]
    span = t1 - t0
    if span <= 0:
        return []
    n = int(span * fs)
    if n < 2:
        return []
    out = []
    j = 0
    for i in range(n):
        t = t0 + i / fs
        while j < len(times) - 2 and times[j + 1] < t:
            j += 1
        t_a, t_b = times[j], times[j + 1]
        if t_b == t_a:
            out.append(values[j])
            continue
        frac = (t - t_a) / (t_b - t_a)
        out.append(values[j] + frac * (values[j + 1] - values[j]))
    return out


def _dominant_freq(samples, fs, band):
    """Best frequency in `band` plus a 0..1 confidence (peak / total band power)."""
    lo, hi = band
    step = 0.02  # Hz resolution of the scan
    best_f, best_p, total_p = 0.0, 0.0, 0.0
    f = lo
    while f <= hi + 1e-9:
        p = _goertzel_power(samples, fs, f)
        total_p += p
        if p > best_p:
            best_p, best_f = p, f
        f += step
    if total_p <= 0:
        return None, 0.0
    return best_f, best_p / total_p


class CSIAnalyzer:
    """Maintains per-node history and derives metrics from incoming amplitudes."""

    def __init__(self):
        self._buffers = defaultdict(_NodeBuffer)

    def analyze(self, node_id, amplitudes, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        buf = self._buffers[node_id or "_default"]
        buf.append(timestamp, list(amplitudes))

        result = {
            "motion_detected": False,
            "motion_score": 0.0,
            "motion_level": 0.0,
            "breathing_rate": None,
            "breathing_conf": 0.0,
            "heart_rate": None,
            "heart_conf": 0.0,
            "samples": len(buf.times),
            "vitals_ready": False,
        }

        # --- motion: mean per-subcarrier std over the recent window ----------
        now = buf.times[-1]
        recent = [a for t, a in zip(buf.times, buf.amps) if t >= now - MOTION_WINDOW]
        if len(recent) >= 3:
            n_sub = min(len(r) for r in recent)
            stds = []
            for k in range(n_sub):
                col = [r[k] for r in recent]
                m = sum(col) / len(col)
                var = sum((c - m) ** 2 for c in col) / len(col)
                stds.append(math.sqrt(var))
            score = sum(stds) / len(stds) if stds else 0.0
            result["motion_score"] = round(score, 3)
            result["motion_detected"] = score > MOTION_THRESHOLD
            result["motion_level"] = round(min(1.0, score / MOTION_FULLSCALE), 3)

        # --- vitals: periodicity of the mean-amplitude series ---------------
        span = buf.times[-1] - buf.times[0]
        if span >= MIN_VITALS_SECONDS and len(buf.times) >= 32:
            series = _resample_uniform(list(buf.times), list(buf.means), RESAMPLE_FS)
            if len(series) >= 32:
                windowed = _detrend_window(series)
                br_f, br_c = _dominant_freq(windowed, RESAMPLE_FS, BREATHING_BAND)
                hr_f, hr_c = _dominant_freq(windowed, RESAMPLE_FS, HEART_BAND)
                result["vitals_ready"] = True
                if br_f:
                    result["breathing_rate"] = round(br_f * 60.0, 1)
                    result["breathing_conf"] = round(br_c, 3)
                if hr_f:
                    result["heart_rate"] = round(hr_f * 60.0, 1)
                    result["heart_conf"] = round(hr_c, 3)
        return result

    def reset(self, node_id=None):
        if node_id is None:
            self._buffers.clear()
        else:
            self._buffers.pop(node_id, None)


# Shared instance used by the UDP ingest path.
analyzer = CSIAnalyzer()

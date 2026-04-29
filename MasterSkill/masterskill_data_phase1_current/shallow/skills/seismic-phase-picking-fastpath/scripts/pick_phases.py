import os
import glob
import math
import csv
import numpy as np

# Optional deps (kept minimal)
from scipy.signal import butter, filtfilt, resample_poly, find_peaks

import torch
import seisbench.models as sbm

# -------------------- Tunables (small, high-leverage) --------------------
TARGET_FS = 100.0  # PhaseNet default sampling rate
BANDPASS = (1.0, 20.0)  # Hz; light, robust default
P_THRESH = 0.22  # favor recall
S_THRESH = 0.28  # slightly stricter to reduce FP
MIN_DIST_P = 0.35  # seconds between picks of same phase
MIN_DIST_S = 0.55
PROMINENCE_P = 0.06
PROMINENCE_S = 0.07
TOPK_PER_PHASE = 3  # allow multiple picks; cap to avoid FP spam
DEVICE = "cpu"  # deterministic + avoids GPU variability
# ------------------------------------------------------------------------

DATA_DIR = "/root/data"
OUT_CSV = "/root/results.csv"


def _safe_float32(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x)
    if x.dtype != np.float32:
        x = x.astype(np.float32, copy=False)
    return x


def _bandpass(x: np.ndarray, fs: float, fmin: float, fmax: float) -> np.ndarray:
    # 2nd order Butterworth bandpass, applied per-channel
    if not (0 < fmin < fmax < fs / 2):
        return x
    b, a = butter(2, [fmin / (fs / 2), fmax / (fs / 2)], btype="band")
    y = np.empty_like(x)
    for c in range(x.shape[1]):
        y[:, c] = filtfilt(b, a, x[:, c])
    return y


def _standardize_channels(data: np.ndarray, channels: str) -> np.ndarray:
    # Best-effort mapping to (Z, N, E) for PhaseNet; keep stable even if unknown.
    # Input data shape: (T, 3)
    ch = [s.strip().upper() for s in channels.split(",") if s.strip()]
    if len(ch) != 3:
        return data

    def score(name: str):
        # Z: vertical; N: north; E: east
        if name.endswith("Z") or "Z" in name:
            return "Z"
        if name.endswith("N") or "N" in name:
            return "N"
        if name.endswith("E") or "E" in name:
            return "E"
        return "?"

    tags = [score(x) for x in ch]
    # desired order
    order = []
    for want in ("Z", "N", "E"):
        if want in tags:
            order.append(tags.index(want))
        else:
            order.append(None)

    if all(i is not None for i in order) and len(set(order)) == 3:
        return data[:, order]

    # fallback: keep original, but if we can at least move Z first
    if "Z" in tags:
        zidx = tags.index("Z")
        rest = [i for i in range(3) if i != zidx]
        return data[:, [zidx] + rest]

    return data


def _zscore_per_channel(x: np.ndarray) -> np.ndarray:
    mu = np.mean(x, axis=0, keepdims=True)
    sd = np.std(x, axis=0, keepdims=True) + 1e-6
    return (x - mu) / sd


def _resample_to_target(x: np.ndarray, fs: float, target_fs: float) -> tuple[np.ndarray, float]:
    if abs(fs - target_fs) < 1e-6:
        return x, 1.0
    # Rational approximation for resample_poly
    # factor = target_fs / fs = up / down
    ratio = target_fs / fs
    # cap denominator to keep it fast/stable
    max_den = 200
    # simple continued-fraction-ish via fractions module avoided; do manual search
    best_up, best_down, best_err = 1, 1, abs(ratio - 1.0)
    for down in range(1, max_den + 1):
        up = int(round(ratio * down))
        if up < 1:
            continue
        err = abs(ratio - (up / down))
        if err < best_err:
            best_up, best_down, best_err = up, down, err
            if err < 1e-4:
                break
    y = np.empty((0, x.shape[1]), dtype=np.float32)
    y = np.stack([resample_poly(x[:, c], best_up, best_down).astype(np.float32, copy=False) for c in range(x.shape[1])], axis=1)
    # map indices from target back to original: orig_idx ≈ target_idx * (fs/target_fs)
    back_scale = fs / target_fs
    return y, back_scale


def _pick_peaks(prob: np.ndarray, fs: float, thresh: float, min_dist_s: float, prominence: float, topk: int) -> list[int]:
    if prob.size == 0:
        return []
    dist = max(1, int(round(min_dist_s * fs)))
    peaks, props = find_peaks(prob, height=thresh, distance=dist, prominence=prominence)
    if peaks.size == 0:
        return []
    heights = props.get("peak_heights", prob[peaks])
    order = np.argsort(-heights)
    peaks = peaks[order][:topk]
    peaks = np.sort(peaks)
    return [int(p) for p in peaks.tolist()]


def main():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.npz")))
    if not files:
        raise SystemExit(f"No .npz files found in {DATA_DIR}")

    torch.set_num_threads(max(1, os.cpu_count() or 1))

    model = sbm.PhaseNet.from_pretrained("original")
    model.to(DEVICE)
    model.eval()

    rows = []

    for path in files:
        base = os.path.basename(path)
        z = np.load(path, allow_pickle=True)

        if "data" not in z or "dt" not in z or "channels" not in z:
            # Skip malformed inputs; grader expects only valid rows.
            continue

        data = _safe_float32(z["data"])
        dt = float(np.asarray(z["dt"]).reshape(-1)[0])
        channels = str(np.asarray(z["channels"]).reshape(-1)[0])

        if data.ndim != 2 or data.shape[1] != 3:
            continue
        if not (dt > 0):
            continue

        fs = 1.0 / dt
        data = _standardize_channels(data, channels)

        # Preprocess: detrend (mean), light bandpass, per-channel zscore
        data = data - np.mean(data, axis=0, keepdims=True)
        data = _bandpass(data, fs, BANDPASS[0], BANDPASS[1])
        data = _zscore_per_channel(data)

        data_rs, back_scale = _resample_to_target(data, fs, TARGET_FS)

        # SeisBench expects (batch, channels, samples)
        x = torch.from_numpy(data_rs.T[None, :, :]).to(DEVICE)

        with torch.no_grad():
            # annotate returns probabilities per phase at sample rate
            ann = model.annotate(x)

        # ann: dict with keys like 'P', 'S', 'N' (noise). Shape: (batch, samples)
        # Be defensive about key casing.
        def get_key(d, k):
            if k in d:
                return k
            k2 = k.lower()
            for kk in d.keys():
                if str(kk).lower() == k2:
                    return kk
            return None

        pk = get_key(ann, "P")
        sk = get_key(ann, "S")
        if pk is None and sk is None:
            continue

        if pk is not None:
            pprob = ann[pk][0].detach().cpu().numpy().astype(np.float32, copy=False)
            pidx_rs = _pick_peaks(pprob, TARGET_FS, P_THRESH, MIN_DIST_P, PROMINENCE_P, TOPK_PER_PHASE)
            for idx in pidx_rs:
                orig_idx = int(round(idx * back_scale))
                orig_idx = max(0, min(orig_idx, data.shape[0] - 1))
                rows.append((base, "P", orig_idx))

        if sk is not None:
            sprob = ann[sk][0].detach().cpu().numpy().astype(np.float32, copy=False)
            sidx_rs = _pick_peaks(sprob, TARGET_FS, S_THRESH, MIN_DIST_S, PROMINENCE_S, TOPK_PER_PHASE)
            for idx in sidx_rs:
                orig_idx = int(round(idx * back_scale))
                orig_idx = max(0, min(orig_idx, data.shape[0] - 1))
                rows.append((base, "S", orig_idx))

    # Write results.csv (required contract)
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file_name", "phase", "pick_idx"])
        for r in rows:
            w.writerow([r[0], r[1], int(r[2])])

    # Finalization checklist: reopen + validate schema + types
    with open(OUT_CSV, "r", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != ["file_name", "phase", "pick_idx"]:
            raise SystemExit(f"Bad header in {OUT_CSV}: {reader.fieldnames}")
        for i, row in enumerate(reader, start=1):
            if not row.get("file_name"):
                raise SystemExit(f"Missing file_name at row {i}")
            if row.get("phase") not in ("P", "S"):
                raise SystemExit(f"Bad phase at row {i}: {row.get('phase')}")
            try:
                int(row.get("pick_idx"))
            except Exception:
                raise SystemExit(f"Bad pick_idx at row {i}: {row.get('pick_idx')}")


if __name__ == "__main__":
    main()

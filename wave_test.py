import numpy as np
import pandas as pd
import soundfile as sf

CSV = "./stock-data/FXCFD/EUR_USD.csv"
OUT_WAV = "./eurusd_sonification.wav"
START_DATE = "2025/01/01"
END_DATE   = "2025/12/31"

SR = 44100          # sample rate
BPM = 120
STEP = 0.5          # 1データあたりの拍(0.5=8分音符, 1.0=4分音符)
WAVE = "sine"       # "sine" / "square" / "saw"
ROOT_MIDI = 60      # C4
SEMI_SPREAD = 10    # 変化量→半音への倍率（小さめほど聴きやすい）
SEMI_CLIP = 24      # 半音の上下限（±2オクターブ）
MASTER_GAIN = 0.18  # 全体音量（0.1〜0.3くらいで調整）

# --- スケール(音階)に丸める（不協和音防止）
# C minor pentatonic: C Eb F G Bb
SCALE = np.array([0, 3, 5, 7, 10], dtype=int)

def quantize_to_scale(midi_note: int, root=ROOT_MIDI) -> int:
    octave = (midi_note - root) // 12
    degree = (midi_note - root) % 12
    nearest = SCALE[np.argmin(np.abs(SCALE - degree))]
    return int(root + octave * 12 + nearest)

def midi_to_freq(m: float) -> float:
    return 440.0 * (2.0 ** ((m - 69.0) / 12.0))

def osc(phase: np.ndarray, kind: str) -> np.ndarray:
    if kind == "sine":
        return np.sin(phase)
    elif kind == "square":
        return np.sign(np.sin(phase))
    elif kind == "saw":
        # saw from phase: map to [-1,1]
        return 2.0 * (phase / (2*np.pi) - np.floor(0.5 + phase / (2*np.pi)))
    else:
        raise ValueError("WAVE must be 'sine', 'square', or 'saw'")

def adsr(n: int, sr: int, a=0.01, d=0.05, s=0.65, r=0.08) -> np.ndarray:
    """必ず長さ n に収まる簡易ADSR（秒指定）"""
    if n <= 0:
        return np.zeros(0, dtype=np.float32)
    if n == 1:
        return np.ones(1, dtype=np.float32)

    A = max(0, int(a * sr))
    D = max(0, int(d * sr))
    R = max(0, int(r * sr))

    # A + D + R が n を超えたら縮める（優先：A,D,R の順で削る）
    total = A + D + R
    if total >= n:
        # 最低でも1サンプルは残す
        over = total - (n - 1)
        # まずRから削る
        cut = min(R, over); R -= cut; over -= cut
        # 次にD
        cut = min(D, over); D -= cut; over -= cut
        # 最後にA
        cut = min(A, over); A -= cut; over -= cut

    S = n - (A + D + R)
    env = np.zeros(n, dtype=np.float32)

    i = 0
    if A > 0:
        env[i:i+A] = np.linspace(0, 1, A, endpoint=False, dtype=np.float32)
        i += A
    if D > 0:
        env[i:i+D] = np.linspace(1, s, D, endpoint=False, dtype=np.float32)
        i += D
    if S > 0:
        env[i:i+S] = np.float32(s)
        i += S
    if R > 0:
        # ここは必ず env の残り長と一致する
        env[i:i+R] = np.linspace(s, 0, R, endpoint=True, dtype=np.float32)

    return env


# --- CSV 読み込み
df = pd.read_csv(CSV)

# 日付を datetime に
df["日付_dt"] = pd.to_datetime(df["日付"], format="%Y/%m/%d", errors="coerce")

start_dt = pd.to_datetime(START_DATE, format="%Y/%m/%d")
end_dt   = pd.to_datetime(END_DATE,   format="%Y/%m/%d")

# 範囲フィルタ（両端含む）
df = df[(df["日付_dt"] >= start_dt) & (df["日付_dt"] <= end_dt)].copy()

if df.empty:
    raise ValueError(f"指定期間にデータがありません: {START_DATE} - {END_DATE}")

# 元データは新しい順の可能性が高いので、古い→新しいへ揃える
df = df.sort_values("日付_dt").reset_index(drop=True)

# 数値化
cols = ["始値", "終値", "高値", "安値"]
for c in cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# 休符（全NaN）
is_rest = df[cols].isna().all(axis=1).to_numpy()

df_num = df.loc[~is_rest].copy()
if df_num.empty:
    raise ValueError("指定期間内に有効な価格データ（平日）がありません。")


close = df_num["終値"].to_numpy()
open_ = df_num["始値"].to_numpy()
high = df_num["高値"].to_numpy()
low  = df_num["安値"].to_numpy()

# log return（先頭は0扱い）
ret = np.diff(np.log(close), prepend=np.log(close[0]))

# 標準化→半音へ
r = (ret - ret.mean()) / (ret.std() + 1e-9)
semi = np.clip(r * SEMI_SPREAD, -SEMI_CLIP, SEMI_CLIP)

raw_notes = ROOT_MIDI + semi
notes = np.array([quantize_to_scale(int(round(n))) for n in raw_notes], dtype=int)

# 音量：レンジ（高値-安値）
vol = (high - low)
v_den = np.ptp(vol)  # NumPy 2.0対応
v_norm = (vol - vol.min()) / (v_den + 1e-9)
amp = 0.15 + 0.85 * v_norm  # 0.15〜1.0

# 長さ：実体（|終値-始値|）
body = np.abs(close - open_)
b_den = np.ptp(body)
b_norm = (body - body.min()) / (b_den + 1e-9)
dur_sec = 0.10 + 0.40 * b_norm  # 0.10〜0.50秒

# --- 合成
step_sec = (60.0 / BPM) * STEP
step_n = int(round(step_sec * SR))

# 全体サンプル数
total_n = len(df) * step_n
audio = np.zeros(total_n, dtype=np.float32)

num_index = 0
for i in range(len(df)):
    start = i * step_n
    end = start + step_n
    if is_rest[i]:
        continue  # 休符
    # このスロット内で鳴らす長さ
    n = min(step_n, int(round(dur_sec[num_index] * SR)))
    if n <= 8:
        num_index += 1
        continue

    f = midi_to_freq(notes[num_index])
    t = np.arange(n, dtype=np.float32) / SR
    phase = 2.0 * np.pi * f * t

    wave = osc(phase, WAVE).astype(np.float32)

    # エンベロープ（クリックノイズ抑制）
    env = adsr(n, SR, a=0.005, d=0.04, s=0.6, r=0.06).astype(np.float32)

    audio[start:start+n] += (wave * env * amp[num_index]).astype(np.float32)

    num_index += 1

# クリップ回避の正規化＋マスターゲイン
mx = float(np.max(np.abs(audio)) + 1e-9)
audio = (audio / mx) * MASTER_GAIN

sf.write(OUT_WAV, audio, SR)
print("saved:", OUT_WAV)

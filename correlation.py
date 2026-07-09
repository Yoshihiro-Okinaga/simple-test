import pandas as pd
import glob
import os
import itertools

# CSVフォルダ（サブフォルダも検索）
CSV_FOLDER = "./stock-data/FXCFD/"

# diff_days（騰落の期間）を範囲指定
# 例：1〜5日騰落を調べる
diff_day_list = range(1, 6)

# lag_days（B銘柄を何日前にずらすか）を範囲指定
# 例：1〜30日ずらす
lag_day_list = range(1, 31)

# サブフォルダも含めて再帰的に CSV を検索
csv_files = glob.glob(os.path.join(CSV_FOLDER, "**", "*.csv"), recursive=True)

data_dict = {}

for file in csv_files:
    name = os.path.splitext(os.path.basename(file))[0]
    df = pd.read_csv(file)

    # 列名の空白・不可視文字を除去
    df.columns = df.columns.str.strip()

    # 日付を datetime に変換
    df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
    df = df.set_index("日付")

    # 終値列を自動検出（"終値" を含む列）
    close_col = [c for c in df.columns if "終値" in c]
    if len(close_col) == 0:
        print(f"⚠ 終値列が見つかりません: {file}")
        continue

    close_col = close_col[0]

    # 終値を保存
    data_dict[name] = df[close_col]

# 銘柄名一覧
names = list(data_dict.keys())

# 全組み合わせ（自己相関含む）
pairs = list(itertools.product(names, names))

# 全 diff_days × lag_days の結果をまとめるリスト
all_corr_list = []

for diff_days in diff_day_list:
    # diff_days 日騰落を計算
    diff_dict = {name: series.diff(diff_days) for name, series in data_dict.items()}

    for lag_days in lag_day_list:
        for a, b in pairs:
            series_a = diff_dict[a]
            series_b = diff_dict[b]

            # B銘柄を lag_days 日ずらす
            series_b_shifted = series_b.shift(lag_days)

            # 結合して日付を揃える
            merged = pd.concat([series_a, series_b_shifted], axis=1, join="inner")
            merged.columns = ["A_diff", "B_diff_shifted"]

            if len(merged) == 0:
                continue

            corr = merged["A_diff"].corr(merged["B_diff_shifted"])

            all_corr_list.append({
                "A": a,
                "B": b,
                "diff_days": diff_days,
                "lag_days": lag_days,
                "corr": corr,
                "abs_corr": abs(corr)
            })

# DataFrame化
all_corr_df = pd.DataFrame(all_corr_list)

# 総合トップ20（diff_days × lag_days の総合ランキング）
top20 = all_corr_df.sort_values("abs_corr", ascending=False).head(20)

print("=== 総合トップ20（騰落 × ラグ相関） ===")
print(top20)

# BOMなし UTF-8 で保存
top20.to_csv("top20_diff_lagged_correlation_overall.csv", encoding="utf-8", index=False)

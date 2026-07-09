import pandas as pd
import glob
import os
import numpy as np
from concurrent.futures import ThreadPoolExecutor

# CSVフォルダ（サブフォルダも検索）
CSV_FOLDER = "./stock-data/FXCFD/"

# diff_days（騰落の期間）を範囲指定
# 例：1〜5日騰落を調べる
diff_day_list = range(1, 6)

# lag_days（B銘柄を何日前にずらすか）を範囲指定
# 例：1〜30日ずらす
lag_day_list = range(1, 31)

# 並列数
# 大きくしすぎるとメモリ使用量が増えるため、まずは4程度が無難。
MAX_WORKERS = min(4, os.cpu_count() or 1)


def load_close_series_dict(csv_folder):
    """CSVフォルダから各銘柄の終値Seriesを読み込む。"""
    # サブフォルダも含めて再帰的に CSV を検索
    csv_files = glob.glob(os.path.join(csv_folder, "**", "*.csv"), recursive=True)

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

    return data_dict


def make_diff_dict(data_dict, diff_days):
    """
    各銘柄の diff_days 日騰落を計算する。

    元コードと同じく、各Seriesごとに diff() を計算する。
    """
    diff_dict = {}

    for name, series in data_dict.items():
        diff_dict[name] = series.diff(diff_days)

    return diff_dict


def make_shifted_dict(diff_dict, lag_days):
    """
    B銘柄側の騰落を lag_days 日ずらす。

    元コードと同じく、各Seriesごとに shift() を計算する。
    """
    shifted_dict = {}

    for name, series in diff_dict.items():
        shifted_dict[name] = series.shift(lag_days)

    return shifted_dict


def calculate_lagged_correlation(diff_dict, shifted_dict, names,
                                 diff_days, lag_days):
    """
    Aの騰落と、lag_daysずらしたBの騰落の相関を一括計算する。

    元コードでは A, B のペアごとに pd.concat() と corr() を呼んでいた。
    ここでは全銘柄をDataFrameにまとめて、相関行列から A × B 部分だけを取り出す。
    """
    a_df = pd.concat(diff_dict, axis=1, sort=True)
    b_df = pd.concat(shifted_dict, axis=1, sort=True)

    a_columns = [f"A__{name}" for name in names]
    b_columns = [f"B__{name}" for name in names]

    a_df.columns = a_columns
    b_df.columns = b_columns

    combined_df = pd.concat([a_df, b_df], axis=1, sort=True)

    corr_matrix = combined_df.corr()

    corr_block = corr_matrix.loc[a_columns, b_columns]

    corr_values = corr_block.to_numpy()

    pair_count = len(names) * len(names)

    corr_df = pd.DataFrame({
        "A": np.repeat(names, len(names)),
        "B": np.tile(names, len(names)),
        "diff_days": diff_days,
        "lag_days": lag_days,
        "corr": corr_values.reshape(pair_count),
    })

    corr_df["abs_corr"] = corr_df["corr"].abs()

    return corr_df


def calculate_one_lag_days(diff_dict, names, diff_days, lag_days):
    """
    1つの lag_days に対する相関計算を行う。

    この関数を並列実行する。
    """
    shifted_dict = make_shifted_dict(diff_dict, lag_days)

    corr_df = calculate_lagged_correlation(
        diff_dict=diff_dict,
        shifted_dict=shifted_dict,
        names=names,
        diff_days=diff_days,
        lag_days=lag_days,
    )

    return corr_df


def calculate_one_diff_days(data_dict, names, diff_days):
    """
    1つの diff_days に対して、複数の lag_days を並列計算する。
    """
    # diff_days 日騰落を計算
    diff_dict = make_diff_dict(data_dict, diff_days)

    all_corr_df_list = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []

        for lag_days in lag_day_list:
            future = executor.submit(
                calculate_one_lag_days,
                diff_dict,
                names,
                diff_days,
                lag_days,
            )
            futures.append(future)

        # futures は lag_day_list の順番で入っている。
        # ここで同じ順番で result() を取り出すことで、
        # 元コードに近い順序を維持する。
        for future in futures:
            corr_df = future.result()
            all_corr_df_list.append(corr_df)

    return all_corr_df_list


def main():
    data_dict = load_close_series_dict(CSV_FOLDER)

    # 銘柄名一覧
    names = list(data_dict.keys())

    # 全 diff_days × lag_days の結果をまとめるリスト
    all_corr_df_list = []

    print(f"銘柄数: {len(names)}")
    print(f"並列数: {MAX_WORKERS}")

    for diff_days in diff_day_list:
        print(f"diff_days = {diff_days} を計算中...")

        corr_df_list = calculate_one_diff_days(
            data_dict=data_dict,
            names=names,
            diff_days=diff_days,
        )

        all_corr_df_list.extend(corr_df_list)

    # DataFrame化
    all_corr_df = pd.concat(all_corr_df_list, ignore_index=True)

    # 総合トップ20（diff_days × lag_days の総合ランキング）
    top20 = all_corr_df.sort_values("abs_corr", ascending=False).head(20)

    print("=== 総合トップ20（騰落 × ラグ相関） ===")
    print(top20)

    # BOMなし UTF-8 で保存
    top20.to_csv(
        "top20_diff_lagged_correlation_overall.csv",
        encoding="utf-8",
        index=False,
    )


if __name__ == "__main__":
    main()

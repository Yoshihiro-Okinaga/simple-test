import pandas as pd
import io
import re
import seaborn as sns
import matplotlib.pyplot as plt

def load_fxcfd_data(file_path):
    """
    1つのテキストファイルに結合された複数CSVデータを解析し、
    終値(Close)の時系列DataFrameとして統合する関数（堅牢版）
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 「==================== START OF FILE: 〇〇 ====================」を区切りとして抽出
    pattern = r"==================== START OF FILE: (.*?) ====================\n(.*?)(?=\n==================== START OF FILE:|\Z)"
    matches = re.findall(pattern, content, re.DOTALL)

    series_dict = {}
    
    for filename, csv_data in matches:
        # ファイル名からアセット名を抽出 (例: Sub/AUD_JPY.csv -> AUD_JPY)
        asset_name = filename.split('/')[-1].replace('.csv', '')
        
        # 【修正点1】データ内に "END OF FILE" 等の行が混ざっている場合への対策
        # '=' で始まる行（メタデータ）を除外してクリーンなCSV文字列にする
        clean_lines = [line for line in csv_data.split('\n') if not line.strip().startswith('=')]
        clean_csv_data = '\n'.join(clean_lines)
        
        if not clean_csv_data.strip():
            continue
            
        # クリーンにした文字列データをPandasで読み込む
        df = pd.read_csv(io.StringIO(clean_csv_data))
        
        # 日付をインデックスに設定
        if '日付' in df.columns and '終値' in df.columns:
            # 【修正点2】errors='coerce' を追加
            # 万が一日付に変換できない不正な文字列があっても、エラーで止めずに「NaT (Not a Time)」に変換する
            df['日付'] = pd.to_datetime(df['日付'], errors='coerce')
            
            # NaT（無効な日付）になってしまった行を安全に削除
            df = df.dropna(subset=['日付'])
            
            df.set_index('日付', inplace=True)
            
            # 終値のSeriesを辞書に格納
            series_dict[asset_name] = df['終値']

    # 全アセットの終値を1つのDataFrameに結合（日付で自動的に横に並ぶ）
    combined_df = pd.DataFrame(series_dict)
    
    # 時系列を過去から現在へ昇順にソート
    combined_df.sort_index(inplace=True)
    
    # 【追加】欠損値（ある銘柄が休場でデータがない日など）を前の日の価格で埋める
    combined_df.ffill(inplace=True)
    
    return combined_df

def main():
    # 1. データのパースと結合
    file_path = 'FXCFD.txt' # ファイルと同じディレクトリで実行してください
    print("データを読み込み中...")
    price_df = load_fxcfd_data(file_path)
    print(f"読み込み完了: {price_df.shape[1]}アセット, {price_df.shape[0]}営業日")

    # 【追加】念のため、すべてのデータを確実な数値（float）に強制変換
    # 万が一、カンマなどの不正な文字があってもNaN（無効値）として処理し計算エラーを防ぐ
    price_df = price_df.apply(pd.to_numeric, errors='coerce')

    # 2. 日次変化率（リターン）の計算
    returns_df = price_df.pct_change()
    # ※ここで .dropna() は行いません。一部のアセットに欠損があっても、
    # 存在するデータ同士で相関を計算させるためです。

    # 3. 相関行列の計算
    # pandasのcorrは、ペアごとに欠損値を無視（pairwise deletion）して計算してくれます
    corr_matrix = returns_df.corr()

    # 4. ヒートマップでの可視化
    plt.figure(figsize=(14, 10))
    # seabornで相関行列を描画 (赤=正の相関, 青=負の相関)
    sns.heatmap(corr_matrix, 
                annot=False,        
                cmap='coolwarm', 
                center=0, 
                square=True, 
                linewidths=.5)
    
    plt.title("Cross-Asset Daily Returns Correlation")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()


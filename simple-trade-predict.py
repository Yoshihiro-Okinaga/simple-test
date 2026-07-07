import pandas as pd
import numpy as np

# 評価・検証用モジュール
from sklearn.metrics import accuracy_score
from sklearn.inspection import permutation_importance

# 機械学習モデル群
from sklearn.ensemble import RandomForestClassifier
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
from catboost import CatBoostClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline


def engineer_features(df):
    """
    AIに「価格の絶対値（水準）」ではなく「相場の勢いや変化（相対値）」だけを
    学習させるための特徴量生成関数。
    """
    df = df.copy()
    
    # 1. リターン（変化率）
    # 価格そのものではなく、「昨日から何％動いたか」を測る最も重要な指標
    df['Return_1d'] = df['終値'].pct_change(1)
    df['Return_5d'] = df['終値'].pct_change(5)  # 1週間のトレンド
    
    # 2. 移動平均との乖離率 (Ratio)
    # 現在の価格が、過去の平均からどれくらい離れているか（買われすぎ/売られすぎ）
    sma05 = df['終値'].rolling(window=5).mean()
    sma20 = df['終値'].rolling(window=20).mean()
    df['SMA_5_Ratio'] = df['終値'] / sma05
    df['SMA_20_Ratio'] = df['終値'] / sma20
    
    # 3. ボラティリティ（値動きの激しさ）
    # 直近14日間のリターンのばらつき（標準偏差）。相場のパニック度合いを測る
    df['Volatility_14d'] = df['Return_1d'].rolling(window=14).std()
    
    # 4. 日中の変動幅 (High-Low Ratio)
    # 高値を安値で割ることで、その日の値動きの激しさを「比率」として抽出
    df['High_Low_Ratio'] = df['高値'] / df['安値']
    
    # 5. 正規化MACD (MACD_Ratio)
    # 通常のMACDは価格帯によって値が極端に変わってしまうため、終値で割って「比率」に直す
    ema_12 = df['終値'].ewm(span=12, adjust=False).mean()
    ema_26 = df['終値'].ewm(span=26, adjust=False).mean()
    macd = ema_12 - ema_26
    df['MACD_Ratio'] = macd / df['終値']
    
    # 指標計算に必要な過去データ分（初期のNaN）を安全に削除
    df = df.dropna().reset_index(drop=True)
    return df


def save_importance_csv(importance_df, output_filepath):
    """
    特徴量の重要度をCSVとして保存する。
    Excelでの日本語文字化けを防ぐため utf-8-sig を指定。
    """
    importance_df.to_csv(output_filepath, index=False, encoding='utf-8-sig')
    print(f"特徴量の重要度をCSVとして保存しました: {output_filepath}")


def run_walk_forward_validation(df, model, exclude_columns, train_years_len=10):
    """
    年単位で学習期間をスライドさせながら検証（ウォークフォワード検証）を行う。
    特定の相場環境への過学習を防ぎ、モデルの真の汎用性を測るため。
    """
    years = sorted(df['日付'].dt.year.unique())
    accuracies = []
    
    print(f"\n--- ウォークフォワード検証 (学習: {train_years_len}年 -> 検証: 1年) ---")
    
    # 学習期間＋テスト期間（1年）が確保できる範囲でループ
    for i in range(len(years) - train_years_len):
        train_years = years[i : i + train_years_len]
        test_year = years[i + train_years_len]
        
        # 年ベースでデータを抽出
        train_df = df[df['日付'].dt.year.isin(train_years)]
        test_df = df[df['日付'].dt.year.isin([test_year])]
        
        # モデルに不要な列を除外して特徴量（X）を作成
        X_train = train_df.drop(columns=exclude_columns, errors='ignore')
        y_train = train_df['Target_Class']
        
        X_test = test_df.drop(columns=exclude_columns, errors='ignore')
        y_test = test_df['Target_Class']
        
        # 祝日等でデータが欠損している年に対する安全装置
        if len(X_train) == 0 or len(X_test) == 0:
            continue
            
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        
        acc = accuracy_score(y_test, y_pred)
        accuracies.append(acc)
        
        print(f"学習: {train_years[0]}〜{train_years[-1]}年 -> 検証: {test_year}年 | 正答率: {acc:.2%}")
        
    print("-" * 50)
    print(f"全体平均 正答率: {np.mean(accuracies):.2%}\n")
    
    # Permutation Importance計算用に、最新の相場で学習したモデルとテストデータを返す
    return model, X_test, y_test


# ==========================================
# メイン処理
# ==========================================

# --- 実行設定 ---
FILE_NAME = './stock-data/FXCFD/EUR_USD.csv'
TARGET_MODEL_NAME = 'lightgbm'  # 'random_forest', 'xgboost', 'catboost', 'logistic' 等に変更可能
TRAIN_YEARS_LEN = 10  # 学習に使う過去の年数

AVAILABLE_MODELS = {
    'random_forest': RandomForestClassifier(
        random_state=42, n_estimators=100, max_depth=8, min_samples_leaf=5
    ),
    'lightgbm': LGBMClassifier(
        random_state=42, n_estimators=100, learning_rate=0.05, max_depth=5, num_leaves=31, verbose=-1
    ),
    'xgboost': XGBClassifier(
        random_state=42, n_estimators=100, learning_rate=0.05, max_depth=5, eval_metric='logloss'
    ),
    'catboost': CatBoostClassifier(
        random_state=42, iterations=100, learning_rate=0.05, depth=5, verbose=False
    ),
    'logistic': make_pipeline(
        StandardScaler(), 
        LogisticRegression(random_state=42, max_iter=1000)
    )
}

if __name__ == "__main__":
    print(f"[{TARGET_MODEL_NAME}] の検証プロセスを開始します...")
    
    if TARGET_MODEL_NAME not in AVAILABLE_MODELS:
        raise ValueError(f"エラー: モデル '{TARGET_MODEL_NAME}' は登録されていません。")

    # 1. データの読み込み
    df = pd.read_csv(FILE_NAME)
    df = df.drop(columns=['株式分割'], errors='ignore')
    df = df.dropna(subset=['終値']).copy()
    df['日付'] = pd.to_datetime(df['日付'])
    df = df.sort_values('日付').reset_index(drop=True)

    # 2. 特徴量の追加
    df = engineer_features(df)

    # 3. ターゲット変数の作成（翌日上がるか下がるか）
    df['Target_Class'] = (df['終値'].shift(-1) > df['終値']).astype(int)
    df = df.dropna(subset=['Target_Class']).reset_index(drop=True)

    # 4. 検証の実行
    # ★重要: 「始値」「終値」「高値」「安値」といった「価格の絶対値」をここで全て捨てる！
    exclude_columns = ['日付', '曜日', '始値', '終値', '高値', '安値', '出来高', 'Target_Class']
    
    features_list = df.drop(columns=exclude_columns, errors='ignore').columns.tolist()
    print("使用する特徴量:", features_list)
    
    model_instance = AVAILABLE_MODELS[TARGET_MODEL_NAME]
    
    trained_model, X_test_latest, y_test_latest = run_walk_forward_validation(
        df=df, 
        model=model_instance, 
        exclude_columns=exclude_columns, 
        train_years_len=TRAIN_YEARS_LEN
    )

    # 5. 最新相場における特徴量重要度の計算
    print("最新のテストデータに対する Permutation Importance を計算中...")
    result = permutation_importance(
        trained_model, X_test_latest, y_test_latest, n_repeats=20, random_state=42, n_jobs=-1
    )

    perm_imp_df = pd.DataFrame({
        'Feature': features_list,
        'Importance_Mean': result.importances_mean,
        'Importance_Std': result.importances_std
    })
    perm_imp_df = perm_imp_df.sort_values(by='Importance_Mean', ascending=False)

    # 6. 結果の保存
    output_csv_path = f'./permutation_importance_{TARGET_MODEL_NAME}.csv'
    save_importance_csv(perm_imp_df, output_csv_path)

    print("すべての処理が完了しました。")

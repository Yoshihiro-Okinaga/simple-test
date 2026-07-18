from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Set


# ---------------------------
# 書き出し設定
# ---------------------------
PROJECT_CONFIGS = [
    {
        "project_path": "../stock-predict",
        "output_file": "./stock-predict_context.txt",
    },
]

# 2. 下の4つで変化する「銘柄名」だけをリストにする
symbols = [
#    "US30_Futures",
    "EUR_USD",
    "USD_JPY",
#    "GOLD_USD",
#    "6752_パナソニック",
    "9501_東京電力ホールディングス",
]

develop_datas = [
    #"result",
    "classification_diagnostic",
    "feature_importance",
    "overfit_diagnostic",
]

# 3. ループで回して PROJECT_CONFIGS に追加する
for symbol in symbols:
    for develop_data in develop_datas:
        config = {
            "project_path": f"../stock_predict_Results/develop/{symbol}/{develop_data}",
            "output_file": f"./stock_Result/{symbol}_{develop_data}.txt",
            "only_target_extensions": {".csv"},
        }
        #PROJECT_CONFIGS.append(config)

PROJECT_CONFIGS_ORG = [
    {
        "project_path": "../stock_predict_Results/results",
        "output_file": "./result.txt",
        "only_target_extensions": {".csv"},
    },
    {
        "project_path": "../../HtmlProject/price-ride-viewer",
        "output_file": "./price-ride-viewer_context.txt",
        "target_extensions": {".html", ".js", ".css"},
    },
    {
        "project_path": "../stock-data",
        "output_file": "./stock-data_context.txt",
        "target_extensions": {
            ".py", ".toml", ".md", ".json", ".yaml", ".yml"
        },
    },
    {
        "project_path": "../../HTML5",
        "output_file": "./HTML5_context.txt",
        "target_extensions": {".html", ".js", ".css"},
    },
]

PROJECT_CONFIGS.extend(PROJECT_CONFIGS_ORG)

PROJECT_CONFIGS_STOCK_PROGRAM = [
    {
        "project_path": "../../VCSProject/CSUtility",
        "output_file": "./CSUtility.txt",
    },
    {
        "project_path": "../../VCSProject/StockCalcForm",
        "output_file": "./StockCalcForm.txt",
    },
]

#PROJECT_CONFIGS.extend(PROJECT_CONFIGS_STOCK_PROGRAM)

PROJECT_CONFIGS_STOCK_DATA = [
    {
        "project_path": "D:/Okinaga/PythonProject/stock-data/Manual/FXCFD",
        "output_file": "./FXCFD.txt",
        "only_target_extensions": {".csv"},
    },
    {
        "project_path": "D:/Okinaga/PythonProject/stock-data/Manual/Stock",
        "output_file": "./Stock.txt",
        "only_target_extensions": {".csv"},
    },
]

PROJECT_CONFIGS.extend(PROJECT_CONFIGS_STOCK_DATA)

@dataclass
class ProjectExportConfig:
    """プロジェクト書き出し設定"""
    project_path: str = "../stock-predict"
    output_file: str = "./stock_predict_context.txt"

    # ここが設定されていたら、その拡張子のみ対象
    only_target_extensions: Set[str] = field(default_factory=lambda: {

    })

    # 中身を出力する拡張子
    target_extensions: Set[str] = field(default_factory=lambda: {
        ".py", ".cs", ".toml", ".md", ".json", ".yaml", ".yml"
    })

    # 除外する拡張子（ツリー表示・内容出力の両方に適用）
    ignore_extensions: Set[str] = field(default_factory=lambda: {
        # ".png", ".jpg", ".jpeg", ".gif",
        # ".zip", ".7z", ".rar",
        # ".log",
    })

    # スキャン対象から除外するディレクトリ名
    ignore_dirs: Set[str] = field(default_factory=lambda: {
        ".git", "__pycache__", ".venv", "venv", ".idea", ".vscode",
    })

    # 完全一致で除外するファイル名（nameで比較する想定）
    ignore_files: Set[str] = field(default_factory=lambda: {
        ".DS_Store"
    })


class ProjectContextExporter:
    """プロジェクト構成とファイル内容を1つのテキストに書き出すクラス"""

    def __init__(self, base_dir: Path | str, config: ProjectExportConfig):
        self.base_dir = Path(base_dir).resolve()
        self.config = config
        self.project_path = (self.base_dir / config.project_path).resolve()
        self.output_path = (self.base_dir / config.output_file).resolve()

    # ---------- public API ----------
    def run(self) -> Path:
        """書き出し実行"""
        if not self._validate_paths():
            return

        # 出力ファイル自身のファイル名は常に除外（project内にある場合の事故防止）
        ignore_files = set(self.config.ignore_files)
        ignore_files.add(self.output_path.name)

        with self.output_path.open("w", encoding="utf-8") as f:
            self._write_header(f)
            self._write_project_structure(f, ignore_files)
            self._write_file_contents(f, ignore_files)

        print(f"✅ 完了しました。 '{self.output_path}' をAIに共有してください。")
        return self.output_path

    # ---------- validation ----------
    def _validate_paths(self) -> bool:
        if not self.project_path.exists():
            print(f"プロジェクトパスが存在しません: {self.project_path}")
            return False
        if not self.project_path.is_dir():
            print(f"プロジェクトパスがディレクトリではありません: {self.project_path}")
            return False

        # 出力先ディレクトリを作成（必要なら）
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        return True

    # ---------- write sections ----------
    def _write_header(self, f) -> None:
        f.write("=" * 50 + "\n")
        f.write(f"PROJECT EXPORT: {self.project_path.name}\n")
        f.write("=" * 50 + "\n\n")

    def _write_project_structure(self, f, ignore_files: set[str]) -> None:
        f.write("--- [PROJECT STRUCTURE] ---\n")
        f.write(f"{self.project_path.name}/\n")
        f.write(self._get_tree_structure(self.project_path, ignore_files=ignore_files))
        f.write("\n\n")

    def _write_file_contents(self, f, ignore_files: set[str]) -> None:
        f.write("--- [FILE CONTENTS] ---\n")

        for file_path in sorted(self.project_path.rglob("*"), key=lambda p: str(p).lower()):
            if not file_path.is_file():
                continue
            if self._is_ignored(file_path, ignore_files=ignore_files):
                continue

            if len(self.config.only_target_extensions) > 0:
                if file_path.suffix.lower() not in self.config.only_target_extensions:
                    continue
            elif file_path.suffix.lower() not in self.config.target_extensions:
                continue

            try:
                relative_path = file_path.relative_to(self.project_path)
                f.write(f"\n{'=' * 20} START OF FILE: {relative_path} {'=' * 20}\n")

                text_content = file_path.read_text(encoding="utf-8", errors="ignore")
                f.write(text_content)

                f.write(f"\n{'=' * 21} END OF FILE: {relative_path} {'=' * 21}\n")
            except Exception as e:
                f.write(f"\n[ERROR READING FILE: {file_path} - {e}]\n")

    # ---------- tree / filtering ----------
    def _get_tree_structure(self, root_path: Path, indent: str = "", ignore_files: set[str] | None = None) -> str:
        """ディレクトリ構造をツリー形式の文字列で返す"""
        ignore_files = ignore_files or set()
        tree_str = ""

        items = [item for item in root_path.iterdir()]
        items = [i for i in items if not self._is_ignored(i, ignore_files=ignore_files)]
        items = sorted(items, key=lambda p: (not p.is_dir(), p.name.lower()))  # dir優先 + 名前順

        for index, item in enumerate(items):
            is_last = index == len(items) - 1
            prefix = "└── " if is_last else "├── "

            tree_str += f"{indent}{prefix}{item.name}\n"

            if item.is_dir():
                new_indent = indent + ("    " if is_last else "│   ")
                tree_str += self._get_tree_structure(item, new_indent, ignore_files=ignore_files)

        return tree_str

    def _is_ignored(self, path: Path, ignore_files: set[str]) -> bool:
        # ディレクトリ名で除外（pathのどこかに含まれていたら除外）
        if any(part in self.config.ignore_dirs for part in path.parts):
            return True

        # ファイル名で除外（完全一致）
        if path.name in ignore_files:
            return True
        
        # 拡張子で除外（ファイルのみ）
        if path.is_file() and path.suffix.lower() in self.config.ignore_extensions:
            return True

        return False


# ---------------------------
# 実行例（従来の main 相当）
# ---------------------------
def main() -> None:
    script_dir = Path(__file__).parent

    for config_values in PROJECT_CONFIGS:
        config = ProjectExportConfig(**config_values)

        exporter = ProjectContextExporter(
            base_dir=script_dir,
            config=config,
        )
        exporter.run()


if __name__ == "__main__":
    main()

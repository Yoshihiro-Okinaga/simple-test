from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------
# 書き出し設定: StockPredictプロジェクト系
# ---------------------------
PROJECT_CONFIGS_STOCK_PREDICT = [
    {
        "project_path": "../stock-predict",
        "output_file": "./stock-predict_context.txt",
    },
    {
        "project_path": "../stock_predict_Results/results",
        "output_file": "./result.txt",
        "only_target_extensions": {".csv"},
    },
]

SYMBOLS = [
    # "US30_Futures",
    "EUR_USD",
    "USD_JPY",
    # "GOLD_USD",
    # "6752_パナソニック",
    "9501_東京電力ホールディングス",
]

DEVELOP_DATAS = [
    # "result",
    "classification_diagnostic",
    "feature_importance",
    "overfit_diagnostic",
]

for symbol in SYMBOLS:
    for develop_data in DEVELOP_DATAS:
        PROJECT_CONFIGS_STOCK_PREDICT.append({
            "project_path": (
                f"../stock_predict_Results/develop/{symbol}/{develop_data}"
            ),
            "output_file": f"./stock_Result/{symbol}_{develop_data}.txt",
            "only_target_extensions": {".csv"},
        })


# ---------------------------
# 書き出し設定: 通常プロジェクト系
# ---------------------------
PROJECT_CONFIGS_ORG = [
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


# ---------------------------
# 書き出し設定: C#系
# ---------------------------
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


# ---------------------------
# 書き出し設定: 株価データ系
# ---------------------------
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


# ---------------------------
# 書き出し設定: stock-data-updater
# ---------------------------
PROJECT_CONFIGS_STOCK_DATA_UPDATER = [
    {
        "project_path": "../stock-data-updater",
        "output_file": "./stock-data-updater_context.txt",
    },
]


# ---------------------------
# 書き出し設定: trade-test
# ---------------------------
PROJECT_CONFIGS_TRADE_TEST = [
    {
        "project_path": "../trade-test/",
        "output_file": "../trade-test/trade-test_context.txt",
        "target_extensions": {".py", ".toml"},
    },
]

PROJECT_CONFIGS_TRADE_TEST_ALL = [
    {
        "project_path": "../trade-test/",
        "output_file": "../trade-test/trade-test-all_context.txt",
        "target_extensions": {".py", ".toml", ".csv"},
    },
]


# ---------------------------
# 実行時に選べる設定グループ
# ---------------------------
PROJECT_CONFIG_GROUPS = {
    "stock-predict": PROJECT_CONFIGS_STOCK_PREDICT,
    "org": PROJECT_CONFIGS_ORG,
    "stock-program": PROJECT_CONFIGS_STOCK_PROGRAM,
    "stock-data": PROJECT_CONFIGS_STOCK_DATA,
    "stock-data-updater": PROJECT_CONFIGS_STOCK_DATA_UPDATER,
    "trade-test": PROJECT_CONFIGS_TRADE_TEST,
    "trade-test-all": PROJECT_CONFIGS_TRADE_TEST_ALL,
}


@dataclass
class ProjectExportConfig:
    """プロジェクト書き出し設定"""

    project_path: str = "../stock-predict"
    output_file: str = "./stock_predict_context.txt"

    # ここが設定されていたら、その拡張子のみ対象
    only_target_extensions: set[str] = field(default_factory=set)

    # 中身を出力する拡張子
    target_extensions: set[str] = field(default_factory=lambda: {
        ".py", ".cs", ".toml", ".md", ".json", ".yaml", ".yml"
    })

    # 除外する拡張子（ツリー表示・内容出力の両方に適用）
    ignore_extensions: set[str] = field(default_factory=lambda: {
        # ".png", ".jpg", ".jpeg", ".gif",
        # ".zip", ".7z", ".rar",
        # ".log",
    })

    # スキャン対象から除外するディレクトリ名
    ignore_dirs: set[str] = field(default_factory=lambda: {
        ".git", "__pycache__", ".venv", "venv", ".idea", ".vscode",
    })

    # 完全一致で除外するファイル名（nameで比較）
    ignore_files: set[str] = field(default_factory=lambda: {
        ".DS_Store"
    })

    def __post_init__(self) -> None:
        """拡張子の表記ゆれを吸収する"""
        self.only_target_extensions = normalize_extensions(
            self.only_target_extensions
        )
        self.target_extensions = normalize_extensions(
            self.target_extensions
        )
        self.ignore_extensions = normalize_extensions(
            self.ignore_extensions
        )


class ProjectContextExporter:
    """プロジェクト構成とファイル内容を1つのテキストに書き出すクラス"""

    def __init__(self, base_dir: Path | str, config: ProjectExportConfig):
        self.base_dir = Path(base_dir).resolve()
        self.config = config
        self.project_path = (self.base_dir / config.project_path).resolve()
        self.output_path = (self.base_dir / config.output_file).resolve()

    # ---------- public API ----------
    def run(self) -> Path | None:
        """書き出し実行"""
        if not self._validate_paths():
            return None

        # 出力ファイル自身のファイル名は常に除外
        # project内にある場合の事故防止
        ignore_files = set(self.config.ignore_files)
        ignore_files.add(self.output_path.name)

        with self.output_path.open("w", encoding="utf-8") as f:
            self._write_header(f)
            self._write_project_structure(f, ignore_files)
            self._write_file_contents(f, ignore_files)

        print(f"✅ 完了しました。'{self.output_path}' をAIに共有してください。")
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

        file_paths = sorted(
            self.project_path.rglob("*"),
            key=lambda p: str(p).lower(),
        )

        for file_path in file_paths:
            if not file_path.is_file():
                continue

            if self._is_ignored(file_path, ignore_files=ignore_files):
                continue

            if not self._is_content_output_target(file_path):
                continue

            self._write_one_file_content(f, file_path)

    def _write_one_file_content(self, f, file_path: Path) -> None:
        """1ファイル分の内容を書き出す"""
        try:
            relative_path = file_path.relative_to(self.project_path)

            f.write(
                f"\n{'=' * 20} START OF FILE: "
                f"{relative_path} {'=' * 20}\n"
            )

            text_content = read_text_file_for_context(file_path)
            f.write(text_content)

            f.write(
                f"\n{'=' * 21} END OF FILE: "
                f"{relative_path} {'=' * 21}\n"
            )

        except Exception as error:
            f.write(f"\n[ERROR READING FILE: {file_path} - {error}]\n")

    # ---------- tree / filtering ----------
    def _get_tree_structure(
        self,
        root_path: Path,
        indent: str = "",
        ignore_files: set[str] | None = None,
    ) -> str:
        """ディレクトリ構造をツリー形式の文字列で返す"""
        ignore_files = ignore_files or set()
        tree_str = ""

        items = list(root_path.iterdir())
        items = [
            item
            for item in items
            if not self._is_ignored(item, ignore_files=ignore_files)
        ]
        items = sorted(
            items,
            key=lambda p: (not p.is_dir(), p.name.lower()),
        )

        for index, item in enumerate(items):
            is_last = index == len(items) - 1
            prefix = "└── " if is_last else "├── "

            tree_str += f"{indent}{prefix}{item.name}\n"

            if item.is_dir():
                new_indent = indent + ("    " if is_last else "│   ")
                tree_str += self._get_tree_structure(
                    root_path=item,
                    indent=new_indent,
                    ignore_files=ignore_files,
                )

        return tree_str

    def _is_ignored(self, path: Path, ignore_files: set[str]) -> bool:
        """除外対象かどうかを判定する"""
        path_parts = self._get_relative_path_parts(path)

        # ディレクトリ名で除外
        if any(part in self.config.ignore_dirs for part in path_parts):
            return True

        # ファイル名で除外
        if path.name in ignore_files:
            return True

        # 拡張子で除外
        if path.is_file() and path.suffix.lower() in self.config.ignore_extensions:
            return True

        return False

    def _get_relative_path_parts(self, path: Path) -> tuple[str, ...]:
        """
        project_path からの相対パス部品を返す。

        絶対パス全体で ignore_dirs を見ると、
        プロジェクト外の親ディレクトリ名に反応する可能性があるため。
        """
        try:
            relative_path = path.relative_to(self.project_path)
            return relative_path.parts
        except ValueError:
            return path.parts

    def _is_content_output_target(self, file_path: Path) -> bool:
        """ファイル内容を書き出す対象かどうかを判定する"""
        suffix = file_path.suffix.lower()

        if len(self.config.only_target_extensions) > 0:
            return suffix in self.config.only_target_extensions

        return suffix in self.config.target_extensions


def normalize_extensions(extensions: set[str]) -> set[str]:
    """
    拡張子の表記ゆれを吸収する。

    例:
        "py"  -> ".py"
        ".PY" -> ".py"
    """
    normalized_extensions = set()

    for extension in extensions:
        extension = extension.strip().lower()

        if not extension:
            continue

        if not extension.startswith("."):
            extension = "." + extension

        normalized_extensions.add(extension)

    return normalized_extensions


def read_text_file_for_context(file_path: Path) -> str:
    """
    AI共有用にテキストファイルを読む。

    utf-8-sig にしている理由:
        UTF-8 BOM付きファイルでも、先頭に BOM 文字を残さず読めるため。

    UnicodeDecodeError 時に errors='ignore' へフォールバックする理由:
        古いCSVやC#ファイルなどで、UTF-8ではない文字が混じる可能性があるため。
    """
    try:
        return file_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        warning_message = (
            "\n[WARNING: UTF-8 decode error. "
            "Some characters may be skipped.]\n"
        )

        text_content = file_path.read_text(
            encoding="utf-8-sig",
            errors="ignore",
        )

        return warning_message + text_content


def build_arg_parser() -> argparse.ArgumentParser:
    """コマンドライン引数を定義する"""
    parser = argparse.ArgumentParser(
        description="プロジェクト構成とファイル内容をテキストに書き出します。",
    )

    parser.add_argument(
        "config_groups",
        nargs="*",
        help=(
            "実行する設定グループ名。"
            "複数指定可能。"
            "all を指定すると全グループを実行します。"
        ),
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="利用可能な設定グループ一覧を表示します。",
    )

    return parser


def print_config_group_list() -> None:
    """利用可能な設定グループ一覧を表示する"""
    print("利用可能な設定グループ:")

    for group_name, configs in PROJECT_CONFIG_GROUPS.items():
        print(f"  {group_name}: {len(configs)} 件")

    print()
    print("例:")
    print("  python export_context.py")
    print("  python export_context.py stock-data-updater")
    print("  python export_context.py org stock-data")
    print("  python export_context.py all")
    print("  python export_context.py --list")


def collect_project_configs(config_group_names: list[str]) -> list[dict]:
    """指定された設定グループ名から、実行対象の設定リストを作る"""
    if len(config_group_names) == 0:
        raise ValueError(
            "設定グループ名を1つ以上指定してください。"
        )

    if "all" in config_group_names:
        config_group_names = list(PROJECT_CONFIG_GROUPS.keys())

    project_configs = []

    for group_name in config_group_names:
        if group_name not in PROJECT_CONFIG_GROUPS:
            available_names = ", ".join(PROJECT_CONFIG_GROUPS.keys())
            raise ValueError(
                f"不明な設定グループです: {group_name}\n"
                f"利用可能な設定グループ: {available_names}"
            )

        project_configs.extend(PROJECT_CONFIG_GROUPS[group_name])

    return project_configs


def run_export(project_configs: list[dict]) -> None:
    """指定された設定一覧を実行する"""
    script_dir = Path(__file__).parent

    for config_values in project_configs:
        config = ProjectExportConfig(**config_values)

        exporter = ProjectContextExporter(
            base_dir=script_dir,
            config=config,
        )
        exporter.run()


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.list:
        print_config_group_list()
        return

    try:
        project_configs = collect_project_configs(args.config_groups)
    except ValueError as error:
        print(error)
        return

    run_export(project_configs)


if __name__ == "__main__":
    main()

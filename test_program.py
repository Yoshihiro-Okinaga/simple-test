import os
from platformdirs import user_config_dir, user_data_dir, user_cache_dir
from pathlib import Path


# =========================
# 設定ここから
# =========================

PROGRAM_NAME = "test_program"

# BOMを確認・削除したい対象フォルダ
# 例:
# TARGET_FOLDER = Path(r"C:\Users\your_name\Desktop\test")
# TARGET_FOLDER = Path("/Users/your_name/Desktop/test")
TARGET_FOLDER = Path(r"D:\Okinaga\Dropbox")

# 対象拡張子
# ".py" のようにドット付きで書く
# "py" のようにドット無しでも動くようにしてあります
TARGET_EXTENSIONS = [
    ".txt",
    ".csv",
]

# サブフォルダも調べるか
SEARCH_SUBFOLDERS = True

# チェックのみ行うか
# True  : BOM付きかどうかを確認するだけ。ファイルは変更しない
# False : BOM付きならBOM無しに変換する
CHECK_ONLY_MODE = False

# BOM付きファイルだけを表示するか
# True  : BOM付きファイルだけプリント
# False : 全てプリント
PRINT_ONLY_BOM = True

# 変換前ファイルのバックアップを作るか
# True にすると example.py.bak のようなファイルを作ります
# CHECK_ONLY_MODE = True の場合は、バックアップも作りません
CREATE_BACKUP = False

# =========================
# 設定ここまで
# =========================


UTF8_BOM = b"\xef\xbb\xbf"


def normalize_extensions(extensions):
    """
    拡張子の表記ゆれを吸収する。

    例:
        "py"  -> ".py"
        ".PY" -> ".py"
    """
    normalized_extensions = []

    for extension in extensions:
        extension = extension.strip().lower()

        if not extension.startswith("."):
            extension = "." + extension

        normalized_extensions.append(extension)

    return set(normalized_extensions)


def find_target_files(folder, extensions, search_subfolders):
    """
    対象フォルダ内から、指定拡張子のファイルを探す。
    """
    if search_subfolders:
        file_paths = folder.rglob("*")
    else:
        file_paths = folder.glob("*")

    for file_path in file_paths:
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() in extensions:
            yield file_path


def has_utf8_bom(file_path):
    """
    ファイルがUTF-8 BOM付きかどうかを確認する。

    戻り値:
        True  : UTF-8 BOM付き
        False : UTF-8 BOM無し
    """
    file_bytes = file_path.read_bytes()
    return file_bytes.startswith(UTF8_BOM)


def remove_utf8_bom(file_path, create_backup):
    """
    UTF-8 BOMを削除する。

    注意:
        この関数は、呼び出し元でBOM付きであることを確認してから呼ぶ想定。
    """
    file_bytes = file_path.read_bytes()

    if create_backup:
        backup_path = file_path.with_name(file_path.name + ".bak")
        backup_path.write_bytes(file_bytes)

    bom_removed_bytes = file_bytes[len(UTF8_BOM):]
    file_path.write_bytes(bom_removed_bytes)


def print_app_dirs():
    """
    platformdirsで取得した各種フォルダとCPU数を表示する。
    元のプログラムの処理。
    """
    config_dir = Path(user_config_dir(PROGRAM_NAME))
    data_dir = Path(user_data_dir(PROGRAM_NAME))
    cache_dir = Path(user_cache_dir(PROGRAM_NAME))

    print(f"core num = {os.cpu_count()}")
    print(f"{config_dir}, {data_dir}, {cache_dir}")


def check_or_convert_utf8_bom_files():
    """
    指定フォルダ内の指定拡張子ファイルを調べる。

    CHECK_ONLY_MODE = True:
        BOM付きかどうかを確認するだけ。

    CHECK_ONLY_MODE = False:
        UTF-8 BOM付きならBOM無しに変換する。
    """
    target_folder = TARGET_FOLDER
    target_extensions = normalize_extensions(TARGET_EXTENSIONS)

    if not target_folder.exists():
        print(f"対象フォルダが存在しません: {target_folder}")
        return

    if not target_folder.is_dir():
        print(f"対象がフォルダではありません: {target_folder}")
        return

    checked_count = 0
    bom_found_count = 0
    converted_count = 0
    failed_count = 0

    print()
    print("UTF-8 BOMチェックを開始します。")
    print(f"対象フォルダ: {target_folder}")
    print(f"対象拡張子: {sorted(target_extensions)}")
    print(f"サブフォルダも調べる: {SEARCH_SUBFOLDERS}")
    print(f"チェックのみ: {CHECK_ONLY_MODE}")
    print(f"バックアップを作る: {CREATE_BACKUP}")
    print()

    for file_path in find_target_files(
        folder=target_folder,
        extensions=target_extensions,
        search_subfolders=SEARCH_SUBFOLDERS,
    ):
        checked_count += 1

        try:
            if has_utf8_bom(file_path):
                bom_found_count += 1

                if CHECK_ONLY_MODE:
                    print(f"BOM付き: {file_path}")
                else:
                    remove_utf8_bom(
                        file_path=file_path,
                        create_backup=CREATE_BACKUP,
                    )
                    converted_count += 1
                    print(f"変換しました: {file_path}")

            elif not PRINT_ONLY_BOM:
                print(f"BOM無し: {file_path}")

        except OSError as error:
            failed_count += 1
            print(f"処理に失敗しました: {file_path}")
            print(f"  理由: {error}")

    print()
    print("完了しました。")
    print(f"確認したファイル数: {checked_count}")
    print(f"BOM付きファイル数: {bom_found_count}")

    if CHECK_ONLY_MODE:
        print("実行モード: チェックのみ")
        print("変換したファイル数: 0")
    else:
        print("実行モード: 変換あり")
        print(f"変換したファイル数: {converted_count}")

    print(f"失敗したファイル数: {failed_count}")


def main():
    print_app_dirs()
    check_or_convert_utf8_bom_files()


if __name__ == "__main__":
    main()

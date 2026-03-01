import os
from platformdirs import user_config_dir, user_data_dir, user_cache_dir
from pathlib import Path


def main():
    config_dir = Path(user_config_dir("test_program"))
    data_dir = Path(user_data_dir("test_program"))
    cache_dir = Path(user_cache_dir("test_program"))
    print(f'core num = {os.cpu_count()}')
    print(f'{config_dir}, {data_dir}, {cache_dir}')


if __name__ == '__main__':
    main()
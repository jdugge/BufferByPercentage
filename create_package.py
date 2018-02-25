# -*- coding: utf-8 -*-

import configparser
import zipfile
import os


def create_package():
    config = configparser.ConfigParser()
    config.read('metadata.txt')
    version = config['general']['version']

    zipfile_name = 'BufferByPercentage-' + version + '.zip'
    directory_name = 'BufferByPercentage'

    with zipfile.ZipFile(zipfile_name, 'w') as package_zipfile:
        for input_file_name in [
            '__init__.py',
            'LICENSE',
            'README.md',
            'README.txt',
            'metadata.txt',
            'bufferbypercentage.py',
            'icon.svg',
        ]:
            package_zipfile.write(
                input_file_name,
                arcname=os.path.join(directory_name, input_file_name)
            )

if __name__ == "__main__":
    create_package()

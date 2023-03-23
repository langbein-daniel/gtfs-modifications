#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv
import sys
import zipfile
from io import TextIOWrapper, StringIO
from pathlib import Path
from sys import argv

from typing import IO, Iterable, Callable


def main():
    if len(argv) != 3:
        print('Usage: gtfs-input.zip gtfs-output.zip', file=sys.stderr)
    gtfs_vgn = Path(argv[1])
    gtfs_vgn_modified = Path(argv[2])

    modifications = {
        'trips.txt': add_bikes_allowed
    }
    modify_zip_file(gtfs_vgn, gtfs_vgn_modified, modifications)


def modify_zip_file(source: Path, target: Path, modifications: dict[str, Callable[[IO[bytes]], bytes | str]]) -> None:
    """
    Iterates over all files in `source` zip file.

    If a file has an entry in the `modifications` dict, the corresponding function is called with the
    source file as argument. The result is then written to the `target` zip file.

    Otherwise, the file is copied to `target` zip file without modifications.

    :param source: Path to source zip file.
    :param target: Path to target zip file.
    :param modifications: Dictionary containing the name of files to be modified and functions that perform the modifications.
    :return:
    """
    # Based on https://techoverflow.net/2020/11/11/how-to-modify-file-inside-a-zip-file-using-python/

    source_zf: zipfile.ZipFile
    target_zf: zipfile.ZipFile
    with zipfile.ZipFile(source, 'r') as source_zf, zipfile.ZipFile(target, 'w') as target_zf:
        # Iterate over files in `source_zf`
        zipinfo: zipfile.ZipInfo
        for zipinfo in source_zf.infolist():
            infile: IO[bytes]
            with source_zf.open(zipinfo) as infile:
                if zipinfo.filename in modifications.keys():
                    # Modify file content.
                    content = modifications[zipinfo.filename](infile)
                    # Write to target zip file.
                    target_zf.writestr(zipinfo.filename, content)
                else:
                    # Copy to target zip file without modifications.
                    target_zf.writestr(zipinfo.filename, infile.read())


def add_bikes_allowed(trips: IO[bytes], exists_ok: bool = False) -> str:
    """
    Adds the column `bikes_allowed` to the CSV file and sets all of its values to true ('1').

    By default, this method raises an error if the column does already exist.

    :param trips: CSV input
    :param exists_ok: If the `bikes_allowed` column does already exist, don't raise an error and set all values to true ('1'). Default: False.
    :return: CSV output
    """

    # https://developers.google.com/transit/gtfs/reference/#tripstxt
    # bikes_allowed values
    #   empty/0 -> undefined
    #   1 -> allowed
    #   2 -> not allowed

    trips_str = TextIOWrapper(trips, 'utf-8')
    data = parse_csv(trips_str)
    header = data[0]

    if 'bikes_allowed' in header:
        if exists_ok:
            print('The bikes_allowed column does already exist. Replacing undefined values with true.')
            bikes_allowed_idx = header.index('bikes_allowed')
            possible_values = ['', 0, 1, 2]
            replaced_ct = 0
            for row in data[1:]:
                value = row[bikes_allowed_idx]
                if value not in possible_values:
                    raise ValueError(f'The value {value} is not one of the expected values {possible_values} for the bikes_allowed field.')
                if value == 0:
                    # Value set to undefined.
                    # We set it to allowed.
                    row[bikes_allowed_idx] = '1'
                    replaced_ct += 1
            print(f'Replaced {replaced_ct} undefined values from a total of {len(data[1:])}.')
        else:
            raise ValueError('Expected the bikes_allowed column to be missing.')
    else:
        print('Adding the bikes_allowed column and setting all values to true.')
        header.append('bikes_allowed')
        for row in data[1:]:
            row.append('1')

    f = StringIO()
    write_csv(f, data)

    return f.getvalue()


def parse_csv(file: Iterable[str]) -> list[list[str]]:
    """
    Parse the CSV file and return it as 2D string list.
    """
    reader = csv.reader(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    return [row for row in reader]


def write_csv(file: IO[str], data: list[list[str]]) -> None:
    """
    Convert `data` to CSV and write it to `file`.
    """
    writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerows(data)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import csv
import re
import zipfile
from io import TextIOWrapper, StringIO
from pathlib import Path

from typing import IO, Iterable, Callable


def main():
    parser = argparse.ArgumentParser(description='Modifies the source GTFS and saves it as target')
    parser.add_argument('source_path',
                        help='Source GTFS zip file',
                        type=Path)
    parser.add_argument('target_path',
                        help='Target GTFS zip file',
                        type=Path)
    parser.add_argument('--bikes-allowed',
                        help='Adds the column `bikes_allowed` and sets all of its values to true',
                        dest='bikes_allowed',
                        default=False,
                        type=bool,
                        choices=[True, False])
    parser.add_argument('--bikes-allowed-exists-ok',
                        help='If the `bikes_allowed` column does already exist, don\'t raise an error'
                             ' and set all undefined values to true.',
                        dest='exists_ok',
                        default=False,
                        type=bool,
                        choices=[True, False])
    parser.add_argument('--escape-double-quotes-in-routes',
                        help='Fixes an invalid routes.txt file with unescaped double quotes',
                        dest='escape_double_quotes_in_routes',
                        default=False,
                        type=bool,
                        choices=[True, False])
    args = parser.parse_args()

    modifications = {}
    if args.bikes_allowed:
        modifications['trips.txt'] = lambda file: add_bikes_allowed(file, exists_ok=args.exists_ok)
    if args.escape_double_quotes_in_routes:
        modifications['routes.txt'] = escape_double_quotes

    modify_zip_file(args.source_path, args.target_path, modifications)


def modify_zip_file(source: Path, target: Path, modifications: dict[str, Callable[[IO[bytes]], bytes | str]]) -> None:
    """
    Iterates over all files in `source` zip file.

    If a file has an entry in the `modifications` dict, the corresponding function is called with the
    source file as argument. The return value is then written to the `target` zip file.

    Otherwise, the file is copied to `target` zip file without modifications.

    :param source: Path to source zip file.
    :param target: Path to target zip file.
    :param modifications: Dictionary mapping the name of files to be modified
     to functions that perform the modifications.
    :return: None
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
    Adds the column `bikes_allowed` to the CSV file and sets all of its values to true.

    By default, this method raises an error if the column does already exist.

    :param trips: CSV input
    :param exists_ok: If the `bikes_allowed` column does already exist,
     don't raise an error and set all undefined values to true. Default: False.
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
            print('The bikes_allowed column does already exist. Replacing undefined with true.')
            bikes_allowed_idx = header.index('bikes_allowed')
            possible_values = ['', 0, 1, 2]
            replaced_ct = 0
            for row in data[1:]:
                value = row[bikes_allowed_idx]
                if value not in possible_values:
                    raise ValueError(
                        f'The value {value} is not one of the expected values'
                        f' {possible_values} for the bikes_allowed field.'
                    )
                if value == 0:
                    # Value set to undefined.
                    # We set it to allowed.
                    row[bikes_allowed_idx] = '1'
                    replaced_ct += 1
            print(f'{100 * len(data[1:]) / replaced_ct}% of the bikes_allowed entries were undefined.\n'
                  f'{replaced_ct} undefined entries have been set to true.')
        else:
            raise ValueError('Expected the bikes_allowed column to be missing.')
    else:
        print('There is no bikes_allowed column. Adding it with all values set to true.')
        header.append('bikes_allowed')
        for row in data[1:]:
            row.append('1')

    f = StringIO()
    write_csv(f, data)

    return f.getvalue()


def escape_double_quotes(file: IO[bytes]) -> str:
    """
    Fixes an invalid CSV file with unescaped double quotes.

    :param file:
    :return:
    """
    string = TextIOWrapper(file, 'utf-8').read()

    # Example:
    #   "2-11-B-j23-1","","RB 11","Fürth  -  Zirndorf  -  Cadolzburg  ( "Rangaubahn" )","2","2A9F6F","000000"
    # Will be changed into
    #   "2-11-B-j23-1","","RB 11","Fürth  -  Zirndorf  -  Cadolzburg  ( ""Rangaubahn"" )","2","2A9F6F","000000"

    # All double-quotes that are not escaped and don't stand before or after a comma.
    pattern = r'([^,^"^\n])"([^,^"^\n])'
    # Escape the double-quote by adding a second double-quote.
    escaped_string, ct = re.subn(pattern, r'\1""\2', string)

    print(f'Escaped {ct} occurrences of ".')

    return escaped_string


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

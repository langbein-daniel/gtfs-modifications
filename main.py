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
    parser = argparse.ArgumentParser(description='Takes a source GTFS zip file, modifies it and saves it as zip')
    parser.add_argument('source_path',
                        help='Source GTFS zip file',
                        type=Path,
                        metavar='SRC_GTFS_ZIP')
    parser.add_argument('target_path',
                        help='Target GTFS zip file',
                        type=Path,
                        metavar='DST_GTFS_ZIP')
    parser.add_argument('--change-stop-location-type',
                        help='In stops.txt, change the value `2` in the `location_type` column to `0`.',
                        dest='change_stop_locations',
                        default=False,
                        type=bool,
                        choices=[True, False])
    parser.add_argument('--bikes-allowed',
                        help='Adds the column `bikes_allowed` and sets all of its values to true.'
                             ' Raises an exception if the column does already exist.',
                        dest='bikes_allowed',
                        default=False,
                        type=bool,
                        choices=[True, False])
    parser.add_argument('--bikes-allowed-exists-ok',
                        help='This argument changes the behavior of `--bikes-allowed`.'
                             ' If it is set to `True`,'
                             ' then no exception is raised if the `bikes_allowed` column does already exist.'
                             ' Instead, all undefined values of it are set to true and other existing values'
                             ' are left as they are.',
                        dest='exists_ok',
                        default=False,
                        type=bool,
                        choices=[True, False])
    parser.add_argument('--escape-double-quotes',
                        help='This argument takes the name of a .txt file from the GTFS zip file.'
                             ' Unescaped double quotes in that file will be corrected.'
                             ' This argument can be given multiple times (for different files).',
                        dest='escape_double_quotes',
                        action='append',
                        type=str,
                        metavar='TXT_FILENAME',
                        default=[])
    parser.add_argument('--delete',
                        help='This argument takes the name of a file from the GTFS zip file.'
                             ' It is deleted (not included in the target GTFS zip file).'
                             ' This argument can be given multiple times (for different files).',
                        dest='delete',
                        action='append',
                        type=str,
                        metavar='FILENAME',
                        default=[])
    args = parser.parse_args()

    # Create a dict mapping filenames (from within the zip file)
    # to functions which are to be performed on the content of the files.
    modifications = {}
    # First, fix a broken CSV file!
    if len(args.escape_double_quotes) > 0:
        filenames: list[str] = args.escape_double_quotes

        # Assert that each given filename is unique
        assert len(filenames) == len(list(set(filenames)))

        for filename in filenames:
            assert filename.endswith('.txt')
            compose(modifications, filename, escape_double_quotes)
    # Then, add/modify column of CSV file.
    if args.bikes_allowed:
        compose(
            modifications,
            'trips.txt',
            lambda file_content: add_bikes_allowed(file_content, exists_ok=args.exists_ok)
        )
    # Modify another column of CSV
    if args.change_stop_locations:
        compose(modifications, 'stops.txt', change_location_type)
    # Lastly, check if a file shall be removed.
    if len(args.delete) > 0:
        filenames: list[str] = args.delete

        # Assert that each given filename is unique
        assert len(filenames) == len(list(set(filenames)))

        for filename in filenames:
            # We could use `compose(modifications, filename, lambda)` here as well,
            # but any previous computations on `filename` are useless
            # if the file is deleted anyway.
            # Thus, we override the function in the modifications dict with a really fast one:
            modifications[filename] = lambda file_content: None

    modify_zip_file(args.source_path, args.target_path, modifications)


def compose(modifications: dict[str, Callable[[str], str | None]],
            filename: str,
            fun: Callable[[str], str | None]) -> None:
    """
    The dict `modifications` contains filenames and functions to run on their content.

    This method adds a new function `fun` for a given `filename` to this dict.

    If the dict does already contain a function which shall be executed for the same file,
    the new function will be executed on the result of the first function.

    :param modifications:
    :param filename:
    :param fun:
    :return:
    """

    def helper(f1: Callable[[str], str | None], f2: Callable[[str], str | None], file_content: str) -> str | None:
        """
        First, execute f1 with file_content.
        If the result is None, directly return None.
        Else, execute f2 with the result of f1.

        :param f1:
        :param f2:
        :param file_content:
        :return:
        """
        file_content = f1(file_content)
        if file_content is None:
            return file_content
        else:
            return f2(file_content)

    if filename in modifications.keys():
        first = modifications[filename]
        second = fun
        modifications[filename] = lambda file_content: helper(first, second, file_content)
    else:
        modifications[filename] = fun


def modify_zip_file(source: Path,
                    target: Path,
                    modifications: dict[str, Callable[[str], str | None]]) -> None:
    """
    Iterates over all files in `source` zip file.

    If a file has an entry in the `modifications` dict, the corresponding function is called with the
    content of the source file as argument. The return value is then written to the `target` zip file.

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
                    print(f'Modifying {zipinfo.filename} ...')
                    # Modify file content.
                    original_content: str = TextIOWrapper(infile, 'utf-8').read()
                    content = modifications[zipinfo.filename](original_content)

                    if content is None:
                        # Delete this file (don't write it to target zip file).
                        print('Deleting this file.')
                        continue
                    elif isinstance(content, str):
                        # Write to target zip file.
                        target_zf.writestr(zipinfo.filename, content, compress_type=8)
                    else:
                        raise ValueError()
                else:
                    # Copy to target zip file without modifications.
                    print(f'Copying {zipinfo.filename} without modifications.')
                    target_zf.writestr(zipinfo.filename, infile.read(), compress_type=8)


def change_location_type(stops_txt: str) -> str:
    """
    In stops.txt, change the value `2` in the `location_type` column to `0`.

    This fixes German wide the DELFI GTFS dataset which hase some stops marked as exit/entrance (of stations)
    which are actually the locations where one enters/leaves a vehicle.
    """
    data = parse_csv(stops_txt.splitlines())
    header = data[0]

    column_name = 'location_type'
    if column_name in header:
        print(f'The {column_name} column does already exist. Replacing values `2` with `0`.')
        column_idx = header.index(column_name)
        replaced_ct = 0
        for row in data[1:]:
            value = row[column_idx]
            if value == '2':
                row[column_idx] = '0'
                replaced_ct += 1
        print(f'{100 * replaced_ct / len(data[1:])}% of the {column_name} entries were changed.\n'
              f'{replaced_ct} entries have been set to 0.')
    else:
        print(f'There is no {column_name} column.')

    f = StringIO()
    write_csv(f, data)

    return f.getvalue()


def add_bikes_allowed(trips_txt: str, exists_ok: bool = False) -> str:
    """
    Adds the column `bikes_allowed` to the CSV file and sets all of its values to true.

    By default, this method raises an error if this column does already exist.

    :param trips_txt: Content of trips.txt CSV file
    :param exists_ok: If the `bikes_allowed` column does already exist, don't raise an error.
     All undefined values of the `bikes_allowed` column are set to true.
     Other values are left as they are.
     Default: False.
    :return: CSV output
    """

    # https://developers.google.com/transit/gtfs/reference/#tripstxt
    # bikes_allowed values
    #   empty/0 -> undefined
    #   1 -> allowed
    #   2 -> not allowed

    # trips: IO[bytes]
    # trips_str = TextIOWrapper(trips, 'utf-8')
    # data = parse_csv(trips_str)

    data = parse_csv(trips_txt.splitlines())
    header = data[0]

    column_name = 'bikes_allowed'
    if column_name in header:
        if exists_ok:
            print(f'The {column_name} column does already exist. Replacing undefined with true.')
            column_idx = header.index(column_name)
            possible_values = ['', '0', '1', '2']
            replaced_ct = 0
            for row in data[1:]:
                value = row[column_idx]
                if value not in possible_values:
                    raise ValueError(
                        f'The value {value} is not one of the expected values'
                        f' {possible_values} for the {column_name} field.'
                    )
                if value == 0:
                    # Value set to undefined.
                    # We set it to allowed.
                    row[column_idx] = '1'
                    replaced_ct += 1
            print(f'{100 * replaced_ct / len(data[1:])}% of the {column_name} entries were undefined.\n'
                  f'{replaced_ct} undefined entries have been set to true.')
        else:
            raise ValueError(f'Expected the {column_name} column to be missing.')
    else:
        print(f'There is no {column_name} column. Adding it with all values set to true.')
        header.append(column_name)
        for row in data[1:]:
            row.append('1')

    f = StringIO()
    write_csv(f, data)

    return f.getvalue()


def escape_double_quotes(file_content: str) -> str:
    """
    Fixes an invalid CSV file with unescaped double quotes.

    :param file_content:
    :return:
    """

    # Example:
    #   "2-11-B-j23-1","","RB 11","Fürth  -  Zirndorf  -  Cadolzburg  ( "Rangaubahn" )","2","2A9F6F","000000"
    # Will be changed into
    #   "2-11-B-j23-1","","RB 11","Fürth  -  Zirndorf  -  Cadolzburg  ( ""Rangaubahn"" )","2","2A9F6F","000000"

    # All double-quotes that are not escaped and don't stand before or after a comma.
    pattern = r'([^,^"^\n])"([^,^"^\n])'
    # Escape the double-quote by adding a second double-quote.
    escaped_string, ct = re.subn(pattern, r'\1""\2', file_content)

    print(f'Escaped {ct} occurrences of ".')

    return escaped_string


def parse_csv(lines: Iterable[str]) -> list[list[str]]:
    """
    Parse the CSV file and return it as 2D string list.
    """
    reader = csv.reader(lines, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    return [row for row in reader]


def write_csv(file: IO[str], data: list[list[str]]) -> None:
    """
    Convert `data` to CSV and write it to `file`.
    """
    writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerows(data)


if __name__ == '__main__':
    main()

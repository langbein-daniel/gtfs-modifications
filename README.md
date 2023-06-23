# GTFS modifications

Modify a GTFS zip file.

See [BikeTripPlanner README](https://github.com/langbein-daniel/BikeTripPlanner#gtfs-data) for mor details.

## Usage

```
usage: main.py [-h] [--bikes-allowed {True,False}]
               [--bikes-allowed-exists-ok {True,False}]
               [--escape-double-quotes TXT_FILENAME] [--delete FILENAME]
               SRC_GTFS_ZIP DST_GTFS_ZIP

Takes a GTFS zip file, modifies it and saves it as zip file

positional arguments:
  SRC_GTFS_ZIP          Source GTFS zip file
  DST_GTFS_ZIP          Target GTFS zip file

options:
  -h, --help            show this help message and exit
  --bikes-allowed {True,False}
                        Adds the column `bikes_allowed` and sets all of its
                        values to true. Raises an exception if the column does
                        already exist.
  --bikes-allowed-exists-ok {True,False}
                        This argument changes the behavior of `--bikes-
                        allowed`. If it is set to `True`, then no exception is
                        raised if the `bikes_allowed` column does already
                        exist. Instead, all undefined values of it are set to
                        true and other existing values are left as they are.
  --escape-double-quotes TXT_FILENAME
                        This argument takes the name of a .txt file from the
                        GTFS zip file. Unescaped double quotes in that file
                        will be corrected. This argument can be given multiple
                        times (for different files).
  --delete FILENAME     This argument takes the name of a file from the GTFS
                        zip file. It is deleted (not included in the target
                        GTFS zip file). This argument can be given multiple
                        times (for different files).
```

# GTFS modifications

Modify a GTFS zip file.

See [BikeTripPlanner README](https://github.com/langbein-daniel/BikeTripPlanner#gtfs-data) for mor details.

## Usage

```
usage: main.py [-h] [--bikes-allowed {True,False}]
               [--bikes-allowed-exists-ok {True,False}]
               [--escape-double-quotes-in-routes {True,False}]
               source_path target_path

Modifies the source GTFS and saves it as target

positional arguments:
  source_path           Source GTFS zip file
  target_path           Target GTFS zip file

options:
  -h, --help            show this help message and exit
  --bikes-allowed {True,False}
                        Adds the column `bikes_allowed` and sets all of its
                        values to true
  --bikes-allowed-exists-ok {True,False}
                        If the `bikes_allowed` column does already exist,
                        don't raise an error and set all undefined values to
                        true.
  --escape-double-quotes-in-routes {True,False}
                        Fixes an invalid routes.txt file with unescaped double
                        quotes
```

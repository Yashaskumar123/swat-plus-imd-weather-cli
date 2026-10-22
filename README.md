# SWAT+ IMD Weather File Creator

This CLI first extracts station CSV files from existing yearwise IMD GRD data,
then converts those CSVs into SWAT+ station files.

- `tmp`: reads `tmax` and `tmin` folders and creates `<station>.tmp` files.
- `pcp`: reads the `rain` folder (or `pcp` when `rain` is absent) and creates
  `<station>.pcp` files.

## Expected input layout

```text
source-directory/
|-- tmax/
|   `-- p_15.50_77.50.csv
|-- tmin/
|   `-- p_15.50_77.50.csv
`-- rain/
    `-- p_15.50_77.50.csv
```

For a `tmp` run, only `tmax` and `tmin` are required. For a `pcp` run, only
`rain` (or `pcp`) is required.

The station Excel file may contain either `Station`, `Long`, and `Lat` columns
or `NAME`, `LONG`, and `LAT` columns.

## Install and run

Open PowerShell in this folder:

```powershell
python -m pip install -r requirements.txt
python swat_weather_cli.py
```

The source directory must already contain the yearwise GRD files for the
selected years. For example, a TMP run for 2010-2024 needs files such as
`tmax/2010.GRD` through `tmax/2024.GRD` and the corresponding files under
`tmin`. A PCP run needs the yearwise files under `rain`.

The CLI asks for the source directory, station Excel file, output variable,
start year, end year, and destination directory. It writes `NA` for missing
dates and for IMD missing-data values (`99.9` for temperature and `-999` for
rainfall).

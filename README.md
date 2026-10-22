# SWAT+ IMD Weather CLI

A command-line tool that extracts station-level time series from existing IMD
yearwise gridded data and creates SWAT+ weather input files.

- `tmp` creates one `<station>.tmp` file from IMD `tmax` and `tmin` data.
- `pcp` creates one `<station>.pcp` file from IMD rainfall data.

The tool reads station names and coordinates from an Excel file. It does not
download IMD data; the yearwise GRD files must already be available locally.

## 1. Install from GitHub

Install [Git](https://git-scm.com/downloads) and Python 3 if they are not
already installed. Then open PowerShell and clone this repository:

```powershell
git clone https://github.com/Yashaskumar123/swat-plus-imd-weather-cli.git
cd swat-plus-imd-weather-cli
```

Creating a virtual environment is recommended:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the required Python packages:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 2. Prepare the yearwise IMD data

Place the existing yearwise GRD files inside variable-specific folders under
one source directory.

For temperature (`tmp`):

```text
source-directory/
|-- tmax/
|   |-- 2010.GRD
|   |-- 2011.GRD
|   `-- ...
`-- tmin/
    |-- 2010.GRD
    |-- 2011.GRD
    `-- ...
```

For precipitation (`pcp`):

```text
source-directory/
`-- rain/
    |-- 2010.grd
    |-- 2011.grd
    `-- ...
```

Every year in the selected start-to-end range must be present. For example, a
2010-2024 TMP run needs all yearwise files from 2010 through 2024 in both
`tmax` and `tmin`.

## 3. Prepare the station Excel file

Create an `.xlsx` or `.xls` file with one station per row. Either of these
column-name styles is accepted:

| Station | Long | Lat |
| --- | ---: | ---: |
| Station_1 | 77.50 | 15.50 |
| Station_2 | 78.50 | 16.50 |

or:

| NAME | LONG | LAT |
| --- | ---: | ---: |
| Station_1 | 77.50 | 15.50 |
| Station_2 | 78.50 | 16.50 |

- `Station` or `NAME` becomes the SWAT+ output filename.
- `Long` or `LONG` is longitude in decimal degrees.
- `Lat` or `LAT` is latitude in decimal degrees.

The coordinates must fall within the grid covered by the selected IMD
dataset.

## 4. Run the CLI

From the cloned repository directory, run:

```powershell
python swat_weather_cli.py
```

The program asks for the following values:

1. **Source directory** containing the `tmax`/`tmin` or `rain` GRD folders.
2. **Station Excel file** containing station names and coordinates.
3. **SWAT+ variable**: enter `tmp` or `pcp`.
4. **Start year** for the output period.
5. **End year** for the output period.
6. **Output directory** where the generated SWAT+ files should be saved.

Example TMP run:

```text
Source directory containing yearwise tmax/tmin/rain GRD folders: D:\IMD\data
Station Excel file (.xlsx or .xls): D:\IMD\stations.xlsx
SWAT+ variable to create (tmp/pcp): tmp
Start year: 2010
End year: 2024
Directory for the generated SWAT+ files: D:\SWAT_Project\Scenarios\Default\TxtInOut\weather
```

Paths containing spaces may be pasted with or without quotation marks.

## 5. How the program works

The program performs these operations in order:

1. Validates the source directory, Excel file, selected variable, years, and
   output directory.
2. Reads the station names, longitudes, and latitudes from Excel.
3. Opens the existing yearwise GRD files using `imdlib.open_data()`.
   - A `tmp` run opens both `tmax` and `tmin`.
   - A `pcp` run opens `rain`.
4. Extracts the daily time series at every station coordinate. Intermediate
   files such as `p_15.50_77.50.csv` are saved in the corresponding `tmax`,
   `tmin`, or `rain` folder.
5. Creates a complete daily date range from January 1 of the start year through
   December 31 of the end year, including leap days.
6. Matches the extracted data to that date range. Missing dates and IMD missing
   values (`99.9` for temperature and `-999` for rainfall) become `NA`.
7. Writes one SWAT+ weather file for every station.

## 6. Generated files

For `tmp`, each output line contains maximum and minimum temperature:

```text
20100101
31.25,18.60
30.80,17.95
NA,NA
```

The first line is the starting date in `YYYYMMDD` format. The remaining lines
contain `Tmax,Tmin`. The file is saved as `<station>.tmp`.

For `pcp`, each output line contains one precipitation value:

```text
20100101
0.00
12.45
NA
```

The file is saved as `<station>.pcp`.

## 7. Rerunning the program

The intermediate station CSV files are recreated from the GRD files each time.
Existing SWAT+ files with the same station name and extension are replaced.
Choose a different output directory if previous results must be retained.

## Common errors

- **Required folder not found**: Confirm that the source directory contains
  `tmax` and `tmin` for TMP, or `rain` for PCP.
- **Could not open GRD data**: Confirm that every selected year exists and that
  the files use the yearwise names expected by `imdlib`.
- **Missing Excel columns**: Use `Station`, `Long`, `Lat` or `NAME`, `LONG`,
  `LAT`.
- **Coordinate extraction failed**: Check that latitude and longitude are
  numeric and inside the IMD grid.
- **Missing dependency**: Activate the virtual environment and run
  `python -m pip install -r requirements.txt` again.

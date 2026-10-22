# SWAT+ IMD Weather CLI

A command-line tool that extracts station-level time series from IMD yearwise
gridded data and creates SWAT+ weather input files.

- `tmp` creates one `<station>.tmp` file from IMD `tmax` and `tmin` data.
- `pcp` creates one `<station>.pcp` file from IMD rainfall data.

The tool reads station names and coordinates from an Excel file. It can use
GRD files already stored locally or download missing GRD files from IMD.

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

## 2. Choose how to obtain the IMD GRD data

When the program asks whether the required GRD files already exist locally:

- Enter `yes` to use existing files. Select a source directory containing the
  variable-specific folders shown below.
- Enter `no` to download the files. Select an existing or new directory where
  the program should save them. The program creates the required `tmax`,
  `tmin`, or `rain` subfolders automatically.

If using existing files, place the yearwise GRD files inside
variable-specific folders under one source directory.

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

From the cloned repository directory, activate the virtual environment and run
the Python file:

```powershell
.\.venv\Scripts\Activate.ps1
python .\swat_weather_cli.py
```

If you do not want to activate the virtual environment first, call its Python
executable directly:

```powershell
.\.venv\Scripts\python.exe .\swat_weather_cli.py
```

Module syntax also works when you are inside the repository directory:

```powershell
python -m swat_weather_cli
```

Do not combine `-m` with a file path:

```powershell
# Incorrect: -m expects a module name, not a relative file path
python -m .\swat_weather_cli.py
```

The incorrect form produces `Relative module names not supported`. Use either
the file command `python .\swat_weather_cli.py` or the module command
`python -m swat_weather_cli`.

The program asks for the following values:

1. **Do the GRD files exist?** Enter `yes` or `no`.
2. **GRD directory**:
   - After `yes`, select the source directory containing the existing files.
   - After `no`, select the directory where files should be downloaded.
3. **Station Excel file** containing station names and coordinates.
4. **SWAT+ variable**: enter `tmp` or `pcp`.
5. **Start year** for the output period.
6. **End year** for the output period.
7. **Output directory** where the generated SWAT+ files should be saved.

Example TMP run:

```text
Do the required GRD files already exist locally? (yes/no): no
Directory where downloaded GRD files should be saved: D:\IMD\data
Station Excel file (.xlsx or .xls): D:\IMD\stations.xlsx
SWAT+ variable to create (tmp/pcp): tmp
Start year: 2010
End year: 2024
Directory for the generated SWAT+ files: D:\SWAT_Project\Scenarios\Default\TxtInOut\weather
```

Paths containing spaces may be pasted with or without quotation marks.

## 5. How the program works

The program performs these operations in order:

1. Reads whether existing GRD files should be used or missing files should be
   downloaded, then validates the selected directories and other inputs.
2. Reads the station names, longitudes, and latitudes from Excel.
3. Obtains the yearwise GRD data:
   - With `yes`, it opens local files using `imdlib.open_data()` and never
     downloads data.
   - With `no`, it uses `imdlib.get_data()`. Valid files already present in the
     selected directory are reused, and only missing years are downloaded.
   - A `tmp` run processes both `tmax` and `tmin`; a `pcp` run processes
     `rain`.
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
In download mode, valid GRD files already in the selected directory are reused
instead of downloaded again. Existing SWAT+ files with the same station name
and extension are replaced. Choose a different output directory if previous
results must be retained.

## Common errors

- **Required folder not found**: Confirm that the source directory contains
  `tmax` and `tmin` for TMP, or `rain` for PCP.
- **Could not open GRD data**: Confirm that every selected year exists and that
  the files use the yearwise names expected by `imdlib`.
- **GRD download failed**: Check the internet connection and confirm that IMD
  has published the selected years.
- **Missing Excel columns**: Use `Station`, `Long`, `Lat` or `NAME`, `LONG`,
  `LAT`.
- **Coordinate extraction failed**: Check that latitude and longitude are
  numeric and inside the IMD grid.
- **Missing dependency**: Activate the virtual environment and run
  `python -m pip install -r requirements.txt` again.

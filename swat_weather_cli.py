"""Create SWAT+ TMP or PCP station files from IMD station CSV files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import imdlib as imd
    import pandas as pd
except ModuleNotFoundError as exc:
    requirements = Path(__file__).with_name("requirements.txt")
    print(
        f"Missing dependency: {exc.name}.\n"
        "Install the requirements with:\n"
        f'    python -m pip install -r "{requirements}"',
        file=sys.stderr,
    )
    raise SystemExit(1) from exc


REQUIRED_COLUMNS = ("NAME", "LONG", "LAT")
STATION_COLUMN_ALIASES = {"STATION": "NAME"}
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def clean_path(value: str) -> Path:
    """Handle paths pasted with surrounding single or double quotes."""
    return Path(value.strip().strip('"').strip("'")).expanduser().resolve()


def prompt_existing_directory() -> Path:
    while True:
        raw = input(
            "Source directory containing yearwise tmax/tmin/rain GRD folders: "
        ).strip()
        if not raw:
            print("Please enter a directory path.")
            continue
        path = clean_path(raw)
        if path.is_dir():
            return path
        print(f"Directory not found: {path}")


def prompt_excel_file() -> Path:
    while True:
        raw = input("Station Excel file (.xlsx or .xls): ").strip()
        if not raw:
            print("Please enter the station Excel file path.")
            continue
        path = clean_path(raw)
        if not path.is_file():
            print(f"File not found: {path}")
            continue
        if path.suffix.lower() not in {".xlsx", ".xls"}:
            print("The station file must be an .xlsx or .xls file.")
            continue
        return path


def prompt_variable() -> str:
    aliases = {
        "tmp": "tmp",
        "temp": "tmp",
        "temperature": "tmp",
        "pcp": "pcp",
        "rain": "pcp",
        "rainfall": "pcp",
    }
    while True:
        value = input("SWAT+ variable to create (tmp/pcp): ").strip().lower()
        if value in aliases:
            return aliases[value]
        print("Enter 'tmp' for temperature or 'pcp' for precipitation.")


def prompt_year(label: str, minimum: int = 1900) -> int:
    while True:
        value = input(f"{label}: ").strip()
        try:
            year = int(value)
        except ValueError:
            print("Enter a four-digit year, for example 2024.")
            continue
        if year < minimum or year > 9999:
            print(f"Enter a year from {minimum} to 9999.")
            continue
        return year


def prompt_output_directory() -> Path:
    while True:
        raw = input("Directory for the generated SWAT+ files: ").strip()
        if not raw:
            print("Please enter an output directory path.")
            continue
        path = clean_path(raw)
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            print(f"Cannot create or use that directory: {exc}")
            continue
        if path.is_dir():
            return path
        print(f"The path is not a directory: {path}")


def load_stations(excel_file: Path) -> pd.DataFrame:
    try:
        stations = pd.read_excel(excel_file)
    except Exception as exc:
        raise ValueError(f"Could not read the station Excel file: {exc}") from exc

    stations.columns = [str(column).strip().upper() for column in stations.columns]
    stations.rename(columns=STATION_COLUMN_ALIASES, inplace=True)
    missing = [column for column in REQUIRED_COLUMNS if column not in stations.columns]
    if missing:
        raise ValueError("Missing Excel column(s): " + ", ".join(missing))

    stations = stations.loc[:, list(REQUIRED_COLUMNS)].copy()
    stations["LONG"] = pd.to_numeric(stations["LONG"], errors="coerce")
    stations["LAT"] = pd.to_numeric(stations["LAT"], errors="coerce")
    invalid = stations[
        stations["NAME"].isna()
        | stations["LONG"].isna()
        | stations["LAT"].isna()
    ]
    if not invalid.empty:
        rows = ", ".join(str(int(index) + 2) for index in invalid.index)
        raise ValueError(f"Blank or invalid values in Excel row(s): {rows}")

    return stations


def extract_imd_station_csvs(
    source_dir: Path,
    stations: pd.DataFrame,
    variable: str,
    start_year: int,
    end_year: int,
) -> None:
    """Open existing yearwise IMD GRD files and extract each station to CSV."""
    imd_variables = ("tmax", "tmin") if variable == "tmp" else ("rain",)

    print("\nExtracting station CSV files from IMD gridded data...")
    for imd_variable in imd_variables:
        variable_folder = source_dir / imd_variable
        if not variable_folder.is_dir():
            raise ValueError(f"Required folder not found: {variable_folder}")

        try:
            data = imd.open_data(
                imd_variable,
                start_year,
                end_year,
                "yearwise",
                str(source_dir),
            )
        except Exception as exc:
            raise ValueError(
                f"Could not open {imd_variable} GRD data for "
                f"{start_year}-{end_year}: {exc}"
            ) from exc

        print(f"\nLoaded {imd_variable} dataset:")
        print(data.get_xarray())

        for _, row in stations.iterrows():
            station = str(row["NAME"]).strip()
            latitude = float(row["LAT"])
            longitude = float(row["LONG"])
            expected_csv = variable_folder / f"p_{latitude:.2f}_{longitude:.2f}.csv"
            try:
                data.to_csv("p.csv", latitude, longitude, str(variable_folder))
            except Exception as exc:
                raise ValueError(
                    f"Could not extract {imd_variable} for {station} at "
                    f"{latitude}, {longitude}: {exc}"
                ) from exc
            print(f"Extracted: {expected_csv.name} ({station}, {imd_variable})")


def find_data_column(frame: pd.DataFrame, latitude: float, longitude: float) -> str:
    """Find the value column even if Excel changed coordinate formatting."""
    value_columns = [column for column in frame.columns if column != "DateTime"]
    expected = f"{latitude} {longitude}"
    if expected in value_columns:
        return expected

    for column in value_columns:
        parts = str(column).split()
        if len(parts) != 2:
            continue
        try:
            column_latitude, column_longitude = map(float, parts)
        except ValueError:
            continue
        if (
            abs(column_latitude - latitude) < 1e-8
            and abs(column_longitude - longitude) < 1e-8
        ):
            return column

    if len(value_columns) == 1:
        return value_columns[0]

    raise ValueError(
        f"No data column matching coordinates {latitude} {longitude}"
    )


def read_station_series(
    csv_path: Path,
    latitude: float,
    longitude: float,
    missing_value: float,
) -> pd.Series:
    try:
        frame = pd.read_csv(csv_path)
    except Exception as exc:
        raise ValueError(f"Could not read {csv_path.name}: {exc}") from exc

    if "DateTime" not in frame.columns:
        raise ValueError(f"DateTime column is missing in {csv_path.name}")

    frame["DateTime"] = pd.to_datetime(
        frame["DateTime"], format="%Y-%m-%d", errors="raise"
    )
    if frame["DateTime"].duplicated().any():
        raise ValueError(f"Duplicate dates found in {csv_path.name}")

    data_column = find_data_column(frame, latitude, longitude)
    values = pd.to_numeric(frame[data_column], errors="coerce")
    values = values.mask(values == missing_value)
    return pd.Series(values.to_numpy(), index=frame["DateTime"], dtype="float64")


def format_value(value: float) -> str:
    return "NA" if pd.isna(value) else f"{value:.2f}"


def safe_station_name(value: object) -> str:
    name = INVALID_FILENAME_CHARS.sub("_", str(value).strip()).rstrip(". ")
    if not name:
        raise ValueError("A station has an empty or invalid NAME value")
    return name


def locate_rain_folder(source_dir: Path) -> Path:
    rain_folder = source_dir / "rain"
    if rain_folder.is_dir():
        return rain_folder
    pcp_folder = source_dir / "pcp"
    if pcp_folder.is_dir():
        return pcp_folder
    return rain_folder


def process_stations(
    source_dir: Path,
    stations: pd.DataFrame,
    variable: str,
    start_year: int,
    end_year: int,
    output_dir: Path,
) -> tuple[int, int]:
    start_date = pd.Timestamp(year=start_year, month=1, day=1)
    end_date = pd.Timestamp(year=end_year, month=12, day=31)
    expected_dates = pd.date_range(start=start_date, end=end_date, freq="D")
    first_line = start_date.strftime("%Y%m%d")

    processed = 0
    skipped = 0
    used_output_names: set[str] = set()

    for _, row in stations.iterrows():
        station = safe_station_name(row["NAME"])
        latitude = float(row["LAT"])
        longitude = float(row["LONG"])
        prefix = f"p_{latitude:.2f}_{longitude:.2f}"
        output_name = f"{station}.{variable}"

        if output_name.casefold() in used_output_names:
            print(f"Skipped duplicate station name: {station}")
            skipped += 1
            continue
        used_output_names.add(output_name.casefold())

        try:
            if variable == "tmp":
                tmax_path = source_dir / "tmax" / f"{prefix}.csv"
                tmin_path = source_dir / "tmin" / f"{prefix}.csv"
                missing = [path for path in (tmax_path, tmin_path) if not path.is_file()]
                if missing:
                    print(
                        f"Missing file(s) for {station}: "
                        + ", ".join(str(path) for path in missing)
                    )
                    skipped += 1
                    continue

                tmax = read_station_series(tmax_path, latitude, longitude, 99.9)
                tmin = read_station_series(tmin_path, latitude, longitude, 99.9)
                tmax = tmax.reindex(expected_dates)
                tmin = tmin.reindex(expected_dates)
                output_lines = [first_line]
                output_lines.extend(
                    f"{format_value(maximum)},{format_value(minimum)}"
                    for maximum, minimum in zip(tmax, tmin)
                )
            else:
                rain_path = locate_rain_folder(source_dir) / f"{prefix}.csv"
                if not rain_path.is_file():
                    print(f"Missing file for {station}: {rain_path}")
                    skipped += 1
                    continue

                rainfall = read_station_series(
                    rain_path, latitude, longitude, -999.0
                ).reindex(expected_dates)
                output_lines = [first_line]
                output_lines.extend(format_value(value) for value in rainfall)

            output_path = output_dir / output_name
            output_path.write_text("\n".join(output_lines), encoding="utf-8")
            print(f"Written: {output_path.name}")
            processed += 1
        except Exception as exc:
            print(f"Skipped {station}: {exc}")
            skipped += 1

    return processed, skipped


def main() -> int:
    print("SWAT+ IMD Weather File Creator")
    print("Required Excel columns: NAME, LONG, LAT\n")

    try:
        source_dir = prompt_existing_directory()
        excel_file = prompt_excel_file()
        variable = prompt_variable()
        start_year = prompt_year("Start year")
        end_year = prompt_year("End year", minimum=start_year)
        output_dir = prompt_output_directory()
        stations = load_stations(excel_file)

        print("\nSettings")
        print(f"  Source directory: {source_dir}")
        print(f"  Station Excel:    {excel_file}")
        print(f"  Variable:         {variable}")
        print(f"  Period:           {start_year}-{end_year}")
        print(f"  Output directory: {output_dir}\n")

        extract_imd_station_csvs(
            source_dir,
            stations,
            variable,
            start_year,
            end_year,
        )

        processed, skipped = process_stations(
            source_dir,
            stations,
            variable,
            start_year,
            end_year,
            output_dir,
        )
        print(
            f"\nFinished. Created {processed} {variable} file(s); "
            f"skipped {skipped} station(s)."
        )
        return 0 if processed else 1
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        return 130
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

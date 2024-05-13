import csv
import re
import io as io
import polars as pl
from django.core.exceptions import ValidationError
from datetime import date, datetime, timedelta
import fitz


def strToDate_anyformat(format_date, expected_format=""):
    if format_date == None:
        return None
    numbers = "".join(re.findall(r"\d+", format_date))
    if (
        "/" in format_date
        or expected_format.upper() == "%D/%M/%Y"
        or expected_format.upper() == "%M/%D/%Y"
    ):
        # in this case, we consider the date as short_date, defaulting to %d/%m/%Y
        if expected_format == "" or expected_format.upper() == "%D/%M/%Y":
            if len(numbers) == 8 and int(numbers[2:4]) <= 12:
                d = datetime(int(numbers[4:8]), int(numbers[2:4]), int(numbers[:2]))
            elif len(numbers) == 6:
                d = datetime(
                    int(numbers[4:6]) + 2000, int(numbers[2:4]), int(numbers[:2])
                )
            else:
                return None
        else:
            # it's in american standard:
            if len(numbers) == 8 and int(numbers[:2]) <= 12:
                d = datetime(int(numbers[4:8]), int(numbers[:2]), int(numbers[2:4]))
            elif len(numbers) == 6:
                d = datetime(
                    int(numbers[4:6]) + 2000, int(numbers[:2]), int(numbers[2:4])
                )
            else:
                return None
    else:
        # else, it's a full date:
        if len(numbers) == 8:
            d = datetime(int(numbers[:4]), int(numbers[4:6]), int(numbers[6:8]))
        elif len(numbers) == 14:
            d = datetime(
                int(numbers[:4]),
                int(numbers[4:6]),
                int(numbers[6:8]),
                int(numbers[8:10]),
                int(numbers[10:12]),
                int(numbers[12:14]),
            )
        elif len(numbers) > 14:
            d = datetime(
                int(numbers[:4]),
                int(numbers[4:6]),
                int(numbers[6:8]),
                int(numbers[8:10]),
                int(numbers[10:12]),
                int(numbers[12:14]),
                microsecond=1000 * int(numbers[14:]),
            )
        else:
            d = None
    return d


def lastDayOfMonth(date):
    if date.month == 12:
        return date.replace(day=31)
    return date.replace(month=date.month + 1, day=1) - timedelta(days=1)


def parseCSV(import_file):
    rows = import_file.read().decode("utf-8-sig").splitlines()
    dialect = csv.Sniffer().sniff(rows[0])

    csv_reader = csv.DictReader(rows, dialect=dialect)

    listOfTransactions = []
    for row in csv_reader:
        row = dict((k.lower(), v) for k,v in row.items())
        if not "value" in row or not "date" in row or not "description" in row:
            raise ValidationError(
                "CSV file doesn't have all the columns needed: date, description and value"
            )
            break
        # we do a nasty conversion of decimals, if needed
        row["value"] = row["value"].replace(" ", "").replace(",", ".")
        row["value"] = row["value"].replace(".", "", row["value"].count(".") - 1)
        # we try to convert the dates:
        row["date"] = strToDate_anyformat(row["date"])

        listOfTransactions.append(
            {
                "select_row": False,
                "value": row["value"] if "value" in row else None,
                "date": row["date"] if "date" in row else None,
                "competency_date": (
                    row["competency_date"] if "competency_date" in row else None
                ),
                "description": row["description"] if "description" in row else None,
                "account_name": row["account_name"] if "account_name" in row else None,
                "account_id": row["account_id"] if "account_id" in row else None,
                "category_name": (
                    row["category_name"] if "category_name" in row else None
                ),
                "category_id": row["category_id"] if "category_id" in row else None,
                "is_transfer": row["is_transfer"] if "transfer" in row else None,
                "concilied": row["concilied"] if "concilied" in row else None,
            }
        )

    return listOfTransactions


def parseXLSX(import_file):
    rows = pl.read_excel(
        source=io.BytesIO(import_file.read())
    ).rows(named=True)
    

    listOfTransactions = []
    for row in rows:
        row = dict((k.lower(), v) for k,v in row.items())
        if not "value" in row or not "date" in row or not "description" in row:
            raise ValidationError(
                "Excel file doesn't have all the columns needed: date, description and value"
            )
            break
        # we try to convert the dates:
        row["date"] = strToDate_anyformat(row["date"])

        listOfTransactions.append(
            {
                "select_row": False,
                "value": row["value"] if "value" in row else None,
                "date": row["date"] if "date" in row else None,
                "competency_date": (
                    row["competency_date"] if "competency_date" in row else None
                ),
                "description": row["description"] if "description" in row else None,
                "account_name": row["account_name"] if "account_name" in row else None,
                "account_id": row["account_id"] if "account_id" in row else None,
                "category_name": (
                    row["category_name"] if "category_name" in row else None
                ),
                "category_id": row["category_id"] if "category_id" in row else None,
                "is_transfer": row["is_transfer"] if "transfer" in row else None,
                "concilied": row["concilied"] if "concilied" in row else None,
            }
        )

    return listOfTransactions

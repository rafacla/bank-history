import csv
import re
from django.core.exceptions import ValidationError
from datetime import date, datetime
from pdfquery import PDFQuery
import fitz


def strToDate_anyformat(format_date, expected_format=""):
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


def parseCSV(import_file):
    csv_reader = csv.DictReader(import_file.read().decode("utf-8-sig").splitlines())

    listOfTransactions = []
    for row in csv_reader:
        if not "value" in row or not "date" in row or not "description" in row:
            raise ValidationError(
                "CSV file doesn't have all the columns needed: date, description and value"
            )
            break
        # we try to convert the dates:
        row["value"] = row["value"].replace(" ", "")
        row["date"] = strToDate_anyformat(row["date"])

        listOfTransactions.append(
            {
                "select_row": False,
                "value": row["value"] if "value" in row else None,
                "date": row["date"] if "date" in row else None,
                "competency_date": row["competency_date"] if "competency_date" in row else None,
                "description": row["description"] if "description" in row else None,
                "account_name": row["account_name"] if "account_name" in row else None,
                "account_id": row["account_id"] if "account_id" in row else None,
                "category_name": row["category_name"] if "category_name" in row else None,
                "category_id": row["category_id"] if "category_id" in row else None,
                "is_transfer": row["is_transfer"] if "transfer" in row else None,
                "concilied": row["concilied"] if "concilied" in row else None,
            }
        )

    return listOfTransactions


def parsePDF(import_file):
    pdf = fitz.open(stream=import_file.read(), filetype="pdf")
    
    def getValuesFromKey(key, below=True, right=False):
        list = []
        for page in pdf:
            rectsFound = page.search_for(key)
            for rectFound in rectsFound:
                x0 = rectFound[2] if right else rectFound[0]
                y0 = rectFound[3] if below else rectFound[1]
                x1 = rectFound[2]-rectFound[0]+x0 if right else rectFound[2]
                y1 = rectFound[3]-rectFound[1]+y0 if below else rectFound[3]
                rectExtract = fitz.Rect(x0, y0, x1, y1)
                list.append(page.get_textbox(rectExtract))
        return list


    # Initialize list of Transactions 
    listOfTransactions = []

    ### For PDF files, there's no standard, so we need to use masks for each kind of statement...
    # The following ifs are used to identify if the statement mask has been catalogued:

    # Itau Credit Card as of January-24
    if pdf[0].search_for("Com vencimento em:"):
        # For credit cards, we match the competency date with the due date of the statement
        competency_date = strToDate_anyformat(getValuesFromKey("Com vencimento em:")[0])
        def getTables():
            list = []
            for page in pdf:
                # Here we tell the script where to look in the statement:
                vertical_lines_coordiantes =[
                    [154, 177, 310, 345],
                    [370, 392, 518, 560]
                ]
                for vlc in vertical_lines_coordiantes:
                    tabs = page.find_tables(horizontal_strategy='lines_strict', vertical_lines=vlc)
                    for table in tabs.tables:
                        if table.col_count == 3:
                            for row in table.extract():
                                # as in itau CC statement transactions doesn't have the year, we need to consider that the year is the same of competency dates
                                # except if the transaction date would result in a date greater then competency_date (due date of statement), in this case we should consider the past year
                                rowDate = strToDate_anyformat(row[0]+'/'+str(competency_date.year))
                                if isinstance(rowDate, date):
                                    if rowDate > competency_date:
                                        rowDate = strToDate_anyformat(row[0]+'/'+str(competency_date.year - 1))
                                    listOfTransactions.append(
                                        {
                                            "select_row": False,
                                            "value": float(str(row[2]).replace(",",".")),
                                            "date": rowDate,
                                            "competency_date": competency_date,
                                            "description": str(row[1]).replace("\n"," (").replace(" .","/")+")",
                                            "account_name": None,
                                            "account_id": None,
                                            "category_name": None,
                                            "category_id": None,
                                            "is_transfer": None,
                                            "concilied": None,
                                        }
                                    )
            return list

        tableList = getTables()   

    return listOfTransactions



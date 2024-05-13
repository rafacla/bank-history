import fitz
from banking.utils import strToDate_anyformat
from datetime import date, datetime, timedelta

class PDFParser:
    file: fitz.Document
    
    def __init__(self, file):
        self.file = fitz.open(stream=file, filetype="pdf")

    def getValuesFromKey(self, key, below=True, right=False, dx0=0, dx1=0, dy0=0, dy1=0):
        list = []
        for page in self.file:
            rectsFound = page.search_for(key)
            for rectFound in rectsFound:
                x0 = rectFound[2] if right else rectFound[0]
                y0 = rectFound[3] if below else rectFound[1]
                x1 = rectFound[2] - rectFound[0] + x0 if right else rectFound[2]
                y1 = rectFound[3] - rectFound[1] + y0 if below else rectFound[3]
                rectExtract = fitz.Rect(x0 + dx0, y0 + dy0, x1 + dx1, y1 + dy1)
                list.append(page.get_textbox(rectExtract))
        return list

    def brazilItauCreditCardJan24(self):
        listOfTransactions = []

        # For credit cards, we match the competency date with the due date of the statement
        competency_date = strToDate_anyformat(self.getValuesFromKey("Com vencimento em:")[0])

        for page in self.file:
            # Here we tell the script where to look in the statement:
            vertical_lines_coordiantes = [[154, 177, 310, 345], [370, 392, 518, 560]]
            for vlc in vertical_lines_coordiantes:
                tabs = page.find_tables(
                    horizontal_strategy="lines_strict", vertical_lines=vlc
                )
                for table in tabs.tables:
                    if table.col_count == 3:
                        for row in table.extract():
                            # as in itau CC statement transactions doesn't have the year, we need to consider that the year is the same of competency dates
                            # except if the transaction date would result in a date greater then competency_date (due date of statement), in this case we should consider the past year
                            rowDate = strToDate_anyformat(
                                row[0] + "/" + str(competency_date.year)
                            )
                            if isinstance(rowDate, date):
                                if rowDate > competency_date:
                                    rowDate = strToDate_anyformat(
                                        row[0] + "/" + str(competency_date.year - 1)
                                    )
                                listOfTransactions.append(
                                    {
                                        "select_row": False,
                                        "value": float(
                                            str(row[2])
                                            .replace(",", ".")
                                            .replace(" ", "")
                                        )
                                        * (-1),
                                        "date": rowDate,
                                        "competency_date": competency_date,
                                        "description": str(row[1])
                                        .replace("\n", " (")
                                        .replace(" .", "/")
                                        + ")",
                                        "account_name": None,
                                        "account_id": None,
                                        "category_name": None,
                                        "category_id": None,
                                        "is_transfer": None,
                                        "concilied": None,
                                    }
                                )

        if self.getValuesFromKey("Pagamento efetuado em ", below=False, right=True):
            payment_last_statement_date =self. getValuesFromKey(
                "Pagamento efetuado em ", below=False, right=True
            )[0]
            payment_last_statement_value = float(
               self. getValuesFromKey(
                    "Pagamento efetuado em ", below=False, right=True, dx0=50, dx1=50
                )[0]
                .replace(" ", "")
                .replace(".", "")
                .replace(",", ".")
            ) * (-1)
            if strToDate_anyformat(payment_last_statement_date):
                listOfTransactions.append(
                    {
                        "select_row": False,
                        "value": payment_last_statement_value,
                        "date": strToDate_anyformat(payment_last_statement_date),
                        "competency_date": None,
                        "description": "Pagamento efetuado em "
                        + payment_last_statement_date,
                        "account_name": None,
                        "account_id": None,
                        "category_name": None,
                        "category_id": None,
                        "is_transfer": True,
                        "concilied": None,
                    }
                )

        return listOfTransactions
        
    def parse(self):
        # this function should identify the statement we are importing, and find the correct function to parse

        # Itau Credit Card as of January-24
        # this is a bad example of check for uniqueness of this kind of statement.. ideally we should lock a position and check for a specific string
        if self.file[0].search_for("Com vencimento em:"):
            return self.brazilItauCreditCardJan24()
        else:
            return []
from datetime import date, datetime
import csv
import re

def strToDate_anyformat(format_date, expected_format = ""):
        numbers = ''.join(re.findall(r'\d+', format_date))
        if ("/" in format_date or expected_format.upper() == "%D/%M/%Y" or expected_format.upper() == "%M/%D/%Y"):
            #in this case, we consider the date as short_date, defaulting to %d/%m/%Y
            if (expected_format == "" or expected_format.upper() == "%D/%M/%Y"):
                if len(numbers) == 8 and int(numbers[2:4]) <= 12:
                    d = datetime(int(numbers[4:8]), int(numbers[2:4]), int(numbers[:2]))
                elif len(numbers) == 6:
                    d = datetime(int(numbers[4:6])+2000, int(numbers[2:4]), int(numbers[:2]))
                else:
                    raise AssertionError(f'length not match:{format_date} or doesn\'t fit the expected format: '+expected_format)
            else:
                #it's in american standard:
                if len(numbers) == 8 and int(numbers[:2]) <= 12:
                    d = datetime(int(numbers[4:8]), int(numbers[:2]), int(numbers[2:4]))
                elif len(numbers) == 6:
                    d = datetime(int(numbers[4:6])+2000, int(numbers[:2]), int(numbers[2:4]))
                else:
                    raise AssertionError(f'length not match:{format_date} or doesn\'t fit the expected format: '+expected_format)
        else:
            #else, it's a full date:
            if len(numbers) == 8:
                d = datetime(int(numbers[:4]), int(numbers[4:6]), int(numbers[6:8]))
            elif len(numbers) == 14:
                d = datetime(int(numbers[:4]), int(numbers[4:6]), int(numbers[6:8]), int(numbers[8:10]), int(numbers[10:12]), int(numbers[12:14]))
            elif len(numbers) > 14:
                d = datetime(int(numbers[:4]), int(numbers[4:6]), int(numbers[6:8]), int(numbers[8:10]), int(numbers[10:12]), int(numbers[12:14]), microsecond=1000*int(numbers[14:]))
            else:
                raise AssertionError(f'length not match:{format_date}')
        return d

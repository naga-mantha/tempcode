from datetime import date
from dateutil.relativedelta import relativedelta
from django.core.management import call_command
from shutil import copyfile
import os
from datetime import date, timedelta
import pandas as pd
from numpy import nan

today = date.today()

def read_text_contents(filename, ignore_line_list):
    no_days = 0
    full_filename = filename + today.strftime("%m-%d-%y") + ".txt"

    # If file doesnt exist, check for the previous days
    while not os.path.exists(full_filename) and no_days < 10:
        no_days += 1
        full_filename = filename + (today - timedelta(days=no_days)).strftime("%m-%d-%y") + ".txt"

    file_copy = "copy of " + os.path.basename(full_filename)
    copyfile(full_filename, file_copy)

    # Read with encoding fallback to safely handle accented characters
    def _read_lines(path):
        last_err = None
        for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
            try:
                with open(path, "r", encoding=enc) as f:
                    return f.readlines()
            except UnicodeDecodeError as e:
                last_err = e
                continue
        # Final fallback with replacement to avoid crashing (preserve as much as possible)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()

    lines = _read_lines(file_copy)

    # Write cleaned copy in UTF-8 to normalize downstream reading
    with open(file_copy, "w", encoding="utf-8") as f:
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Skip header/separator or ignored prefixes
            if line.startswith(tuple(ignore_line_list)):
                continue
            f.write(line)
            f.write("\n")

    return file_copy


def check_file_line(line):
    currentline = line.split("|")
    for i in range(0, len(currentline)):
        if currentline[i].strip()[:2] == "##":
            return False

    return True

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

    # Open the copied file and read the contents
    with open(file_copy, "r") as f:
        lines = f.readlines()

    with open(file_copy, "w") as f:
        for line in lines:
            # First we strip off all the blank spaces before and after the line
            line = line.strip()

            # Next we loop through each line and check if its blank or contains certain text. If it does, we skip them
            if not line.startswith(tuple(ignore_line_list), 0) and line[0:1:1] != "":
                f.write(line)
                f.write("\n")

    return file_copy


def check_file_line(line):
    currentline = line.split("|")
    for i in range(0, len(currentline)):
        if currentline[i].strip()[:2] == "##":
            return False

    return True
"""
This module provides a date handler. Again, json would make this
class useless.
"""

from datetime import date


class DateHandler:
    """ This class provides the parsing for dates. """

    def __init__(self, date_input=None):
        """
        __init__ - handles parsing the date into a datetime object
        :param date_input: string form of the date from the preferences
        """
        self.date = None
        if "/" in date_input:
            dates = date_input.split("/")
            self.date = date(int(dates[2]), int(dates[0]), int(dates[1]))
        elif "-" in date_input:
            dates = date_input.split("-")
            self.date = date(int(dates[2]), int(dates[0]), int(dates[1]))
        else:
            raise Exception()

    @staticmethod
    def datetime_to_short_text(datetime):
        return str(datetime.strftime("%b")) + " " + \
               str(datetime.strftime("%-d")) + ", " + \
               str(datetime.strftime("%Y"))

    @staticmethod
    def datetime_to_normal_text(datetime):
        return str(datetime.strftime("%m")) + "/" + \
               str(datetime.strftime("%d")) + "/" + \
               str(datetime.strftime("%Y"))

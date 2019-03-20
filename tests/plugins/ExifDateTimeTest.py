import unittest
from plugins import ExifDateTime
from datetime import datetime


class ExifDateTimeTests(unittest.TestCase):
    def test_random_date(self):
        date = ExifDateTime.random_date("01-01-2010", "12-31-2020")
        assert(date is not False)
        assert(datetime.strptime("01-01-2010", "%m-%d-%Y").date() <=
               datetime.strptime(date, "%Y:%m:%d").date() <=
               datetime.strptime("12-31-2020", "%m-%d-%Y").date())

        date = ExifDateTime.random_date("12-31-2020", "01-01-2010")
        assert(date is False)

        date = ExifDateTime.random_date("12-31-2020", "12-31-2020")
        assert(date is not False)
        assert(datetime.strptime(date, "%Y:%m:%d").date() == datetime.strptime("12-31-2020", "%m-%d-%Y").date())

    def test_random_time(self):
        time = ExifDateTime.random_time("23:00:00", "03:00:00")
        assert(time is not False)

        time = ExifDateTime.random_time("08:00:00", "12:00:00")
        assert(time is not False)
        assert(datetime.strptime("08:00:00", "%H:%M:%S").time() <=
               datetime.strptime(time, "%H:%M:%S").time() <=
               datetime.strptime("12:00:00", "%H:%M:%S").time())

        time = ExifDateTime.random_time("15:00:00", "15:00:00")
        assert(time is not False)
        assert(datetime.strptime("15:00:00", "%H:%M:%S").time() ==
               datetime.strptime(time, "%H:%M:%S").time())

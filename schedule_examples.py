import unittest
import schedule
import time
import datetime



def job():
    print('I am working as scheduler....!')


class UnitTest(unittest.TestCase):

    def test_every_xxx(self):
        print(datetime.datetime.now())

        print(schedule.every().minute.do(lambda: None))
        print(schedule.every().hour.do(lambda: None))
        print(schedule.every().day.do(lambda: None))
        print(schedule.every().monday.do(lambda: None))
        print(schedule.every().week.do(lambda: None))

        # while True:
        #     schedule.run_pending()
        #     time.sleep(1)

    def test_every_xxx_at(self):
        print(datetime.datetime.now())

        print(schedule.every().minute.at(":05").do(lambda: None))
        with self.assertRaises(schedule.ScheduleValueError):
            print(schedule.every().minute.at("05:05").do(lambda: None))
        print(schedule.every().hour.at(":10").do(lambda: None))
        print(schedule.every().day.at("15:00").do(lambda: None))
        print(schedule.every().monday.at("20:00").do(lambda: None))
        with self.assertRaises(schedule.ScheduleValueError):
            schedule.every().week.at("00:00").do(lambda: None)

        print("===")

        print(schedule.every(2).minutes.at(":05").do(lambda: None))
        print(schedule.every(2).hours.at(":15").do(lambda: None))
        print(schedule.every(2).days.at("15:00").do(lambda: None))

        # while True:
        #     schedule.run_pending()
        #     time.sleep(1)




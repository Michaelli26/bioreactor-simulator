import unittest
import pandas as pd
import numpy as np
import deviation_notifier
import datetime


class TestNotifier(unittest.TestCase):

    def test_check_constants(self):
        temp_normal = pd.Series(np.array([32.1, 32.0, 31.6, 32.4, 31.0, 33.0]))
        temp_up = pd.Series(np.array([32.0, 31.2, 32.5, 33, 33.5, 34, 34.2, 34.6]))
        temp_down = pd.Series(np.array([32.0, 31.2, 32.5, 31.3, 30.6, 29.6, 29, 29]))

        self.assertIsNone(deviation_notifier.check_constants(temp_normal, 32, 3))
        self.assertEqual(deviation_notifier.check_constants(temp_up, 32, 2), 6)
        self.assertEqual(deviation_notifier.check_constants(temp_down, 32, 2), 5)

    def test_check_pumps(self):
        # for quick reference
        # pump_specs = {'Base Pump [mL/hr]': {'on': 5, 'off': 320}, 'Feed Pump [ml/hr]': {'on': 50, 'off': 320},
        #             'Antifoam Pump [mL/hr]': {'on': 20, 'off': 180}}
        zeroes = pd.Series(np.array([0, 0, 0, 0, 0, 0, 0, 0]))
        off_pre_trigger = pd.Series(np.array([30, 0, 0, 0, 0]))
        feed_on = pd.Series(np.array([0, 0, 40, 40, 40, 40, 40, 40]))
        feed_up = pd.Series(np.array([40, 41, 42, 44, 45, 46, 48, 50, 51, 49]))
        feed_down = pd.Series(np.array([40, 42, 39, 40, 37, 36, 35, 34.2, 33.1, 32.0]))

        self.assertEqual(deviation_notifier.check_pumps('Feed Pump [ml/hr]', off_pre_trigger, 40, 3), (1, 660))
        self.assertEqual(deviation_notifier.check_pumps('Feed Pump [ml/hr]', zeroes, 40, 3), (0, 660))
        self.assertEqual(deviation_notifier.check_pumps('Feed Pump [ml/hr]', feed_on, 40, 3), (2, 50))
        self.assertEqual(deviation_notifier.check_pumps('Feed Pump [ml/hr]', feed_up, 40, 3), (3, 5))
        self.assertEqual(deviation_notifier.check_pumps('Feed Pump [ml/hr]', feed_down, 40, 3), (5, 5))

        base_on = pd.Series(np.array([0, 0, 35, 35, 35, 35, 35, 35, ]))
        base_up = pd.Series(np.array([35.0, 36, 35.6, 37.0, 37.9, 38, 39, 39]))
        base_up2 = pd.Series(np.array([0, 0, 0, 0, 40.0, 40.0, 40.0, 40.0, 40.0]))
        base_down = pd.Series(np.array([35, 33, 34, 32, 31, 31.0, 30.8, 30, 29, 30.4]))

        self.assertEqual(deviation_notifier.check_pumps('Base Pump [mL/hr]', base_on, 35, 3), (2, 5))
        self.assertEqual(deviation_notifier.check_pumps('Base Pump [mL/hr]', base_up, 35, 3), (6, 5))
        self.assertEqual(deviation_notifier.check_pumps('Base Pump [mL/hr]', base_up2, 35, 3), (4, 5))
        self.assertEqual(deviation_notifier.check_pumps('Base Pump [mL/hr]', base_down, 35, 3), (4, 5))

    def test_agitation(self):
        pre_ramp = pd.Series(np.array([999.0, 998.0, 1000.0, 1002.0, 1001, 999.5]))
        ramp = pd.Series(np.array([1000, 999.8, 1001.2, 1001, 1000.6, 1500]))

        self.assertTrue(deviation_notifier.agitation(ramp))
        self.assertFalse(deviation_notifier.agitation(pre_ramp))

    def test_check_pH(self):
        missed_trigger = pd.Series(
            np.array([7.2071, 7.2065, 7.2102, 7.21, 7.214, 7.212, 7.2133, 7.2144, 7.2206, 7.2221, 7.2232, 7.2244,
                      7.2306, 7.2272, 7.2324, 7.2351, 7.2379, 7.2383, 7.2385, 7.2441, 7.2455, 7.2488, 7.2451,
                      7.2507, 7.2486, 7.2541, 7.2532, 7.2609, 7.2581, 7.2655, 7.2611, 7.2639, 7.2647, 7.2695,
                      7.2719, 7.2734, 7.2763, 7.2753, 7.2833, 7.2838, 7.286, 7.288, 7.2909, 7.2909]))

        self.assertEqual(deviation_notifier.check_pH(missed_trigger, max_ph=7.27), 34)

    def test_check_time(self):
        timestamps = pd.Series(np.array([
            datetime.datetime(2019, 11, 7, 12, 1),
            datetime.datetime(2019, 11, 7, 12, 2),
            datetime.datetime(2019, 11, 7, 12, 3),
            datetime.datetime(2019, 11, 7, 12, 4),
            datetime.datetime(2019, 11, 7, 12, 5),
            datetime.datetime(2019, 11, 7, 12, 6),
            datetime.datetime(2019, 11, 7, 12, 7),
            datetime.datetime(2019, 11, 7, 12, 8),
            datetime.datetime(2019, 11, 7, 12, 9)]))

        self.assertTrue(deviation_notifier.check_time(timestamps, 2))
        self.assertFalse(deviation_notifier.check_time(timestamps, 3))
        self.assertTrue(deviation_notifier.check_time(timestamps, 0, minutes=7))

if __name__ == '__main__':
    unittest.main()

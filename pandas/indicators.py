#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import pandas as pd
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import numpy as np
import talib as ta

pd.set_option('expand_frame_repr', False)


class UnitTest(unittest.TestCase):
    timeperiod = 20
    close = pd.Series([9.0, 9.2, 9.5, 9.6, 9.7, 9.9, 10.2, 10.2, 10.8, 11.0,
                       11.2, 11.5, 11.5, 11.6, 11.4, 11.3, 11.0, 10.8, 10.9,
                       10.8, 10.8, 10.3, 10.4, 10.5, 10.9, 11.0, 10.9, 10.8,
                       10.7, 10.7, 10.4, 10.3, 10.2, 10.0, 9.6, 9.3, 9.0, 8.5,
                       8.5, 8.2, 8.0, 9.1, 9.5, 9.9, 10.5, 10.6, 10.8, 10.9,
                       11.4, 11.5, 11.6, 12.0, 12.3, 12.4, 12.6, 9.9, 9.8, 9.5,
                       9.3, 8.9, 8.5, 8.3, 8.2, 8.0, 7.8, 7.3, 7.2, 7.1, 7.1,
                       7.7, 7.8, 7.9, 8.5, 8.8, 8.9, 9.3, 9.5, 9.7, 9.9, 10.0,
                       11.3, 11.5, 11.7, 12.3, 12.5, 12.6, 12.9, 12.8, 12.3,
                       11.3, 11.0, 10.4, 10.2, 10.1, 9.9, 9.8, 9.3, 9.1, 9.0,
                       9.1, 9.1, 9.5, 9.7, 9.9, 10.6, 10.7, 10.9, 10.9, 11,
                       11.1, 11.2, 11.5, 11.9, 12.1, 12.6, 12.6, 12.5, 12.2, 12.1,
                       10.9, 10.9, 11.0, 11.3, 10.7, 9.9, 9.9, 9.8, 9.5, 10.0,
                       ])

    @staticmethod
    def _hma(close, timeperiod):
        """Hull Moving Average (HMA)

        Fidelity:   https://bit.ly/2Jhuvge
        InstaForex: https://bit.ly/2Hi4Su0
        """
        n = timeperiod
        n1 = np.ceil(timeperiod / 2)
        n2 = np.ceil(np.sqrt(timeperiod))
        hma = ta.WMA(2 * ta.WMA(close, n1) - ta.WMA(close, n), n2)
        return pd.Series(hma, name=f'HMA({timeperiod})')

    def test_moving_average(self):
        self.close.plot(label='data', style='--')

        for ma_type in ['DEMA', 'MAMA', 'TEMA', 'EMA', 'SMA', 'TRIMA', 'KAMA', 'T3', 'WMA']:
            s = ta.MA(self.close, self.timeperiod, getattr(ta.MA_Type, ma_type))
            pd.Series(s, name=f'{ma_type}({self.timeperiod})').plot()

        self._hma(self.close, self.timeperiod).plot()

        plt.legend(fontsize='x-small')
        plt.show()


if __name__ == '__main__':
    unittest.main(verbosity=2)

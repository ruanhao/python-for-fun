#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import pandas as pd
import numpy as np
from datetime import date

pd.set_option('expand_frame_repr', False)
pd.options.display.max_columns = 999

class UnitTest(unittest.TestCase):

    def test_pivot_table(self):
        '''
        查看每个分类(index)每年(columns)的销售总量(values)
        参考：https://www.bilibili.com/video/av36643275?p=23
        '''

        orders = pd.read_excel('data/Orders.xlsx', dtype={'Date': date})
        orders['Year'] = pd.DatetimeIndex(orders.Date).year  # 年份列需要手工加入

        pt = orders.pivot_table(index='Category', columns='Year', values='Total', aggfunc=np.sum)
        print(pt)

        with self.subTest("Use groupby to generate pivot table"):
            groups = orders.groupby(['Category', 'Year'])
            s = groups['Total'].sum()
            c = groups['ID'].count()
            pt = pd.DataFrame({'Sum': s, 'Count': c})
            print(pt)

            print(pt.drop(columns=['Count']).unstack().droplevel(level=0, axis=1))  # same output as by pivot_table









if __name__ == '__main__':
    unittest.main(verbosity=2)

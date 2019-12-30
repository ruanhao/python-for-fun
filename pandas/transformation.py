#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import pandas as pd
import numpy as np

pd.set_option('expand_frame_repr', False)
pd.options.display.max_columns = 999

class UnitTest(unittest.TestCase):

    def test_splitting_col_into_cols(self):
        '''
        将一列数据分割成多列
        '''
        employees = pd.read_excel('data/Employees.xlsx', index_col='ID')
        df = employees['Full Name'].str.split(expand=True)
        employees['First Name'] = df[0]
        employees['Last Name'] = df[1]
        print(employees)

    def test_rotation(self):
        '''
        行变列，列变行
        '''
        videos = pd.read_excel('data/Videos.xlsx', index_col='Month')
        # table = videos.transpose()
        table = videos.T
        print(table)









if __name__ == '__main__':
    unittest.main(verbosity=2)

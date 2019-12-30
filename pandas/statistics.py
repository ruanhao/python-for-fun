#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import pandas as pd
import numpy as np

pd.set_option('expand_frame_repr', False)


class UnitTest(unittest.TestCase):

    def test_calculating_statistics(self):
        students = pd.read_excel('data/Students_3_Scores.xlsx', index_col='ID')

        row_sum = students[['Test_1', 'Test_2', 'Test_3']].sum(axis=1)
        row_mean = students[['Test_1', 'Test_2', 'Test_3']].mean(axis=1)

        students['Total'] = row_sum
        students['Average'] = row_mean

        col_mean_row = students[['Test_1', 'Test_2', 'Test_3', 'Total', 'Average']].mean()
        col_mean_row['Name'] = 'Summary'
        students = students.append(col_mean_row, ignore_index=True)
        print(students)






if __name__ == '__main__':
    unittest.main(verbosity=2)

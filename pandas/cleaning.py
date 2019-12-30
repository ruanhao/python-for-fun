#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import pandas as pd
import numpy as np

pd.set_option('expand_frame_repr', False)


class UnitTest(unittest.TestCase):

    def test_deleting_duplication(self):
        students = pd.read_excel('data/Students_Duplicates.xlsx')
        dupe = students.duplicated(subset='Name')
        dupe = dupe[dupe == True]  # dupe = dupe[dupe]
        print(students.iloc[dupe.index])  # 找出去除的条目
        print("=========")
        students.drop_duplicates(subset='Name', inplace=True, keep='last')
        print(students)





if __name__ == '__main__':
    unittest.main(verbosity=2)

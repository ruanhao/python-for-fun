#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import pandas as pd
import numpy as np

pd.set_option('expand_frame_repr', False)


class UnitTest(unittest.TestCase):

    def test_verifying(self):
        '''
        校验行数据
        '''
        def _score_validate(row):
            try:
                assert 0 <= row.Score <= 100
            except:
                print(f'#{row.ID}\tstudent {row.Name} has an invalid score {row.Score}')

        students = pd.read_excel('data/students_verify.xlsx')
        # axis=0 表示从上到下，axis=1 表示从左到右，一条数据(row)是从左到右表示的，因此这里使用 axis=1
        students.apply(_score_validate, axis=1)







if __name__ == '__main__':
    unittest.main(verbosity=2)

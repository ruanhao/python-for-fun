#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import pandas as pd
import numpy as np

pd.set_option('expand_frame_repr', False)


class UnitTest(unittest.TestCase):

    def test_merging_on_a_common_col(self):
        students = pd.read_excel('data/students_score.xlsx', sheet_name='Students')
        scores = pd.read_excel('data/students_score.xlsx', sheet_name='Scores')
        # print(students)
        # print(scores)

        inner_table = students.merge(scores, on='ID')
        # print(inner_table)
        self.assertFalse((inner_table['ID'] == 2).any(), 'Inner join is used here')

        left_table = students.merge(scores, on='ID', how='left')
        self.assertTrue((left_table['ID'] == 2).any(), 'All ids in scores table should exist')
        self.assertTrue(np.isnan(left_table[left_table['ID'] == 2].iloc[0]['Score']), "Score for student#2 is missing")
        left_table.fillna(0, inplace=True);             # fill na
        left_table.Score = left_table.Score.astype(int)  # change type

        with self.subTest("Use join"):
            '''
            join 底层使用的仍然是 merge ，根据*索引*合并(默认是左连接)
            '''
            students = pd.read_excel('data/students_score.xlsx', sheet_name='Students', index_col='ID')
            scores = pd.read_excel('data/students_score.xlsx', sheet_name='Scores', index_col='ID')
            table = students.join(scores).fillna(0)
            print(table)





if __name__ == '__main__':
    unittest.main(verbosity=2)

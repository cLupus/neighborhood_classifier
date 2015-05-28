# -*- coding: utf-8 -*-
__author__ = 'Sindre Nistad'

import Database.connector as conn


def run():
    conn.connect(True)
    conn.export_to_csv('soil')
    # dataset = conn.get_dataset_sample('soil', 3, number_of_samples=20)
    # print(dataset)
    pass


run()
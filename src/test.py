# -*- coding: utf-8 -*-
__author__ = 'Sindre Nistad'

import Database.connector as conn
import Classifier.neural_network as nn


def run():
    # conn.bind()
    # conn.disconnect(True, True)
    conn.connect()
    # set_norm_points_table(True)
    # set_extended_point_table(True)
    # conn.export_to_csv(dataset="AVIRIS", k=0)
    k = 3
    dataset = conn.get_dataset_sample('soil', k, normalizing_mode='min-max', dataset='AVIRIS', number_of_samples=20,
                                      use_stored_normalization_values=False)
    # print(dataset)
    net = nn.ClassificationNet(0, 1, dataset, k, 'soil')
    net.divide_dataset(0.2)

    print(net)
    pass


run()
# -*- coding: utf-8 -*-
__author__ = 'Sindre Nistad'

from pickle import load

import neurolab.train as train

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
    # dataset = conn.get_dataset_sample('soil', k, normalizing_mode='gaussian', dataset='AVIRIS',
    #                                   number_of_samples=-1,
    #                                   background_target_ratio=1.5,
    #                                   use_stored_normalization_values=False)
    f = open('soil.ds.pkl', 'rb')
    # dump(dataset, f)
    dataset = load(f)
    # print(dataset)

    minimum = dataset.min()
    maximum = dataset.max()
    transfer_functions = None  # [nltf.TanSig(), nltf.TanSig()]

    net = nn.ClassificationNet(minimum, maximum, dataset, k, 'soil', transfer_functions=transfer_functions,
                               training_function=train.train_gd)
    # net.net.errorf = nle.MSE()
    net.net.init()
    net.divide_dataset(0.25)

    net.train(1000, 0.01)
    net.net.save('soil.neuralnetwork')
    err = net.test()
    print(err)
    print(err.sum() / err.size)
    # pass


run()

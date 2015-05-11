# -*- coding: utf-8 -*-
__author__ = 'Sindre Nistad'

from Classifier.neural_network import ClassificationNet

from RegionOfInterest.export import get_roi

import Database.connector as conn


def run():
    # soil = net.data_set.data.

    # #print(net)
    # best = hidden_layer_to_input_output_layers(0, ['soil'], [0.8, 1], 0.02, 3)
    # best.save('../best.nn')
    # t = [folder + targets[0] + extension, folder + targets[1] + extension]
    #merge_roi_files(t)

    # files = get_file_list()
    # normalized_files = get_file_list(True)
    # roi_master_r19 = RegionsOfInterest(files[0], normalizing_path=normalized_files[0], normalize=False)
    # aviris_r19 = RegionsOfInterest(files[1], normalizing_path=normalized_files[0])
    #print roi_master_r19.standard_deviations

    # roi_master_r19.save_to_csv(";", "../master_r19.csv")
    # create_database(overwrite=False, create_tables=True, check_tables=True)
    conn.connect()
    # drop_tables(True)
    #roi_to_database(roi_master_r19)
    # export_to_potgres(debug=True, add_wavelengths=True, start_index=2, force_load=True)
    #add_wavelength_to_dataset()
    sample = conn.get_points_from_region('soil', normalizing_mode='min-max', k=3)
    print(sample)
    pass


def run_neural_network(i, mode='guass', target=None, neigborhood_size=3,
                       targets_background_ration=None, hidden_ratio=0.98,
                       learning_rate=0.2, verbose=True, momentum=0.1, weight_decay=0.,
                       max_epochs=10):
    """
        Aggregate method for reading all the data, and then creating a neural network, training it, and saving it.
    :param i:                           The index of which file is to be loaded
    :param mode:                        How is the data going to be normalized? max-min or gaussian.
                                        The latter is default
    :param target:                      What do we consider to be the target of interest? Everything else will be
                                        considered background.
    :param neigborhood_size:            The size of the neighborhood. Default is 3.
    :param targets_background_ration:   The ratios of targets to background. Default is 1:1.
    :param hidden_ratio:                The ratio of hidden nodes to input plus output nodes.
    :param learning_rate:               The learning rate for the back-propagation algorithm.
    :param verbose:                     Toggles verbose mode on or off. Default is on.
    :param momentum:                    The momentum (previous round) of the learning algorithm to use. Default is 0.1.
    :param weight_decay:                How fast the weighs are decaying. Default is 0.
    :param max_epochs:                  The maximum number of epochs the algorithm will run. Default is 10.

    :type i:                            int
    :type mode:                         str
    :type target:                       list of [str] | str
    :type neigborhood_size:             int
    :type targets_background_ration:    list of [float]
    :type hidden_ratio:                 float
    :type learning_rate:                float
    :type verbose:                      bool
    :type momentum:                     float
    :type weight_decay:                 float
    :type max_epochs:                   int
    :return:                            None
    :rtype:                             None
    """
    # Defaults
    if target is None:
        target = ['soil']
    if targets_background_ration is None:
        targets_background_ration = [1., 1.]

    roi = get_roi(i, normalized=False)
    roi.set_aggregate(True)
    net = ClassificationNet(roi, target, neigborhood_size=neigborhood_size,
                            targets_background_ration=targets_background_ration, hidden_ratio=hidden_ratio)
    net.neural_net.randomize()

    net.set_trainer(learning_rate=learning_rate, verbose=verbose, momentum=momentum, weight_decay=weight_decay)
    net.train_network(max_epochs=max_epochs, verbose=verbose)
    name = target[0] + '.nn'
    net.save('../' + name)

run()
# -*- coding: utf-8 -*-
"""
A collection of methods that can search for good parameters for the neural network
"""
__author__ = 'Sindre Nistad'


from neural_network import ClassificationNet
from regions_of_interest import RegionsOfInterest

folder = '../ASCII roi/'
normalized = 'normalizing/'
targets = ['master_r19_7_5_emissivity_sub', 'sb_r19_sub_sub_corrected', 'sb_r20_2011_rfl_sub',
           'sb_r21_sub_sub_corrected', 'sb_r22_sub_sub_corrected_colored']
extension = '.txt'


def hidden_layer_to_input_output_layers(target_index, target_regions, target_ratios,
                                        hidden_ratio_resolution, neighborhood_size):
    """
        Method to see which parameter works best
    :param target_index:            The index of which regions of interest we are to use from the list 'targets'.
    :param target_regions:          The regions we are interested in, e.g. 'soil', or 'rock'.
    :param target_ratios:           The ratios of targets vs. background.
    :param hidden_ratio_resolution: The ratio between hidden layers, and the sum of input and output layers.
    :param neighborhood_size:       The size of the neigborhood.

    :type target_index:             int
    :type target_regions:           list of [str]
    :type target_ratios:            list of [float]
    :type hidden_ratio_resolution:  float
    :type neighborhood_size:        int
    :return:                        The best neural network
    :rtype:                         ClassificationNet
    """
    path = folder + targets[target_index] + extension
    normalized_path = folder + normalized + targets[target_index] + extension
    rois = RegionsOfInterest(path, normalizing_path=normalized_path)
    net = ClassificationNet(rois, neigborhood_size=neighborhood_size, hidden_layer=1,
                            targets=target_regions, targets_background_ration=target_ratios)
    net.set_trainer()
    net.train_network(max_epochs=15, verbose=True, continue_epochs=10, validation_proportion=0.25, force_split=True)
    best = net
    ratios = [n * hidden_ratio_resolution for n in range(1, int(1/hidden_ratio_resolution))]
    for ratio in ratios:
        net = ClassificationNet(rois, neigborhood_size=neighborhood_size, hidden_ratio=ratio,
                                targets=target_regions, targets_background_ration=target_ratios)
        net.set_trainer()
        net.train_network(max_epochs=15, verbose=True, continue_epochs=10, validation_proportion=0.25, force_split=True)
        if net.is_better(best, best.data_set):
            best = net
    return best

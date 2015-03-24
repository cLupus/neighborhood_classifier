__author__ = 'Sindre Nistad'

from regions_of_interest import RegionsOfInterest


def run():
    file_list = ['master_r19_7_5_emissivity_sub.txt', 'sb_r19_sub_sub_corrected.txt', 'sb_r20_2011_rfl_sub.txt', 'sb_r21_sub_sub_corrected.txt', 'sb_r22_sub_sub_corrected_colored.txt']
    #prefix = '/Volumes/Kingston/Geog214a_data/ASCII roi/'
    prefix = '../ASCII roi/'
    norm = 'normalizing/'
    for itm in file_list:
        print "Now processing ", itm
        roi = RegionsOfInterest("".join([prefix, itm]))
        roi.read_normalizing_data(prefix + norm + itm)
        #roi.read_data()
        name = itm.split(".")[0]
        roi.save_to_file("".join([name, ".pkl"]))

run()

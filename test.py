__author__ = 'sindrenistad'

from regions_of_interest import RegionsOfInterest

def run():
    path = "/Volumes/Kingston/Geog214a_data/ASCII roi/sb_r19_sub_sub_corrected.txt"
    roi = RegionsOfInterest(path)
    roi.read_data()

run()
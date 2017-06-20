# -*- coding: utf-8 -*-
'''
Created on Jun 19, 2017

@author: tom
'''
from __future__ import absolute_import, division, unicode_literals, print_function
import logging
import os
import ujson


class CrawlerStatus(object):
    '''
    A CrawlerStatus object represents the status of collecting
    information from a website.
    '''
    status_filename = 'crawler_status'

    def __init__(self, status_folder):
        '''
        Builds a CrawlerStatus object.

        Args:
            status_folder: Path to the folder where the json file
                representing this status is stored.

        Raises:
            IOError: Invalid status folder.
        '''
        # Validation checks.
        if not os.path.isdir(status_folder):
            raise IOError('Invalid folder: {}'.format(status_folder))
        self.status_folder = status_folder
        self.cars = {}

    def load(self):
        '''
        Loads the json file relative to this status object and populates
        this status.
        '''
        status_filepath = os.path.join(self.status_folder,
                                       '{}.json'.format(self.status_filename))
        if not os.path.isfile(status_filepath):
            # There is no status json file yet: do nothing.
            return
        with open(status_filepath, 'r') as f:
            # TODO: we should validate what we load from the disk.
            self.cars = ujson.load(f)

    def save(self):
        '''
        Saves on disk this status object as a json file.
        '''
        status_filepath = os.path.join(self.status_folder,
                                       '{}.json'.format(self.status_filename))
        with open(status_filepath, 'w') as f:
            ujson.dump(self.cars, f, indent=4)

    def add(self, car_dict):
        '''
        Adds to this status the information about a car.

        This function is used to validate the data to insert into
        the crawling status.

        Args:
            car_dict: Dict containing the information about the car.

        Raises:
            ValueError: Invalid or incomplete car information.
        '''
        # Validation checks.
        if 'car_id' not in car_dict:
            raise ValueError('A car must have an id.')
        if 'car_price' not in car_dict:
            raise ValueError('A car must have a price.')
        if 'car_img_url' not in car_dict:
            raise ValueError('A car must have an image url.')

        self.cars[car_dict['car_id']] = car_dict

    def contains(self, car_id):
        '''
        Returns True if the queried car is already in our registry.

        Args:
            car_id: Identifies the queried car.

        Returns:
            True if the car information have already been collected.
        '''
        return car_id in self.cars

    @property
    def size(self):
        '''
        Number of cars collected so far.
        '''
        return len(self.cars)

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()


if __name__ == '__main__':
    logging.basicConfig()

# -*- coding: utf-8 -*-
'''
Created on Jun 19, 2017

@author: tom
'''
from __future__ import absolute_import, division, unicode_literals, print_function
from PIL import Image
from StringIO import StringIO
from bs4 import BeautifulSoup
from second_hand_cars.crawler_status import CrawlerStatus
from tqdm._tqdm import tqdm
import hashlib
import logging
import os
import urllib2
import argparse


'''
Crawls the AutoRicardo webiste.

Usage:
> python -m src.second_hand_cars.crawler \
    /home/tom/second_hand_cars_data \
    --num 1000 \
    --from-cheapest \
    --save-every 200 \
    --max-pages 1000 \

Arguments example to play with this script. Copy thiìe following in the
main() method.
[
    '/home/tom/second_hand_cars_data',
    '--num', '1000',
    '--from-cheapest',
    '--save-every', '200',
    '--max-pages', '1000',
]
'''


base_url = 'https://auto.ricardo.ch/search/results/?pn={}&po={}'
from_cheapest_code = 2
from_most_expensive_code = 3


def numeric_folder_structure(filename):
    '''
    Returns the relative path of the folder where the file
    should be located.

    Args:
        filename: Name of the file.

    Returns:
        The relative path of the subfolder where to store this
        file.
    '''
    hash_fun = hashlib.md5()
    hash_fun.update(bytes(filename))
    hashstring = hash_fun.hexdigest()
    return os.path.join(hashstring[:2], hashstring[2: 4])


def dump_image(img_url, img_id, img_folder):
    '''
    Download a car image from the Internet and stores it
    on disk.

    Args:
        img_url: URL of the image to download.
        img_id: Will identify this image.
        img_folder: Path to the root image folder where the picture
            will be stored.

    Returns:
        The absolute path to the dumped image.
    '''
    full_img_folder = os.path.join(img_folder,
                                   numeric_folder_structure(img_id))
    full_img_path = os.path.join(full_img_folder,
                                 '{}.jpg'.format(img_id))
    if os.path.isfile(full_img_path):
        # The image is already stored on disk, don't waste time with it.
        return full_img_path
    if not os.path.isdir(full_img_folder):
        # Create the image folder, if it does not exist.
        os.makedirs(full_img_folder)
    pil_image = Image.open(StringIO(urllib2.urlopen(img_url).read()))
    pil_image.save(full_img_path, 'JPEG')
    return full_img_path


def crawl_car_info(car_item, status, img_folder):
    '''
    Crawls the information relative to a single car and returns it.

    Args:
        car_item: A BeautifulSoup object representing the list item
            relative to a car.
        status: CrawlerStatus object to update.
            See src.second_hand_cars.crawler_status.CrawlerStatus.
        img_folder: Path to the root image folder where the picture
            will be stored.

    Returns:
        A dict with the information relative to the current car; None
        if duownloaded information are not valid.
    '''
    item_class = car_item.get('class', None)
    if item_class is None:
        # This tag does not contain a "class" field. Not interesting.
        return None
    item_class_string = '_'.join(item_class)
    if item_class_string not in ['ric-article_clearfix']:
        # Not the list item we are looking for.
        return None
    car_info_string = car_item.get('data-target', None)
    if car_info_string is None:
        # No basic car info, nothing to do.
        return None
    car_info_list = str(car_info_string).split('/')
    car_id = car_info_list[-2]
    if status.contains(car_id):
        # Car already registered: do not waste time.
        return None
    car_info = {
        'car_id': car_id,
        'car_model': car_info_list[-4],
        'car_type': car_info_list[-5],
    }
    for sub_div in car_item.findAll('div'):
        sub_div_class_list = sub_div.get('class', [])
        if 'ric-offer-image' in sub_div_class_list:
            # This div represents the image.
            car_info['car_img_url'] = str('http:' + sub_div.div['data-image-src'])
        elif 'ric-price-container' in sub_div_class_list:
            # This div represents the price.
            price_string = sub_div.ul.findAll('li')[1].text
            car_info['car_price'] = int(price_string.strip().replace("'", ''))
    try:
        car_img_path = dump_image(img_url=car_info['car_img_url'],
                                  img_id=car_id,
                                  img_folder=img_folder)
    except:
        # Image download did not complete: do not keep this car.
        logging.error('Unable to download image: {}'.format(car_info['car_img_url']))
        return None
    car_info['car_img_path'] = car_img_path
    return car_info


def crawl_page(page_url, status, img_folder, save_every):
    '''
    Crawls a web page and updates the crawler status with the car
    information collected from the current page.

    Args:
        page_url: URL of the page to crawl.
        status: CrawlerStatus object to update.
            See src.second_hand_cars.crawler_status.CrawlerStatus.
        img_folder: Path to the root folder where images will be stored.
        save_every: How many new collected cars between two status security
            saves.
    '''
    html_page = urllib2.urlopen(page_url).read()
    soup = BeautifulSoup(html_page, 'html.parser')
    for car_item in soup.find_all('li'):
        # Each page contains a list of cars.
        try:
            car_info = crawl_car_info(car_item, status, img_folder)
        except:
            # Failed to crawl this car, go to next one.
            continue
        if car_info is None:
            # Invalid information for this car, go to next one.
            continue
        status.add(car_info)
        if status.size % save_every == 0:
            status.save()


def main():
    '''
    Runs this script.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('output_folder',
                        type=str,
                        help='Path to the root folder where data will be stored.')
    parser.add_argument('--num',
                        dest='num_cars',
                        type=int,
                        required=True,
                        help='Amount of cars to crawl.')
    parser.add_argument('--from-cheapest',
                        action='store_true',
                        required=True,
                        help='If set, crawls the cars starting from the cheapest one, otherwise from the most expensive one.')
    parser.add_argument('--save-every',
                        type=int,
                        default=100,
                        help='Interval between two security saves.')
    parser.add_argument('--max-pages',
                        type=int,
                        default=10000,
                        help='Sets the maximum number of pages to crawl. Avoids infinity loops.')
    args = parser.parse_args([
        '/home/tom/second_hand_cars_data',
        '--num', '1000',
        '--from-cheapest',
        '--save-every', '200',
        '--max-pages', '1000',
        ])

    img_folder = os.path.join(args.output_folder, 'imgs')
    sort_value = from_most_expensive_code
    if args.from_cheapest:
        sort_value = from_most_expensive_code
    with CrawlerStatus(status_folder=args.output_folder) as status:
        for page_id in tqdm(range(args.max_pages)):
            page_url = base_url.format(page_id, sort_value)
            try:
                crawl_page(page_url, status, img_folder, args.save_every)
            except:
                # Could not complete to crawl this page, go to next one.
                logging.error('Unable to crawl page: {}'.format(page_url))
                continue
            if status.size >= args.num_cars:
                # Collected enough cars: quit crawling.
                break


if __name__ == '__main__':
    logging.basicConfig()
    main()

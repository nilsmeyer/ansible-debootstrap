#!/usr/bin/env python3


def filter_2sectors(size, metric_prefix=None, sector_size_b=512):
    '''
    Convertion disk size with metric prefixes to size in sectors
    "size" - disk size with or without metric prefix
    "metric_prefix" - metric prefix, default "None"
    "sector_size_b" - logical sector size, default "512B"
    '''

    if metric_prefix:
        _size = size.upper() + metric_prefix
    else:
        _size = size.upper()

    if 'B' in _size:
        return int(_size.split('B')[0]) / sector_size_b
    elif 'K' in _size:
        return int(_size.split('K')[0]) * 1024 / sector_size_b
    elif 'M' in _size:
        return int(_size.split('M')[0]) * 1024**2 / sector_size_b
    elif 'G' in _size:
        return int(_size.split('G')[0]) * 1024**3 / sector_size_b
    elif 'P' in _size:
        return int(_size.split('G')[0]) * 1024**4 / sector_size_b
    else:
        return int(_size)


class FilterModule(object):
    '''
    Ansible filters
    '''
    def filters(self):
        return {
            # jinja2 overrides
            'f_2sectors': filter_2sectors
        }

if __name__ == '__main__':
    from pprint import pprint

    _list = ['128M', '2M', '256M', '3G']
    [print(filter_2sectors(item)) for item in _list]

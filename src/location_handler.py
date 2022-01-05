# -*- coding: utf-8 -*-
"""
Created on Fri Aug  6 14:56:52 2021

@author: krose
"""

from os import path
from os import getcwd
import src.date_handler as dh


class NoLocationsFileException(Exception):
    pass


class NoLocationsException(Exception):
    pass


class NoDateSetException(Exception):
    pass


class LocationHandler:

    def __init__(self, locations='preferences/locations.txt', locations_type=None):
        """
        __init__ - handles parsing the locations file
        :param locations: path to the file containing locations and entry points
        :param locations_type: type of locations, camping or permits
        """
        self.locations = dict()
        self.locations_type = locations_type

        locations_path = path.join(getcwd(), locations)
        if not path.exists(locations_path):
            raise NoLocationsFileException("Locations File does not exist @: " + locations_path)

        location_data = list()
        details_data = list()
        detail_input = False

        with open(locations_path, "r") as locations_file:
            for line in locations_file:
                if "detail" in line.strip().lower():
                    detail_input = True
                elif detail_input:
                    details_data.append(line.strip())
                elif "#" not in line.strip().lower() and line.strip() != "" and "location" not in line.lower():
                    location_data.append(line.strip())

        if len(location_data) == 0:
            raise NoLocationsException("Locations File does not contain any locations")

        self.details = dict() if detail_input else None

        if "camp" in self.locations_type:
            for location in location_data:
                split_line = location.split("-")
                park, campground, sites = "", "", -1
                if len(split_line) == 2:
                    campground = split_line[0].strip()
                    sites = [int(site.strip()) for site in split_line[1].split(",") if site.strip() != ""]
                else:
                    park = split_line[0].strip()
                    campground = split_line[1].strip()
                    sites = [int(site.strip()) for site in split_line[2].split(",") if site.strip() != ""]

                self.locations[park + ":" + campground] = sites

        elif "permit" in self.locations_type:
            for entry in location_data:
                location = entry.split("-")[0].strip()
                entry_points = [entry_point.strip() for entry_point in entry.split("-")[1].strip().split(",")
                                if entry_point.strip() != ""]
                self.locations[location] = entry_points

        for detail in details_data:
            detail_type = detail.split("-")[0].strip()
            self.details[detail_type] = [detail_field.strip() for detail_field in
                                         detail.split("-")[1].strip().split(",") if detail_field.strip() != ""]

        if 'dates' in self.details:
            try:
                start_date = dh.DateHandler(self.details['dates'][0]).date
                end_date = None
                if "camp" in locations_type and len(self.details['dates']) <= 1:
                    raise Exception()
                elif "permit" not in locations_type and len(self.details['dates']) == 2:
                    end_date = dh.DateHandler(self.details['dates'][1]).date

                self.details['dates'] = [start_date, end_date]

            except Exception as e:
                self.details['dates'] = None
                print("Malformed date provided, ignoring, will use Next Available")

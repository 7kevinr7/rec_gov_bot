# -*- coding: utf-8 -*-
"""
Created on Fri Aug  6 14:56:52 2021

@author: krose
"""

from os import path
from os import getcwd
from sys import exit
from datetime import time, datetime

import src.location_handler as lh
import src.credential_handler as ch


class NoTimeOrRefreshCountProvidedException(Exception):
    pass


class PreferencesHandler:

    def __init__(self, prefs='preferences/preferences.txt'):
        """
        __init__ - constructor that handles parsing the preferences file
        :param prefs: path to the preferences files
        """
        preferences = dict()

        prefs_path = path.join(getcwd(), prefs)
        if path.exists(prefs_path):
            with open(prefs_path, "r") as prefs_file:
                for line in prefs_file:
                    # Ignore all lines that are commented out
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    pref_pair = line.strip().split(",")
                    preferences[pref_pair[0].strip()] = pref_pair[1].strip()

        # We don't care to execute if there aren't any locations provided
        if 'permit_locations' not in preferences and 'camping_locations' not in preferences:
            print("Please provide permit/camping locations file in " + prefs)
            exit(1)

        # No credentials and no login variable, exit
        # No credentials and login is set to True, exit
        # Otherwise, ignore credentials
        if ('credentials' not in preferences and 'login' not in preferences) or \
                ('login' in preferences and "True" in preferences['login'] and
                 'credentials' not in preferences):
            print("Please provide credentials file in " + prefs)
            exit(1)

        self.camping_details = None
        self.camping_locations = None
        if 'camping_locations' in preferences:
            location_handler = lh.LocationHandler(preferences['camping_locations'], "camping")
            self.camping_locations = location_handler.locations
            self.camping_details = location_handler.details

        self.permit_details = None
        self.permit_locations = None
        if 'permit_locations' in preferences:
            location_handler = lh.LocationHandler(preferences['permit_locations'], "permits")
            self.permit_locations = location_handler.locations
            self.permit_details = location_handler.details

        self.credentials = None
        if 'credentials' in preferences:
            _credential_handler = ch.CredentialHandler(preferences['credentials'])
            self.credentials = (_credential_handler.credentials[0], _credential_handler.credentials[1])

        self.wait_duration = int(preferences['wait_duration']) if 'wait_duration' in preferences else 1
        self.long_delay = int(preferences['long_delay']) if 'long_delay' in preferences else 5
        self.guests = int(preferences['guests']) if 'guests' in preferences else 2
        self.login = bool(preferences['login']) if 'login' in preferences and "True" in preferences['login'] else False

        self.url = preferences['url'] if 'url' in preferences else "https://www.recreation.gov/"

        self.time_start = None
        self.time_end = None
        self.num_refreshes = 0

        if 'time_start' in preferences:
            try:
                time_start_string = preferences['time_start']
                time_start, time_end = time_start_string.split("-")
                hours, minutes, seconds = time_start.split(":")
                self.time_start = time(int(hours.strip()), int(minutes.strip()), int(seconds.strip()))
                hours, minutes, seconds = time_end.split(":")
                self.time_end = time(int(hours.strip()), int(minutes.strip()), int(seconds.strip()))
                if datetime.now().time() > self.time_end:
                    raise NoTimeOrRefreshCountProvidedException("Invalid time, end time is before current time")

                print("Processing will begin at " + str(self.time_start) + " and end at " + str(self.time_end))

            except NoTimeOrRefreshCountProvidedException as e:
                self.time_start = None
                self.time_end = None
                print(e)
            except Exception as e:
                self.time_start = None
                self.time_end = None
                print("Malformed time provided, ignoring, will use num_refreshes")

        if self.time_start is None:
            if 'num_refreshes' in preferences:
                self.num_refreshes = int(preferences['num_refreshes'])
                print("Processing will execute for " + str(self.num_refreshes) + " iterations")
            else:
                raise NoTimeOrRefreshCountProvidedException(
                    "Please provide a time to start or refresh count in " + prefs)

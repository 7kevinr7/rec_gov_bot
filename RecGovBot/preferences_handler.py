# -*- coding: utf-8 -*-
"""
Created on Fri Aug  6 14:56:52 2021

@author: krose
"""

from os import path
from os import getcwd
from sys import exit

import RecGovBot.location_handler as lh
import RecGovBot.credential_handler as ch


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
                    if "#" not in line.strip() and line.strip != "":
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
        self.num_refreshes = int(preferences['num_refreshes']) if 'num_refreshes' in preferences else 1

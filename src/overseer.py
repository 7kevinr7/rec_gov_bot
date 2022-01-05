# -*- coding: utf-8 -*-
"""
Created on Fri Aug  6 14:56:52 2021

@author: krose
"""

import multiprocessing as mp
from traceback import print_exc
from selenium import webdriver
from os import path
from os import getcwd

from src.recgov import RecGov
from src.camp_recgov import CampRecGov
from src.permit_recgov import PermitRecGov
import src.preferences_handler as ph


class Overseer:

    def __init__(self, prefs='preferences/preferences.txt'):
        """
        __init__ - basic constructor
        :param prefs: the preference file to be used
        """
        self.preferences = ph.PreferencesHandler(prefs)

    @staticmethod
    def merge_parameters(locations, rec_type):
        return [[location, rec_type] for location in locations]

    def start_driver(self, merged_location_type):
        """
        start_driver - creates the chrome driver and starts the browser
        :param merged_location_type: list containing location and rec_type for this driver
        :return: None
        """
        driver = None
        try:
            location_type_str = ""
            if "camp" in merged_location_type[1].lower():
                location_type_str = "<Camping> "
            elif "permit" in merged_location_type[1].lower():
                location_type_str = "<Permits> "

            print(location_type_str + RecGov.format_location_string(merged_location_type[0]) + ": driver starting")
            exec_path = path.join(getcwd(), 'chromedriver')
            driver = webdriver.Chrome(executable_path=exec_path,
                                      chrome_options=webdriver.ChromeOptions())
            driver.maximize_window()
            driver.implicitly_wait(self.preferences.wait_duration)

        except Exception as e:
            print(print_exc())
            print(RecGov.format_location_string(merged_location_type[0]) + ": Unable to create driver for location: ")
            driver = None

        if driver is not None:
            rcgv = None
            if "camp" in merged_location_type[1].lower():
                rcgv = CampRecGov(driver=driver, preferences=self.preferences,
                                  camping_location=merged_location_type[0])
            elif "permit" in merged_location_type[1].lower():
                rcgv = PermitRecGov(driver=driver, preferences=self.preferences,
                                    permit_location=merged_location_type[0])
            else:
                print("Invalid Rec Type provided")
                return

            if rcgv is None or not rcgv.execute():
                driver.quit()

    def start(self):
        """
        start - creates a separate process for each driver
        :return: None
        """
        num_processes = (len(self.preferences.camping_locations.keys())
                         if self.preferences.camping_locations is not None else 0)
        num_processes += (len(self.preferences.permit_locations.keys())
                          if self.preferences.permit_locations is not None else 0)

        process_pool = mp.Pool(processes=num_processes)

        merged_list = list()
        if self.preferences.camping_locations is not None:
            merged_list.extend(Overseer.merge_parameters(
                self.preferences.camping_locations.keys(), "Camping"))
        if self.preferences.permit_locations is not None:
            merged_list.extend(Overseer.merge_parameters(
                self.preferences.permit_locations.keys(), "Permits"))

        process_pool.map(self.start_driver, merged_list)


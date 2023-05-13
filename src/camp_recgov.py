"""
This module provides the flow for campsite reservations.
"""

from traceback import print_exc
from time import sleep
from re import sub
from datetime import datetime, date, time
from datetime import timedelta
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from src.recgov import RecGov
from src.date_handler import DateHandler


class EndOfTriesException(Exception):
    pass


class CampRecGov(RecGov):
    """ This class provides the functionality for campsite reservations. """

    def __init__(self, driver, preferences, camping_location):
        """
        __init__ - constructor
        :param driver: the chrome driver for this object
        :param preferences: the preferences to be used during execution
        :param camping_location: string location for this browser
        """
        super(CampRecGov, self).__init__(driver, preferences, camping_location)
        self._camping_details = preferences.camping_details

    def execute(self):
        """
        execute - starts the execution of the browser
        :return: bool: True if successfully in checkout, False otherwise
        """
        try:
            super(CampRecGov, self).navigate_site()
            super(CampRecGov, self).log_into_account()
            self._navigate_camping_heading()
            self._load_camping_link()
            self._handle_campground_page()
            self._scheduling_details()
            self._poll()
            # unreachable unless successfully booking
            # detaches browser on successful selection of campsite
            return True
        except EndOfTriesException as e:
            print(e)
        except Exception:
            print(print_exc())

        return False

    def _poll(self):
        """
        _poll - polls the availability page
        :return: None
        """
        retries = 0

        start_datetime, end_datetime, start_date, end_date, campsite = self._select_campsite()
        super(CampRecGov, self).wait()
        result = 0

        if self._time_end:
            current_time = datetime.now().time()
            while current_time < self._time_end:
                self._refresh_availability_table()
                if result == 2:
                    start_datetime, end_datetime, start_date, end_date, campsite = \
                        self._select_campsite()
                result = self._handle_availability(start_datetime, end_datetime,
                                                   start_date, end_date, campsite,
                                                   retries + 1)
                if result == 1:
                    return True
                retries += 1
                current_time = datetime.now().time()
        else:
            while retries < self._num_refreshes:
                self._refresh_availability_table()
                if result == 2:
                    start_datetime, end_datetime, start_date, end_date, campsite = \
                        self._select_campsite()
                result = self._handle_availability(start_datetime, end_datetime,
                                                   start_date, end_date, campsite,
                                                   retries + 1)
                if result == 1:
                    return True
                retries += 1

        except_str = RecGov.format_location_string(self._location) \
                     + ": driver stopping, tried " + \
                     str(retries) + " times"
        if self._time_end:
            except_str += ", reached timeout " + str(self._time_end)

        # Unable to successfully book permits
        raise EndOfTriesException(except_str)

    def _navigate_camping_heading(self):
        """
        _navigate_camping_heading - finds the camping link on the main page
        :return: None
        """
        super(CampRecGov, self).navigate_main_page("Camping & Lodging")

    def _load_camping_link(self):
        """
        _get_camping_link - grabs the necessary link from the search page
        :return: None
        """
        try:
            search_bar = self._driver.find_element_by_xpath(
                "//input[contains(@placeholder, 'Where to')]"
            )
            search_bar.send_keys(self._location.split(":")[1])
            search_bar.send_keys(Keys.RETURN)
            super(CampRecGov, self).navigate_location_link(
                self._location.split(":")[1],
                "/camping/campgrounds/"
            )

        except Exception as e:
            print(RecGov.format_location_string(self._location)
                  + ": CampRecGov._load_camping_link() failed")
            print(print_exc())
            raise e

    def _handle_campground_page(self):
        """
        _handle_campground_page - handles some nuances of the campground pages
        :return: None
        """
        try:
            # Close the dialog that appears if it appears
            WebDriverWait(self._driver, self._wait_duration).until(ec.element_to_be_clickable(
                (By.XPATH, "//button[@aria-label='Close modal']"))).click()

        except Exception:
            print(print_exc())

        try:
            # Scroll down to the table
            table_section = self._driver.find_element_by_class_name("rec-slider-container")
            self._driver.execute_script("arguments[0].scrollIntoView();", table_section)
            sleep(self._wait_duration)

        except Exception as e:
            print(RecGov.format_location_string(self._location)
                  + ": CampRecGov._handle_campground_page() failed")
            print(print_exc())
            raise e

    def _dropdown_menu_handler(self, element_type_id, parameters=""):
        """
        _dropdown_menu_handler - generic handler to cover the campsite detail selection
        :param element_type_id: the dropdown id to search for
        :param parameters: the parameter string to use for selection
        :return: None
        """
        type_elements = self._driver.find_elements_by_id(element_type_id)
        if len(type_elements) > 0:
            type_elements[0].click()

            menu_element = type_elements[0].find_element_by_xpath("..")
            for option in menu_element.find_elements_by_class_name("filter-menu-checkbox-item"):
                if option.text.split()[0].lower().rstrip() in parameters.lower():
                    checkbox = option.find_element_by_tag_name("input")
                    checkbox.click()

            apply_button = menu_element.find_element_by_xpath("//span[contains(text(), 'Apply')]")
            apply_button = RecGov.find_parent_with_tag(apply_button, "button")
            apply_button.click()

    def _campsite_type(self):
        """
        _campsite_type - handles the dropdown campsite type menu
        :param campsite_type: campsite type
        :return: None
        """
        campsite_type = 'standard'
        if 'site_type' in self._camping_details:
            campsite_type = ", ".join(self._camping_details['site_type'])

        self._dropdown_menu_handler("filter-menu-site-types", campsite_type)

    def _allowed_equipment(self):
        """
        _allowed_equipment - handles the campsite equipment selection
        :param equipment_type: campsite equipment type
        :return: None
        """
        equipment_type = 'tent'

        if 'allowed_equipment' in self._camping_details:
            equipment_type = ", ".join(self._camping_details['allowed_equipment'])

        self._dropdown_menu_handler("filter-menu-equipment", equipment_type)

    def _select_dates(self):
        """
        _select_dates - selects the desired dates
        :return: None
        """

        if self._camping_details['dates'] is not None:
            super(CampRecGov, self).select_date(
                self._camping_details['dates'][0],
                "campground-start-date-calendar"
            )
            super(CampRecGov, self).select_date(
                self._camping_details['dates'][1],
                "campground-end-date-calendar"
            )

    def _scheduling_details(self):
        """
        _scheduling_details - handles the scheduling details on the availability page
        :return: None
        """
        try:
            if len(self._camping_details['site_type']) > 0:
                self._campsite_type()
            if len(self._camping_details['allowed_equipment']) > 0:
                self._allowed_equipment()
            self._select_dates()

        except Exception as e:
            print(RecGov.format_location_string(self._location)
                  + ": CampRecGov._scheduling_details() failed")
            print(print_exc())
            raise e

    def _refresh_availability_table(self):
        """
        _refresh_availability_table - refresh the availability grid on the campground page
        :return: None
        """
        try:
            refresh_button = self._driver.find_element_by_xpath(
                "//span[contains(text(), 'Refresh Table')]"
            )
            refresh_button = RecGov.find_parent_with_tag(refresh_button, "button")
            refresh_button.click()

        except Exception as e:
            print(RecGov.format_location_string(self._location)
                  + ": CampRecGov._refresh_availability_table() failed")
            print(print_exc())
            raise e

    def _book_now(self, campsite, book_dates, iteration):
        """
        _book_now - handles the Book Now selection
        :param campsite: the campsite that is currently being booked
        :param book_dates: the dates that are being booked
        :param iteration: the current refresh try
        :return: True if successfully in checkout, else False
        """
        try:
            output_str = "#" + str(iteration) + ": " \
                         + RecGov.format_location_string(self._location) \
                         + ": Able to book: Site #" + str(campsite).zfill(3) \
                         + " for: " + book_dates \
                         + ", you must log in to proceed"

            if super(CampRecGov, self).book_now("//span[contains(text(), 'Add to Cart')]"):
                return super(CampRecGov, self).finish_book_now(output_str,
                                                               RecGov.format_location_string(self._location))

        except Exception as e:
            print(RecGov.format_location_string(self._location)
                  + ": CampRecGov._book_now() failed")
            print(print_exc())
            raise e

        # Any issues, etc. continue polling the availability page
        return False

    def _clear_selection(self):
        """
        _clear_selection - clears the selection on the table
        :return: None
        """
        clear_selection_elements = self._driver.find_elements_by_xpath("//span[contains(text(), "
                                                                       "'Clear selection')]")
        if len(clear_selection_elements) > 0:
            clear_selection = RecGov.find_parent_with_tag(clear_selection_elements[0], "button")
            clear_selection.click()

    def _handle_availability(self, start_datetime, end_datetime, start_date, end_date, campsite, iteration):
        try:
            self._clear_selection()
            available_date_elements = self._driver.find_elements_by_class_name("available")
            if len(available_date_elements) > 0:
                available_date_buttons = list()
                for index in range(len(available_date_elements)):
                    available_date_buttons.append(
                        available_date_elements[index].find_element_by_class_name("rec-availability-date"))

                if len(available_date_buttons) > 0:
                    start_date_button = available_date_buttons[0]
                    end_date_button = available_date_buttons[0]

                    for index in range(len(available_date_buttons)):
                        if available_date_buttons[index].get_attribute("aria-label") is not None:
                            aria_label = available_date_buttons[index].get_attribute("aria-label").lower()
                            if start_date in aria_label:
                                start_date_button = available_date_buttons[index]
                            elif end_date in aria_label:
                                end_date_button = available_date_buttons[index]
                                break

                    if start_date_button != end_date_button:
                        ActionChains(self._driver).move_to_element(start_date_button).click(
                            start_date_button).perform()
                        ActionChains(self._driver).move_to_element(end_date_button).click(
                            end_date_button).perform()

                        # verify that the correct dates are selected
                        start_date_verification = self._driver.find_elements_by_class_name("start")
                        end_date_verification = self._driver.find_elements_by_class_name("end")
                        if len(start_date_verification) == 0 or len(end_date_verification) == 0:
                            return 1

                        start_date_verification = start_date_verification[0]
                        end_date_verification = end_date_verification[0]
                        start_date_verification_button = start_date_verification.find_elements_by_class_name(
                            "rec-availability-date")
                        end_date_verification_button = end_date_verification.find_elements_by_class_name(
                            "rec-availability-date")
                        if len(start_date_verification_button) == 0 or len(end_date_verification_button) == 0:
                            return 1

                        start_date_verification_button = start_date_verification_button[0]
                        end_date_verification_button = end_date_verification_button[0]
                        start_valid = False
                        end_valid = False

                        if start_date_verification_button.get_attribute("aria-label") is not None and \
                                start_date in start_date_verification_button.get_attribute("aria-label").lower():
                            start_valid = True

                        if end_date_verification_button.get_attribute("aria-label") is not None and \
                                end_date in end_date_verification_button.get_attribute("aria-label").lower():
                            end_valid = True

                        if start_valid and end_valid:
                            dates = DateHandler.datetime_to_normal_text(start_datetime) + "-" + \
                                    DateHandler.datetime_to_normal_text(end_datetime)

                            return 1 if self._book_now(campsite, dates, iteration) else 0

        except Exception as e:
            print(RecGov.format_location_string(self._location) + ": CampRecGov._handle_availability() failed")
            print(print_exc())
            return 2

    def _select_campsite(self):
        """
        _select_campsite - inputs the given site number into the search bar
        :return: None
        """
        try:
            site_search_elements = self._driver.find_elements_by_id("campsite-filter-search")

            if len(site_search_elements) > 0:
                site_search_element = site_search_elements[0]

                start_datetime = self._camping_details['dates'][0]
                end_datetime = self._camping_details['dates'][1]
                start_date = DateHandler.datetime_to_short_text(start_datetime).lower()
                end_date = DateHandler.datetime_to_short_text(end_datetime).lower()
                campsite = self._location.split(":")[2]

                site_search_element.send_keys(Keys.CONTROL + 'a')
                site_search_element.send_keys(campsite)

                return start_datetime, end_datetime, start_date, end_date, campsite

        except Exception as e:
            print(RecGov.format_location_string(self._location) + ": CampRecGov._select_campsite() failed")
            print(print_exc())
            raise e

        return False

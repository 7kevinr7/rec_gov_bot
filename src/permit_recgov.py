# -*- coding: utf-8 -*-
"""
Created on Fri Aug  6 14:56:52 2021

@author: krose
"""

from traceback import print_exc
from time import sleep
from re import sub
from datetime import date, datetime, time
from datetime import timedelta
from calendar import monthrange
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


class CommercialTripException(Exception):
    pass


class PermitRecGov(RecGov):

    def __init__(self, driver, preferences, permit_location):
        """
        __init__ - constructor
        :param driver: the chrome driver for this object
        :param preferences: the preferences to be used during execution
        :param permit_location: string location for this browser
        """
        super(PermitRecGov, self).__init__(driver, preferences, permit_location)
        self._permit_details = preferences.permit_details

    def execute(self):
        """
        execute - starts the execution of the browser
        :return: bool: True if successfully in checkout, False otherwise
        """
        try:
            super(PermitRecGov, self).navigate_site()
            super(PermitRecGov, self).log_into_account()
            self._navigate_permit_heading()
            self._load_permit_link()
            self._poll()
            # unreachable unless successfully booking
            # detaches browser on successful selection of permits
            return True
        except EndOfTriesException as e:
            print(e)
        except CommercialTripException as e:
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

        self._driver.refresh()
        self._scheduling_details()
        entry_point = self._select_permit()
        super(PermitRecGov, self).wait()
        result = 0

        if self._time_end:
            current_time = datetime.now().time()
            while current_time < self._time_end:
                self._refresh_availability_table()
                result = self._handle_availability(entry_point, retries + 1)
                if result == 1:
                    return True
                retries += 1
                current_time = datetime.now().time()

                self._driver.refresh()
                self._scheduling_details()
                entry_point = self._select_permit()
        else:
            while retries < self._num_refreshes:
                self._refresh_availability_table()
                result = self._handle_availability(entry_point, retries + 1)
                if result == 1:
                    return True
                retries += 1

                self._driver.refresh()
                self._scheduling_details()
                entry_point = self._select_permit()

        except_str = RecGov.format_location_string(self._location) + ": driver stopping, tried " + \
                     str(retries) + " times"
        if self._time_end:
            except_str += ", reached timeout " + str(self._time_end)

        # Unable to successfully book permits
        raise EndOfTriesException(except_str)

    def _navigate_permit_heading(self):
        """
        _navigate_permit_heading - finds the permit link on the main page
        :return: None
        """
        super(PermitRecGov, self).navigate_main_page("Permits")

    def _load_permit_link(self):
        """
        _get_permit_link - grabs the necessary link from the search page
        :return: None
        """
        super(PermitRecGov, self).navigate_location_link(self._location.split(":")[0], "/permits/",
                                                         "/registration/detailed-availability")

    def _permit_type(self):
        """
        _permit_type - handles the dropdown permit type menu
        :param exiting_whitney: overnight permit type
        :return: None
        """
        permit_type = "overnight"
        if 'permit_type' in self._permit_details:
            permit_type = ", ".join(self._permit_details['permit_type']).lower()

        permit_type_element = self._driver.find_elements_by_id("permit-type")

        if len(permit_type_element) > 0:
            # Find the correct option and click it
            for option in permit_type_element[0].find_elements_by_tag_name("option"):
                # These are called out for a reason to get this selection to work properly
                if "mt whitney" in permit_type and option.text.lower().strip() != "overnight" and \
                        option.text.lower().strip() in permit_type:
                    option.click()
                    break
                elif "mt whitney" not in permit_type and option.text.lower().strip() in permit_type:
                    option.click()
                    break

    def _commercial_trip(self):
        """
        _commercial_trip - handles the commercial trip radio selection
        :return: None
        """
        commercial_trip_type = ", ".join(self._permit_details['commercial_trip']).lower()
        commercial_trip_id = "prompt-answer-no1"

        if 'commercial_trip' in self._permit_details:
            if "yes" in commercial_trip_type:
                commercial_trip_id = "prompt-answer-yes1"

        commercial_trip = self._driver.find_elements_by_id(commercial_trip_id)

        if len(commercial_trip) > 0:
            # Only click if the option is actually present
            commercial_trip[0].click()

            if "yes" in commercial_trip_type:
                sleep(self._wait_duration)
                raise CommercialTripException(RecGov.format_location_string(self._location) + ": You have selected a commercial trip")

    def _add_group_member(self, path):
        """
        _add_group_member - adds the correct number of guests to the reservation
        :param path: the path to the button, changes based on the page
        :return: None
        """
        add_group_member = self._driver.find_elements_by_xpath(path)

        if len(add_group_member) > 0:
            # Click the button to add the correct number of guests
            # Unable to send the value to the selection field as the field will reject the value
            for i in range(self._guests):
                add_group_member[0].click()

    def _select_dates(self):
        """
        _select_dates - selects the desired dates or Next Available based on preferences
        :return: None
        """
        if self._permit_details['dates'] is not None:
            super(PermitRecGov, self).select_date(self._permit_details['dates'][0], "SingleDatePicker1")
            self._driver.find_element_by_id("SingleDatePicker1").send_keys(Keys.TAB)
            return

        # No dates provided, use the next available
        sleep(self._wait_duration)
        super(PermitRecGov, self).next_available()

        # Grab this next available date from the calendar
        date_input = self._driver.find_element_by_id("SingleDatePicker1")
        next_avail_dates = date_input.get_attribute("value")

        if next_avail_dates is None:
            raise ValueError("Unable to parse date from next available")

        # Update the dates for this reservation with the next available
        next_avail_dates = next_avail_dates.split("/")
        if len(next_avail_dates) == 3:
            self._permit_details['dates'] = [date(int(next_avail_dates[2]), int(next_avail_dates[0]),
                                                  int(next_avail_dates[1])), None]

    def _scheduling_details(self):
        """
        _scheduling_details - handles the scheduling details on the availability page
        :return: None
        """
        try:
            self._permit_type()
            self._commercial_trip()
            # Attempt to add group members using the two different page layouts
            self._add_group_member("//button[@aria-label='Add guests']")
            self._add_group_member("//button[@aria-label='Add group members']")
            self._select_dates()

        except CommercialTripException as e:
            raise e

        except Exception as e:
            print(RecGov.format_location_string(self._location) + ": PermitRecGov._scheduling_details() failed")
            print(print_exc())
            raise e

    def _refresh_availability_table(self):
        """
        _refresh_availability_table - refresh the availability grid on the permits page
        :return: None
        """
        try:
            pass
            """
            refresh_button = self._driver.find_element_by_xpath("//span[contains(text(), 'Refresh Table')]")
            refresh_button = RecGov.find_parent_with_tag(refresh_button, "button")
            refresh_button.click()
            """

        except Exception as e:
            print(RecGov.format_location_string(self._location) + ": PermitRecGov._refresh_availability_table() failed")
            print(print_exc())
            raise e

    def _book_now(self, entry_point, book_date, iteration):
        """
        _book_now - handles the Book Now selection
        :param entry_point: the entry point selected
        :param book_date: the date selected
        :return: True if successfully in checkout, else False
        """
        try:
            output_str = "#" + str(iteration) + ": " + RecGov.format_location_string(self._location) + \
                         ": Able to book: " + entry_point + " for: " + book_date + ", you must log in to proceed"
            
            if super(PermitRecGov, self).book_now("//span[contains(text(), 'Book Now')]"):
                return super(PermitRecGov, self).finish_book_now(output_str, RecGov.format_location_string(self._location))

        except Exception as e:
            print(RecGov.format_location_string(self._location) + ": PermitRecGov._book_now() failed")
            print(print_exc())
            raise e

        # Any issues, etc. continue polling the availability page
        return False

    def _clear_selection(self):
        """
        _clear_selection - clears the selection on the table
        :return: None
        """
        clear_selection_elements = self._driver.find_elements_by_xpath("//span[contains(text(), 'Clear Dates')]")
        if len(clear_selection_elements) > 0:
            clear_selection = RecGov.find_parent_with_tag(clear_selection_elements[0], "button")
            clear_selection.click()

    def _handle_availability(self, entry_point, iteration):
        try:
            self._clear_selection()
    
            # Grab the container for the page
            grid_cell_available = self._driver.find_elements_by_class_name('rec-grid-grid-cell.available')

            for index in range(0, len(grid_cell_available)):
                available_date_button = grid_cell_available[0].find_elements_by_tag_name("button")
                if len(available_date_button) == 0:
                    return 0

                available_date_button = available_date_button[0]
                day_date = 0
                permits_available = 0

                if "whitney" in self._location.split(":")[0].lower():
                    permits_available = int(sub("[^0-9]", "", str(available_date_button.text)))
                    day_date = self._permit_details['dates'][0].day
                    row_text = RecGov.find_parent_with_attribute_value(available_date_button, "class", "rec-grid-row").text

                    if entry_point not in row_text:
                        return 0
                else:
                    day_date, permits_available = available_date_button.get_attribute("aria-label").split("\n")

                    day_date = int(sub("[^0-9]", "", str(day_date)))
                    permits_available = int(sub("[^0-9]", "", str(permits_available.split("out of")[0])))

                book_date = self._permit_details['dates'][0]

                if permits_available < self._guests or book_date.day != day_date:
                    return 0

                ActionChains(self._driver).move_to_element(available_date_button).click(
                    available_date_button).perform()

                book_date_str = DateHandler.datetime_to_normal_text(book_date)

                # When this becomes True, we are at the checkout screen
                # Signal to the polling function to exit, but keep the browser open
                return 1 if self._book_now(entry_point, book_date_str, iteration) else 0

        except Exception as e:
            print(RecGov.format_location_string(self._location) + ": CampRecGov._handle_availability() failed")
            print(print_exc())
            return 0

    def _select_permit(self):
        """
        _select_permit - inputs the entry point info
        :return: None
        """
        try:
            filter_button = self._driver.find_element_by_xpath("//span[contains(text(), 'Filters')]")
            filter_button = RecGov.find_parent_with_tag(filter_button, "button")
            filter_button.click()

            entry_point_input = self._driver.find_element_by_id("division-search-input")
            entry_point_input.send_keys(self._location.split(":")[1])
            entry_point_input.send_keys(Keys.RETURN)
            sleep(self._wait_duration)

            return self._location.split(":")[1]

        except Exception as e:
            print(RecGov.format_location_string(self._location) + ": PermitRecGov._select_permit() failed")
            print(print_exc())
            raise e

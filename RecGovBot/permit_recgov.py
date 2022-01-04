# -*- coding: utf-8 -*-
"""
Created on Fri Aug  6 14:56:52 2021

@author: krose
"""

from traceback import print_exc
from time import sleep
from re import sub
from datetime import date
from datetime import timedelta
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from RecGovBot.recgov import RecGov
from RecGovBot.date_handler import DateHandler


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
        self._desired_entries = preferences.permit_locations[permit_location]
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
            print(e + ", exiting")
        except Exception:
            print(print_exc())

        return False

    def _poll(self):
        """
        _poll - polls the availability page
        :return: None
        """
        retries = 0
        while retries < self._num_refreshes:
            # for each refresh:
            # - refresh the webpage, reschedule permit details and restart checking for availabilities
            self._driver.refresh()
            self._scheduling_details()
            if self._select_permit(retries + 1):
                return True
            retries += 1

        # Unable to successfully book permits
        raise EndOfTriesException("<Permits> " + self._location + ": driver stopping")

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
        super(PermitRecGov, self).navigate_location_link(self._location, "/permits/",
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
                raise CommercialTripException(self._location + ": You have selected a commercial trip")

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
            print(self._location + ": PermitRecGov._scheduling_details() failed")
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
            output_str = "#" + str(iteration) + ": " + self._location + ": Able to book: " + entry_point[0] + \
                         ", " + entry_point[1] + " for: " + book_date + ", you must log in to proceed"
            
            if super(PermitRecGov, self).book_now("//span[contains(text(), 'Book Now')]"):
                return super(PermitRecGov, self).finish_book_now(output_str, self._location)

        except Exception as e:
            print(self._location + ": PermitRecGov._book_now() failed")
            print(print_exc())

        # Any issues, etc. continue polling the availability page
        return False

    def _select_permit(self, iteration=1):
        """
        _select_permit - parses the availabilities page to find the first desired permit and selects it
        :return: True if successfully reached the checkout screen, False otherwise
        """
        try:
            scroll_element_to_middle = "var viewPortHeight = Math.max(document.documentElement.clientHeight, " + \
                                       "window.innerHeight || 0);" + "var elementTop = arguments[0]." + \
                                       "getBoundingClientRect().top; window.scrollBy(0, " + \
                                       "elementTop-(viewPortHeight/2));";

            # Set the correct table class name based on page
            table_string = "per-availability-table-container"
            if "whitney" in self._location.lower():
                table_string = "per-availability-content"

            # Grab the container for the page
            container = self._driver.find_element_by_class_name(table_string)
            grid_rows = container.find_elements_by_xpath(
                ".//div[(@data-component='Row') and (@role='row') and (@class='rec-grid-row')]")

            # Iterate over the grid rows to find the correct and available entry points
            for row in range(2, len(grid_rows)):
                cell_elements = grid_rows[row].find_elements_by_xpath(
                    ".//div[(@data-component='GridCell') and (@role='gridcell')]")
                # Skip empty rows
                if len(cell_elements) < 3:
                    continue
                entry_point_info = [cell_elements[0].text.strip(), cell_elements[1].text.strip(),
                                    cell_elements[2].text.strip()]
                # Find where the first available day is for this entry point
                first_available_index = -1
                for cell_index in range(3, len(cell_elements)):
                    if int(sub("[^0-9]", "", cell_elements[cell_index].text) if
                           cell_elements[cell_index].text.strip() != "" else 0) >= self._guests:
                        first_available_index = cell_index
                        break
                # Check if this entry point is in our list and if it is actually available
                if (self._desired_entries is not None and (entry_point_info[0] not in self._desired_entries) and
                        (entry_point_info[1] not in self._desired_entries)) or first_available_index == -1:
                    continue

                available_date_button = cell_elements[first_available_index].find_elements_by_tag_name("button")
                if len(available_date_button) == 0:
                    continue

                # Click the first available date button that is on our desired date
                WebDriverWait(self._driver, self._long_delay).until(ec.visibility_of_all_elements_located(
                    (By.CLASS_NAME, "sarsa-button.rec-availability-date.sarsa-button-primary.sarsa-button-md")))

                self._driver.execute_script(scroll_element_to_middle, available_date_button[0])
                ActionChains(self._driver).click(available_date_button[0]).perform()

                book_date = self._permit_details['dates'][0]
                book_date += timedelta(days=(first_available_index - 3))
                book_date_str = DateHandler.datetime_to_normal_text(book_date)

                # When this becomes True, we are at the checkout screen
                # Signal to the polling function to exit, but keep the browser open
                return self._book_now(entry_point_info, book_date_str, iteration)

        except Exception as e:
            print(self._location + ": PermitRecGov._select_permit() failed")
            print(print_exc())
            raise e

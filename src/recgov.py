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


class EndOfTriesException(Exception):
    pass


class RecGov:

    def __init__(self, driver, preferences, location):
        """
        __init__ - constructor
        :param driver: the chrome driver for this object
        :param preferences: the preferences to be used during execution
        :param location: string location for this browser
        """
        self._driver = driver
        self._location = location
        self._wait_duration = preferences.wait_duration
        self._long_delay = preferences.long_delay
        self._login = preferences.login
        self._credentials = preferences.credentials
        self._url = preferences.url
        self._guests = preferences.guests
        self._num_refreshes = preferences.num_refreshes

    @staticmethod
    def find_parent_with_attribute_value(element, target, value):
        """
        find_parent_with_attribute_value - provides parent traversal to find an attribute set to value
        :param element: the child element of the desired element
        :param target: the attribute to look for
        :param value: the value of the attribute to look for
        :return: WebElement: the parent WebElement of the provided child, None if the element is not found
        """
        try:
            while element.get_attribute(target) is None or element.get_attribute(target).strip() != value:
                element = element.find_element_by_xpath("..")
            return element

        except Exception as e:
            print("RecGov.find_parent_with_attribute_value() failed")
            print(print_exc())

        return None

    @staticmethod
    def find_parent_with_tag(element, target):
        """
        find_parent_with_tag - provides parent traversal to find a tag set to value
        :param element: the child element of the desired element
        :param target: the tag name to look for
        :return: WebElement: the parent WebElement of the provided child, None if the element is not found
        """
        try:
            while element.tag_name.strip() != target:
                element = element.find_element_by_xpath("..")
            return element

        except Exception as e:
            print("RecGov.find_parent_with_tag() failed")
            print(print_exc())

        return None

    @staticmethod
    def format_location_string(location_to_format):
        """
        _format_location_string - handles formatting for the location string, so it looks decent
        :param location_to_format: the location to format
        :return: the formatted string
        """
        location_str = location_to_format
        if ":" in location_str:
            # Camping location
            if location_str.split(":")[0] == "":
                location_str = location_str.replace(":", "")
            else:
                location_str = location_str.replace(":", " - ")

        return location_str

    def execute(self):
        """
        execute - starts the execution of the browser
        :return: bool: True if successfully in checkout, False otherwise
        """
        try:
            self.navigate_site()
            self._log_into_account()
            self._navigate_main_page()
            self._get_permit_link()
            self._poll()
            # unreachable unless successfully booking
            # detaches browser on successful selection of permits
            return True
        except Exception as e:
            pass

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
            if self._parse_availabilities(retries + 1):
                return True
            retries += 1

        # Unable to successfully book permits
        raise EndOfTriesException(format_location_string() + ": finished executing")

    def navigate_site(self):
        """
        navigate_site - opens the desired url in the driver
        :return: None
        """
        try:
            self._driver.get(self._url)
        except Exception as e:
            print(format_location_string() + ": RecGov.navigate_site() failed: " + self._url)
            print(print_exc())
            raise e

    def log_into_account(self):
        """
        log_into_account - logs into the account with credentials provided if desired
        :return: None
        """
        try:
            # Only logs in if intended to and has valid credentials
            if not self._login or self._credentials is None:
                return

            # Grab the sign-in button
            WebDriverWait(self._driver, self._long_delay).until(ec.element_to_be_clickable((By.ID,
                "ga-global-nav-log-in-link"))).click()

            # Grab the username / password elements
            username = self._driver.find_element_by_id("email")
            password = self._driver.find_element_by_id("rec-acct-sign-in-password")

            # Send credentials
            username.send_keys(self._credentials[0])
            password.send_keys(self._credentials[1])

            # Grab the submit button
            WebDriverWait(self._driver, self._long_delay).until(ec.element_to_be_clickable((By.XPATH,
                "//button[contains(@class, 'rec-acct-sign-in-btn') and (@type='submit')]"))).click()

            # Wait for login screen to clear
            sleep(self._wait_duration)

        except Exception as e:
            print(format_location_string() + ": RecGov.log_into_account() failed")
            print(print_exc())
            raise e

    def navigate_main_page(self, heading_text):
        """
        navigate_main_page - finds the heading link on the main page
        :return: None
        """
        try:
            # Need to pick out the desired heading from all of the other headings
            headings = self._driver.find_elements_by_xpath("//h3[(@data-component='Heading') and (@class='h3')]")
            heading_element = None
            for heading in headings:
                if heading.text.strip() == heading_text and heading.get_attribute("class").strip() == "h3":
                    heading_element = heading
                    break

            # Find the button corresponding to the parent of the heading
            heading_element = RecGov.find_parent_with_tag(heading_element, "button")
            heading_element.click()

        except Exception as e:
            print(format_location_string() + ": RecGov.navigate_main_page() failed")
            print(print_exc())
            raise e

    def navigate_location_link(self, location, primary_link_text, secondary_link_text=""):
        """
        navigate_location_link - grabs the necessary link from the search page
        :return: None
        """
        try:
            # Search the page to find the link for this location
            location_element = self._driver.find_element_by_xpath("//a[contains(@href, '" + primary_link_text + "') "
                                                                  "and contains(@title, '" + location + "')]")
            current_link = location_element.get_attribute("href") + secondary_link_text
            self._driver.get(current_link)

        except Exception as e:
            print(format_location_string() + ": RecGov.navigate_location_link() failed")
            print(print_exc())
            raise e

    def next_available(self):
        """
        next_available - selects the next available button on the calendar
        :return: None
        """
        next_avail = self._driver.find_element_by_xpath("//*[contains(text(), 'Next Available')]")
        # Click the Next Available button if it is present
        next_avail = RecGov.find_parent_with_attribute_value(next_avail, "type", "button")
        next_avail.click()

    def select_date(self, desired_date, calendar_element=""):
        """
        select_date - selects the desired date on the element provided
        :param desired_date: the desired date to select
        :param calendar_element: the id of the calendar element to select
        :return: None
        """
        # Update the calendar to use the desired dates
        date_str = "/".join([desired_date.strftime("%m"), desired_date.strftime("%d"),
                             desired_date.strftime("%Y")])

        date_input = self._driver.find_element_by_id(calendar_element)
        # The calendar is finicky: select previous date and overwrite, shift focus elsewhere to force a page update
        date_input.send_keys(Keys.CONTROL + "a")
        date_input.send_keys(date_str)
        date_input.send_keys(Keys.TAB)

    def book_now(self, book_now_xpath):
        """
        book_now - finds and clicks the book now / add to cart button
        :param book_now_xpath: the xpath used to locate the button
        :return:
        """
        # Grab the Book Now button
        book_now_button = self._driver.find_elements_by_xpath(book_now_xpath)

        if len(book_now_button) == 0:
            return False
        # Find the parent button of the Book Now text
        book_now_button = RecGov.find_parent_with_tag(book_now_button[0], "button")
        book_now_button.click()

        return True

    def finish_book_now(self, output_details_to_user, location_str):
        """
        finish_book_now - closes the book now page
        :param output_details_to_user:
        :param location_str:
        :return:
        """
        # Site will prompt a login, since we aren't logged in, this will kick the bot back to the availability
        # screen to continue looking
        if not self._login:
            close_book_now = self._driver.find_elements_by_xpath("//span[contains(text(), 'Close Log In')]")
            if len(close_book_now) == 0:
                return False

            close_book_now = RecGov.find_parent_with_tag(close_book_now[0], "button")
            close_book_now.click()

            print(output_details_to_user)
            return False
        else:
            print("---> " + location_str + ": You are now in control, please finish the booking process <---")
            # On the checkout screen, indicate for bot to end and allow user to take over
            return True

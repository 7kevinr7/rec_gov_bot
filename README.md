This bot is intended to help with booking camping and permit reservations on the Recreation.gov website.

------------------------------------------------------------------------------------
The bot is run by executing: python3 main.py

It will take your preferences and selections from the preferences/ directory to set up reservations.

---------------------------------------------------------------------------------------
The preferences directory currently has a couple files:

1. camping_locations.txt - This contains the desired campgrounds and sites along with some other details for the reservations

2. credentials.txt - This stores the credentials to be used to book the reservation

3. permit_locations.txt - This contains the desired wildernesses, etc. and entry points long with some other details for the reservations

4. preferences.txt - This contains the paths to the above files along with some bot settings that can be tweaked as needed

---------------------------------------------------------------------------------------
If the bot fails to run because of a chromedriver error. Replace the chromedriver that is present in the topmost directory with an updated version that matches your browser version.

It is wise to run "pkill chromedrivers" from a terminal window after a few uses of the RecGovBot. When the bot reaches the booking window where you have some time before checking out, the bot detaches the browser. This allows the browser to stay open, but there will be a chromedriver process still running after closing the browser.

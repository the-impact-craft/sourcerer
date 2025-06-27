"""Application settings and constants.

This module contains various configuration constants and settings used throughout
the application, including UI elements and display configurations.
"""

from enum import Enum

NO_DATA_LOGO = """
          ###                 ###
          ###                 ###
             ####         ####
             ####         ####
          #######################
       ######    #########    ######
       ######    #########    ######
    ###################################
    ###################################
    ###   #######################   ###
    ###   #######################   ###
    ###   ###                 ###   ###
             #######   #######
             #######   #######


###   ##                ##         #
####  ##  ####      ######  ####  #### #####
## ## ## ##  ##    ##   ##   ####  #    ####
##  #### ##  ##    ##   ## ##  ##  #  ##  ##
##    ##  ####       ##### ######  ### ### #
"""

MIN_SECTION_DIMENSION = 10


class KeyBindings(Enum):
    """Enum representing key bindings for various actions in the application."""

    ARROW_DOWN = "down"
    ARROW_UP = "up"
    ARROW_RIGHT = "right"
    ARROW_LEFT = "left"
    ENTER = "enter"
    BACKSPACE = "backspace"
    CTRL = "ctrl"

"""
This module contains the main entry point
"""

import src.overseer as overwatch


def main():
    overseer = overwatch.Overseer()
    overseer.start()

if __name__ == '__main__':
    main()

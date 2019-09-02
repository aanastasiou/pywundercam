"""Athanasios Anastasiou, September 2019

Mnemonic constants for various states.
"""
import enum

class ShootMode(enum.Enum):
    PHOTO = 0
    VIDEO3K = 1
    TIMER = 2
    CONTINUOUS = 3
    TIMELAPSE = 4
    VIDEO60FPS = 5
    LOOP = 6

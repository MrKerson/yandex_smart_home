"""Schema for toggle capability.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/toggle.html
"""

from enum import StrEnum

from .base import APIModel


class ToggleCapabilityInstance(StrEnum):
    """Instance of a toggle capability.

    https://yandex.ru/dev/dialogs/smart-home/doc/concepts/toggle-instance.html

    ``LEFT``/``RIGHT``/``CENTER`` and ``CHANNEL_*`` are experimental
    instances used by this fork to test multi-gang wall switches in Yandex
    Smart Home. They are not part of the public Yandex Smart Home API.
    """

    BACKLIGHT = "backlight"
    CONTROLS_LOCKED = "controls_locked"
    IONIZATION = "ionization"
    KEEP_WARM = "keep_warm"
    MUTE = "mute"
    OSCILLATION = "oscillation"
    PAUSE = "pause"

    # Experimental multi-gang switch instances.
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    CHANNEL_1 = "channel_1"
    CHANNEL_2 = "channel_2"
    CHANNEL_3 = "channel_3"
    CHANNEL_4 = "channel_4"
    CHANNEL_5 = "channel_5"
    CHANNEL_6 = "channel_6"
    CHANNEL_7 = "channel_7"
    CHANNEL_8 = "channel_8"


class ToggleCapabilityParameters(APIModel):
    """Parameters of a toggle capability."""

    instance: ToggleCapabilityInstance


class ToggleCapabilityInstanceActionState(APIModel):
    """New value for a toggle capability."""

    instance: ToggleCapabilityInstance
    value: bool

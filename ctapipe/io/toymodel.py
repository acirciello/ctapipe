# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Create a toymodel event stream of array events
"""
import logging

import numpy as np
import astropy.units as u

from ..containers import (
    DataContainer, DL1CameraContainer, EventIndexContainer,
)
from ..core import traits
from ..core import TelescopeComponent
from ..image import toymodel
from .eventsource import EventSource

logger = logging.getLogger(__name__)


class ToyEventSource(EventSource, TelescopeComponent):

    trigger_probability = traits.FloatTelescopeParameter(
        default_value=0.5, help='Probability that the telescope has an event',
    )

    min_length_m = traits.FloatTelescopeParameter(
        default_value=0.05, help='Minimum length m',
    )
    max_length_m = traits.FloatTelescopeParameter(
        default_value=0.3, help='Maximum length in m',
    )
    min_eccentricity = traits.FloatTelescopeParameter(
        default_value=0.8, help='Minimum eccentricity = sqrt(1 - width**2/length**2)',
    )
    max_eccentricity = traits.FloatTelescopeParameter(
        default_value=0.98, help='Maximum eccentricity = sqrt(1 - width**2/length**2)',
    )
    min_skewness = traits.FloatTelescopeParameter(
        default_value=0.1, help='Minimum skewness',
    )
    max_skewness = traits.FloatTelescopeParameter(
        default_value=0.5, help='Maximum skewness',
    )

    def __init__(self, subarray, config=None, parent=None, **kwargs):
        super().__init__(subarray=subarray, config=config, parent=parent, **kwargs)
        self._subarray = subarray
        self._camera_radii = {}

    @staticmethod
    def calc_width(eccentricity, length):
        return length * np.sqrt(1 - eccentricity**2)

    @property
    def subarray(self):
        return self._subarray

    @subarray.setter
    def subarray(self, value):
        self._subarray = value

    @classmethod
    def is_compatible(cls):
        return False

    def _generator(self):
        self.event_id = 0
        while True:
            if self.event_id >= self.max_events:
                break

            yield self.generate_event()
            self.event_id += 1

    def generate_event(self):

        event = DataContainer(
            index=EventIndexContainer(obs_id=1, event_id=self.event_id),
            trig=None,
            r0=None,
            dl0=None,
            dl2=None,
            mc=None,
            mcheader=None,
            count=self.event_id,
            calibration=None,
        )

        for tel_id, telescope in self.subarray.tel.items():
            if np.random.uniform() >= self.trigger_probability.tel[tel_id]:
                continue

            cam = telescope.camera.geometry

            # draw cog
            r_fraction = np.sqrt(np.random.uniform(0, 0.9))
            r = r_fraction * cam.guess_radius()
            phi = np.random.uniform(0, 2 * np.pi)
            x = r * np.cos(phi)
            y = r * np.sin(phi)

            # draw length
            length = np.random.uniform(
                self.min_length_m.tel[tel_id],
                self.max_length_m.tel[tel_id],
            )
            eccentricity = np.random.uniform(
                self.min_eccentricity.tel[tel_id],
                self.max_eccentricity.tel[tel_id],
            )
            width = self.calc_width(eccentricity, length)

            psi = np.random.randint(0, 360)
            intensity = np.random.poisson(int(1e5 * width * length))
            skewness = np.random.uniform(
                self.min_skewness.tel[tel_id],
                self.max_skewness.tel[tel_id]
            )

            model = toymodel.SkewedGaussian(
                x=x,
                y=y,
                length=length * u.m,
                width=width * u.m,
                psi=f'{psi}d',
                skewness=skewness,
            )
            image, _, _ = model.generate_image(
                cam,
                intensity,
            )

            event.dl1.tel[tel_id] = DL1CameraContainer(image=image)

        return event

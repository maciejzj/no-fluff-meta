"""Geolocation services."""

import functools
from typing import Sequence

from geopy.geocoders import Nominatim
from retry import retry

from it_jobs_meta.common.utils import throttle


class Geolocator:
    def __init__(self, country_filter: Sequence[str] | None = None):
        """Create geolocator instance.

        :param country_filter: Tuple of country names that the geolocation
            should be limited to (use ISO 3166-1alpha2 codes).
        """
        self._geolocator = Nominatim(user_agent='it-jobs-meta')
        self._country_filter = country_filter

    @functools.cache
    @retry(TimeoutError, tries=3, delay=10)
    @throttle(0.1)
    def __call__(self, city_name: str) -> tuple[str, float, float] | None:
        """Call to get_universal_city_name_lat_lon method."""
        return self.get_universal_city_name_lat_lon(city_name)

    def get_universal_city_name_lat_lon(
        self, city_name: str
    ) -> tuple[str, float, float] | None:
        """For given city name get it's location.

        :param city_name: Name of the city to geolocate, can be in native
            language or in English, different name variants will be unified on
            return.
        :return: Tuple with location as (unified_city_name, latitude,
            longitude) or None if location failed.
        """
        location = self._geolocator.geocode(
            city_name, country_codes=self._country_filter
        )

        if location is None:
            return None

        city_name = location.address.split(',')[0]
        return (city_name, location.latitude, location.longitude)

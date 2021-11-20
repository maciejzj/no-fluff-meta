import functools
from typing import Optional, Tuple

from geopy.geocoders import Nominatim


class Geolocator:
    geolocator = Nominatim(user_agent='it-jobs-meta')

    @functools.cache
    def __call__(self, city_name: str) -> Optional[Tuple[str, float, float]]:
        return self.get_universal_city_name_lat_lon(city_name)

    @classmethod
    def get_universal_city_name_lat_lon(
            cls, city_name: str) -> Optional[Tuple[str, float, float]]:
        location = cls.geolocator.geocode(city_name)

        if location is None:
            return None, None, None

        city_name, country_name = Geolocator.address_str_to_city_country_name(
            location.address)

        if country_name == 'Polska':
            return city_name, location.latitude, location.longitude
        else:
            return None, None, None

    @staticmethod
    def address_str_to_city_country_name(address: str) -> str:
        split_loc = address.split(',')
        city_name, country_name = split_loc[0].strip(), split_loc[-1].strip()
        return city_name, country_name

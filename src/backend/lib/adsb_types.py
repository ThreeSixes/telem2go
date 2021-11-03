"""
This file is part of telem2go. This file stores decoders.
"""

import math

from .util import AdsbCrc
from .util import Slicer

class AirbornePosition(dict):
    """
    ADS-B airborne position
    """

    def __new__(cls, bin_data):
        decoded = cls.__decode(bin_data)

        return decoded


    def __decode(bin_data):
        """
        Decode airborne position data.
        """
        decoded = {}

        field_descriptor = {
            "boundaries": [[1, 5], [6, 7], [8, 8], [9, 20], [21, 21], [22, 22], [23, 39], [40, 56]],
            "labels": ["me_type", "surveillance_status", "single_antenna_flag", "altitude",
                        "time", "cpr-format", "lat-cpr", "lon-cpr"],
            "types": [BinInt, AirbornePositionSurveillanceStatus, bool, bytearray, bool, BinInt,
                        BinInt, BinInt]
        }

        unwrapped_fields = Slicer.slice_bin(bin_data, field_descriptor['boundaries'])

        # Process all fields.
        for field_index in range(0, len(unwrapped_fields)):
            this_field_content = unwrapped_fields[field_index]
            decoded.update({
                field_descriptor['labels'][field_index]:
                    field_descriptor['types'][field_index](this_field_content)
            })
        
        altitude = decoded.pop('altitude')

        # Barometric altitude based on message type code.
        if decoded['me_type'] >= 9 and decoded['me_type'] <= 18:
            decoded.update({
                'altitude_type': 'barometric',
                'altitude_unit': 'ft',
                'altitude': BaroAlt(altitude)
            })
        elif decoded['me_type'] >= 20 and decoded['me_type'] <= 22:
            decoded.update({
                'altitude_type': 'gnss',
                'altitude_unit': 'm',
                'altitude': BinInt(altitude)
            })

        return decoded


class AirbornePositionSurveillanceStatus(str):
    """
    Returns a string representing the airborne position surveillance status.
    """

    def __new__(cls, ss: int):
        ss_str = ""
        ss_map = ["no condition", "permanent alert", "temporary alert", "spi"]

        ss_int = int.from_bytes(ss, 'big')

        try:
            ss_str = ss_map[ss_int]
        except IndexError:
            return("The surveillance status must be between 0x0 and 0x3.")
        
        return ss_str


class AirborneVelocity(dict):
    """
    Airborne velocity data
    """

    def __new__(cls, bin_data):
        decoded = cls.__decode(bin_data)

        return decoded


    def __decode(bin_data):
        """
        Decode airborne position frames
        """

        descriptor = {
            "boundaries": [[1, 5], [6, 8], [9, 9], [10, 10], [11, 13], [14, 35], [36, 36],
                        [37, 37], [38, 46], [47, 48], [49, 49], [50, 56]],
            "labels": ["me_type", "sub_type", "intent_change", "ifr_capability",
                        "velociy_uncertainty_catgoery", "sub_field", "source_bit",
                        "vert_rate_sign", "vert_rate_raw", "reserved", "gnss_baro_alt_diff_sign",
                        "gnss_baro_alt_diff"],
            "types": [BinInt, BinInt, bool, BinInt, BinInt, bytearray, BinInt, BinInt,
                        BinInt, BinInt, BinInt, BinInt]
        }

        decoded = {}

        unwrapped_fields = Slicer.slice_bin(bin_data, descriptor['boundaries'])

        for field_index in range(0, len(unwrapped_fields)):
            this_field_content = unwrapped_fields[field_index]
            decoded.update({
                descriptor['labels'][field_index]:
                    descriptor['types'][field_index](this_field_content)
            })

        return decoded


class AisStr(str):
    """
    AIS string from bytearray.
    """

    ais_charset = [
        "@", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P",
        "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "[", "/", "]", "^", "_", " ", "!",
        "\"", "#", "$", "%", "&", "\\", "(", ")", "*", "+", ",", "-", ".", "/", "0", "1", "2",
        "3", "4", "5", "6", "7", "8", "9", ":", ";", "<", "=", ">", "?"
    ]

    def __new__(cls, bin_data):
        value = ""

        # Each char is 6 bits.
        bitmask = 0x3f

        # How many 6 bit characters do we have?
        char_ct = math.floor((len(bin_data) * 8) / 6)

        # Convert our bytes to a big int...
        bytes_as_int = int.from_bytes(bin_data, 'big')

        # Decode each character.
        for cursor in range(0, char_ct):
            char_idx = (bytes_as_int >> (cursor * 6)) & bitmask
            value = cls.ais_charset[char_idx] + value

        # Return as a string object.
        return str.__new__(cls, value)


class BinInt(int):
    """
    Integer from bing-endian binary data
    """

    def __new__(cls, bin_data):
        value = int.from_bytes(bin_data, 'big')
        return int.__new__(cls, value)


class BaroAlt(int):
    """
    Barometric altitude
    """

    def __new__(self, bin_data):
        altitude = 0

        decoded = {}

        field_descriptor = {
            # Bits 1-4 are padding all 12 bits are big endian.
            "boundaries": [[5, 11], [12, 12], [13, 16]],
            "labels": ["alt_1", "q_bit", "alt_2"],
            "types": [BinInt, bool, BinInt]
        }

        unwrapped_fields = Slicer.slice_bin(bin_data, field_descriptor['boundaries'])

        for field_index in range(0, len(unwrapped_fields)):
            this_field_content = unwrapped_fields[field_index]
            decoded.update({
                field_descriptor['labels'][field_index]:
                    field_descriptor['types'][field_index](this_field_content)
            })

        alt_combined = (decoded['alt_1'] * 4) + (decoded['alt_2'])
        
        # Q bit sets 25 ft increments w/ a 1K ft offset.
        if decoded["q_bit"] is True:
            altitude = (alt_combined * 25) - 1000
        else:
            raise RuntimeWarning("Altitude encoded w/gray code.")

        return int(altitude)


class Crc(dict):
    """
    ADS-B CRC field
    """

    def __new__(cls, bin_data):
        decoded = cls.__decode(bin_data)

        return decoded


    def __decode(bin_data):
        """
        Decode ID and category data.
        """
        decoded = {}

        computed_crc_table = AdsbCrc.compute_crc_table()
        bitmask = 0xffffff

        # Everything but the 3 byte CRC is data.
        data_field_len_bytes = len(bin_data) - 3

        # Get boundaries of
        data_field = bin_data[:data_field_len_bytes]
        crc_field = int.from_bytes(bin_data[-3:], 'big')

        crc = 0
        
        # Compute the CRC for the data portion of the frame.
        for i in range(0, len(data_field)):
            crc = computed_crc_table[((crc >> 16) ^ data_field[i]) & 0xff] ^ (crc << 8)
        
        crc = (crc & bitmask)
        
        # Look for a match.
        crc_match = False
        if crc == crc_field:
            crc_match = True

        decoded.update({
             "crc_match": crc_match,
             "crc_hex": hex(crc)[2:] # CRC in hex without the 0x
         })

        return decoded


class ExtendedSquitter(dict):
    """
    Extended squitter
    """

    def __new__(cls, df, ca, bin_data):
        decoded = cls.__decode(df, ca, bin_data)

        return decoded


    def __decode(df, ca, bin_data):
        decoded = {}

        if df == 17:
            decoded.update({"df_name": "extended squitter"})
            decoded.update(MessageField(bin_data))

        else:
            decoded.update({"raw_data": bin_data.hex()})

        return decoded


class ShortSquitter(dict):
    """
    Short (7 byte) frame data.
    """

    def __new__(cls, df, ca, bin_data):
        decoded = cls.__decode(df, ca, bin_data)

        return decoded


    def __decode(df, ca, bin_data):
        """
        Decode a 7 byte squitter
        """

        decoded = {}

        if False:
            pass

        else:
            decoded.update({"raw_data": bin_data.hex()})

        return decoded


class IcaoAA(str):
    """
    ICAO Aircraft Address
    """
    def __new__(cls, icao_aa):
        # Handle ICAO AA based on incoming type.
        incoming_type = type(icao_aa)
        if incoming_type is int:
            cls.__icao_int = icao_aa
        elif incoming_type is bytearray:
            cls.__icao_int = int.from_bytes(icao_aa, 'big')
        elif incoming_type is str:
            try:
                icao_aa.replace("0x", "")
                cls.__icao_int = int(icao_aa, 16)
            except ValueError:
                raise ValueError("An ICAO Aircraft address must be a hex string " \
                    "representing a number between >= 0 and <= ffffff.")

        # Post-conversion boundary check.
        if cls.__icao_int < 0x0 and cls.__icao_int > 0xffffff:
            raise ValueError("An ICAO Aircraft address must be >= 0x0 and <= 0xffffff.")

        icao_hex_str = hex(cls.__icao_int)[2:]
        
        # Expand ICAO AA to 6 characters.
        missing = 6 - len(icao_hex_str)
        for i in range(0, missing):
            icao_hex_str = "0" + icao_hex_str

        return str.__new__(cls, icao_hex_str)


    def __int__(cls):
        """
        ICAO AA as integer
        """
        return cls.__icao_int


class IdAndCategory(dict):
    """
    ADS-B aircraft ident and category
    """

    def __new__(cls, bin_data):
        decoded = cls.__decode(bin_data)

        return decoded


    def __decode(bin_data):
        """
        Decode ID and category data.
        """
        decoded = {}

        field_descriptor = {
            "boundaries": [[1, 5], [6, 8], [9, 56]],
            "labels": ["me_type", "aircraft_category", "ident"],
            "types": [BinInt, BinInt, AisStr]
        }

        unwrapped_fields = Slicer.slice_bin(bin_data, field_descriptor['boundaries'])

        # Process all fields.
        for field_index in range(0, len(unwrapped_fields)):
            this_field_content = unwrapped_fields[field_index]
            decoded.update({
                field_descriptor['labels'][field_index]:
                    field_descriptor['types'][field_index](this_field_content)
            })

        return decoded


class MessageField(dict):
    """
    ADSB Message field
    """

    def __new__(cls, me_field):
        decoded = cls.__decode_field(me_field)

        return decoded


    def __decode_field(me_field):
        """
        Decode our message field.
        """

        decoded = dict()

        descriptor = {
            "boundaries": [[1, 5], [1, 56]],
            "labels": ["me_type", "me_data"],
            "types": [BinInt, bytearray]
        }

        unwrapped_fields = Slicer.slice_bin(me_field, descriptor['boundaries'])

        for field_index in range(0, len(unwrapped_fields)):
            this_field_content = unwrapped_fields[field_index]
            decoded.update({
                descriptor['labels'][field_index]:
                    descriptor['types'][field_index](this_field_content)
            })

        # Aircraft ID and category data.
        if decoded['me_type'] >= 1 and decoded['me_type'] <= 4:
            me_data = decoded.pop('me_data')
            decoded.update(IdAndCategory(me_data))
            decoded.update({"me_type_name": "aircraft identification"})
        
            # Get our named category data.
            decoded.update(WakeVortexCategory(decoded['me_type'], decoded['aircraft_category']))

        # Airborne position data.
        elif decoded['me_type'] >= 9 and decoded['me_type'] <= 18:
            me_data = decoded.pop('me_data')
            decoded.update(AirbornePosition(me_data))
            decoded.update({"me_type_name": "airborne position (baro alt)"})

        # Airborne velocity data.
        elif decoded['me_type'] == 19:
            me_data = decoded.pop('me_data')
            decoded.update(AirborneVelocity(me_data))
            decoded.update({"me_type_name": "airborne velocity"})

        # Airborne position data.
        elif decoded['me_type'] >= 20 and decoded['me_type'] <= 22:
            me_data = decoded.pop('me_data')
            decoded.update(AirbornePosition(me_data))
            decoded.update({"me_type_name": "airborne position (gnss height)"})

        # Reseved.
        elif decoded['me_type'] >= 23 and decoded['me_type'] <= 27:
            me_data = decoded.pop('me_data')
            decoded.update({"me_type_name": "reserved"})

        # Aircraft status.
        elif decoded['me_type'] == 28:
            me_data = decoded.pop('me_data')
            decoded.update({"me_type_name": "aircraft status"})

        # Target state and status information.
        elif decoded['me_type'] == 29:
            me_data = decoded.pop('me_data')
            decoded.update({"me_type_name": "target state and status information"})

        # Target state and status information.
        elif decoded['me_type'] == 31:
            me_data = decoded.pop('me_data')
            decoded.update({"me_type_name": "aircraft operation status"})

        return decoded


class WakeVortexCategory(dict):
    """
    Decode wake vortex category
    """

    def __new__(cls, me_type, category):
        return cls.__decode(me_type, category)

    def __decode(me_type, category):
        """
        Decode wake vortex category data.
        """

        wake_cat_data = {}

        tc_ca_matrix = [
            None, # TC 0, illegal
            None, # TC 1, no info
            [ # TC 2
                "no category info", # CA 0
                "surface emergency vehicle", # CA 1
                "surface service vehicle", # CA 2
                "ground obstruction", # CA 3
                "ground obstruction", # CA 4
                "ground obstruction", # CA 5
                "ground obstruction", # CA 6
                "ground obstruction", # CA 7
            ],
            [ # TC 3
                "no category info", # CA 0
                "glider/sailplane", # CA 1
                "lighter-than-air", # CA 2
                "parachutist/skydiver", # CA 3
                "ultralight/hang-glider/paraglider", # CA 4
                "reserved", # CA 5
                "unmanned aerial vehicle", # CA 6
                "space/transatmospheric vheicle", # CA 7
            ], 
            [ # TC 4
                "no category info", # CA 0
                "light aircraft", # CA 1
                "medium 1 aircraft", # CA 2
                "medium 2 aircraft", # CA 3
                "high vortex aircraft", # CA 4
                "heavy aircraft", # CA 5
                "high performance aircraft", # CA 6
                "rotorcraft", # CA 7
            ] 
        ]

        # invalid
        if me_type == 0:
            pass
        # reserved
        elif me_type == 1:
            wake_cat_data.update({
                'aircraft_category_name': "reserved"})
        # all others
        else:
            wake_cat_data.update({
                'aircraft_category_name': tc_ca_matrix[me_type][category]})

        return wake_cat_data


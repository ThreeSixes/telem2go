"""
This file is part of Flextelem. Its purpose is to support decoding ADS-B frames.
https://mode-s.org/decode/index.html
"""

from .adsb_types import *
from .util import Slicer


class ADSBFrame(dict):
    """
    Class representing an ADS-B frame.
    """

    def __new__(cls, frame):
        # Handle our frame based on incoming type.
        if type(frame) is str:
            try:
                frame = bytearray.fromhex(frame)
            except ValueError:
                raise TypeError("Please provide a frame as a hex string or bytearray.")
        elif type(frame) is bytearray:
            frame = frame
        else:
            raise TypeError("Please provide a frame as a hex string or bytearray.")
        
        # See if we have a frame of expected length.
        if len(frame) not in [7, 14]:
            raise ValueError("Frames must be 7 or 14 bytes in length.")
        
        return cls.__decode(frame)


    def __decode(frame):
        """
        Decode an ADS-B frame, returning a dictionary that contains the frame's fields, or None
        if a frame can't be decoded.
        """

        adsb_short_frame_descriptor = {
            "boundaries": [[1, 5], [6, 8], [9, 32], [33, 56]],
            "labels": ["df", "ca", "aa", "data"],
            "types": [BinInt, BinInt, IcaoAA, bytearray]
        }

        adsb_ext_frame_descriptor = {
            "boundaries": [[1, 5], [6, 8], [9, 32], [33, 88]],
            "labels": ["df", "ca", "icao", "data"],
            "types": [BinInt, BinInt, IcaoAA, bytearray]
        }

        # Build a frame descriptor.
        frame_parsed = {
            "frame_hex": frame,
            "frame_bytes": len(frame)
        }

        if frame_parsed['frame_bytes'] in [7, 14]:
            # Build CRC object.
            crc_object = Crc(frame_parsed['frame_hex'])
            frame_parsed.update(crc_object)

        # 56 bit / 7 byte short squitter frame
        if frame_parsed['frame_bytes'] == 7:
            frame_parsed['frame_mode'] = "s short?"

            # Get our raw binary fields.
            frame_fields_raw = Slicer.slice_bin(
                frame, adsb_short_frame_descriptor['boundaries'])

            # Break the frame down.
            for field_cursor in range(0, len(adsb_short_frame_descriptor['labels'])):
                type_cast = adsb_short_frame_descriptor['types'][field_cursor]
                field_label = adsb_short_frame_descriptor['labels'][field_cursor] 
                field_value = type_cast(frame_fields_raw[field_cursor])

                # If we have a dictionary just integrate it.
                if type(field_value) is dict:
                    frame_parsed.update(field_value)
                # Or else add the new field.
                else:
                    frame_parsed.update({
                        field_label: field_value
                    })

            # Remove the raw frame since we know what it is.
            frame_parsed.pop('frame_hex')

            # Grab data for parsing.
            data = frame_parsed.pop('data')

            frame_parsed.update(ShortSquitter(
                frame_parsed['df'],
                frame_parsed['ca'],
                data))

        # 112 bit / 14 byte extended squitter frame
        elif frame_parsed['frame_bytes'] == 14:
            # Set frame type.
            frame_parsed['frame_mode'] = "s extended"

            # Get our raw binary fields.
            frame_fields_raw = Slicer.slice_bin(
                frame, adsb_ext_frame_descriptor['boundaries'])

            # Break the ES frame down.
            for field_cursor in range(0, len(adsb_ext_frame_descriptor['labels'])):
                type_cast = adsb_ext_frame_descriptor['types'][field_cursor]
                field_label = adsb_ext_frame_descriptor['labels'][field_cursor] 
                field_value = type_cast(frame_fields_raw[field_cursor])

                # If we have a dictionary just integrate it.
                if type(field_value) is dict:
                    frame_parsed.update(field_value)
                # Or else add the new field.
                else:
                    frame_parsed.update({
                        field_label: field_value
                    })

            # Remove the raw frame since we know what it is.
            frame_parsed.pop('frame_hex')

            # Grab data for parsing.
            data = frame_parsed.pop('data')

            frame_parsed.update(ExtendedSquitter(
                frame_parsed['df'],
                frame_parsed['ca'],
                data
            ))

            ## DF 0 - ACAS short reply
            #if frame_parsed['df'] == 0:
            #    frame_parsed.update({"df_name": "acas short reply"})
            #    frame_parsed.update({"raw_data": data.hex()})

            ## DF 4 - Altitude reply
            #elif frame_parsed['df'] == 4:
            #    frame_parsed.update({"df_name": "altitude reply"})
            #    frame_parsed.update({"raw_data": data.hex()})

            ## DF 5 - Identity reply
            #elif frame_parsed['df'] == 5:
            #    frame_parsed.update({"df_name": "identity reply"})
            #    frame_parsed.update({"raw_data": data.hex()})

            ## DF 16 - ACAS long reply
            #elif frame_parsed['df'] == 16:
            #    frame_parsed.update({"df_name": "acas long reply"})
            #    frame_parsed.update({"raw_data": data.hex()})

            ## DF 21 - Identity reply
            #elif frame_parsed['df'] == 21:
            #    frame_parsed.update({"df_name": "identity reply"})
            #    frame_parsed.update({"raw_data": data.hex()})

            #else:
            #    frame_parsed.update({"raw_data": data.hex()})

        return frame_parsed

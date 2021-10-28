import math
from pprint import pprint


class Slicer:
    @staticmethod
    def slice_bin(bin_data, chunks, debug=False):
        """
        Slice a binary string into smaller binary chunks given binary data and a list of chunk boundaries.
        """

        slices = []

        bin_int = int.from_bytes(bin_data, 'big')
        len_bits = len(bin_data) * 8

        if debug is True:
            print("----")
            print(" Bytes: %s" %hex(bin_int))
            print(" Len: %s bits" %len_bits)

        for chunk in chunks:
            # Chunk boundaries.
            chunk_start = chunk[0]
            chunk_end = chunk[1]

            # Compute chunk parameters
            chunk_len = chunk_end - chunk_start + 1
            chunk_mask = int(2 ** chunk_len) - 1
            chunk_required_bytes = math.ceil((chunk_len) / 8)
            chunk_shift = len_bits - chunk_end

            # Build an appropriately sized bytearray to ultimately hold our chunk
            this_chunk = bytearray(chunk_required_bytes)

            # Whole chunk as integer via shifting right and ANDing with our binary mask.
            chunk_int = int((bin_int >> chunk_shift) & chunk_mask)

            # Debug
            if debug is True:
                print(" Chunk: %s -> %s" %(chunk_start, chunk_end))
                print(" Chunk len: %s" %chunk_len)
                print(" Chunk shift: %s" %chunk_shift)
                print(" Chunk mask: %s" %bin(chunk_mask))
                print(" Chunk bits: %s" %bin(chunk_int))
                print(" Requred chunk bytes: %s" %chunk_required_bytes)
 
            for chunk_byte_cursor in range(0, chunk_required_bytes):
                chunk_byte_shift = ((chunk_required_bytes - 1) * 8) - (chunk_byte_cursor * 8)

                if debug is True:
                    print("  Chunk byte cursor: %s" %chunk_byte_cursor)
                    print("  Chunk shift right: %s bits" %chunk_byte_shift)

                # Shift right and limit to one byte.
                chunk_byte = int((chunk_int >> chunk_byte_shift) & 0xff)

                # Debug
                if debug is True:
                    print("  Chunk byte: %s" %hex(chunk_byte))
                
                this_chunk[chunk_byte_cursor] = chunk_byte

            if debug is True:
                print(" +++")

            slices.append(this_chunk)

        if debug is True:
            print(slices)
            print()

        return slices

 
    @staticmethod
    def old_slice_bin(bin_data, chunks):
        """
        Slice a binary string into smaller binary chunks given binary data and a list of chunk boundaries.
        """

        slices = []

        for chunk in chunks:
            chunk_start = chunk[0]
            chunk_end = chunk[1]

            # Construct bytes object to hold our chunk.
            chunk_bytes_required = math.ceil((chunk_end - chunk_start) / 8)
            this_chunk = bytearray(chunk_bytes_required)

            # Byte offset start and end for loop.
            chunk_offset_start = math.floor(chunk_start / 8)
            chunk_offset_end = math.ceil(chunk_end / 8)

            chunk_byte_cursor = 0

            # Loop thorugh the bytes in the binary data containing interesting data.
            for interesting_byte_index in range(chunk_offset_start, chunk_offset_end):
                # Get the current byte we want to manipulate
                interesting_byte = bin_data[interesting_byte_index]

                # Figure out where we are in our number line.
                byte_boundary_start = interesting_byte_index * 8
                byte_boundary_end = byte_boundary_start + 7
                bit_stop_in_byte = ((8 + (byte_boundary_start - chunk_start)) % 8) + 1

                # Figoure out the parameters we need to operate against our byte.
                shift_right = 8 - ((byte_boundary_end + chunk_end) % 8) - 1
                and_mask = int(2 ** abs(shift_right - bit_stop_in_byte)) - 1

                # Get the byte we want.
                this_chunk[chunk_byte_cursor] = (interesting_byte >> shift_right) & and_mask

                # Increment the chunk byte cursor.
                chunk_byte_cursor += 1

            # Tack our byte array onto the slice.
            slices.append(this_chunk)

        return slices


class AdsbCrc:
    """
    ADS-B CRC funcitons
    """

    def compute_crc_table():
        """
        Create CRC value table for improved CRC computation performance.
        
        Returns the CRC table.
        """
        
        crc = 0
        crc_table = []
        crc_poly = 0xfff409
        bitmask = 0xffffff
        
        for i in range(0, 256):
            crc = i << 16
            
            for j in range(0, 8):
                if int(crc & 0x800000) > 0:
                    crc = ((crc << 1) ^ crc_poly) & bitmask
                else:
                    crc = (crc << 1) & bitmask
            
            crc_table.append((crc & bitmask))
        
        return crc_table

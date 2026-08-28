"""
stego.py

The actual hiding mechanism: LSB (Least Significant Bit) steganography.

Every pixel in an image is made of color channel bytes (Red, Green, Blue,
each 0-255). Changing just the very last bit of one of those bytes shifts
the color value by at most 1 out of 255, completely invisible to the eye,
but that's a free bit of storage per channel. Chain enough of those bits
together across enough pixels and you can hide a real message inside a
completely normal-looking photo.

Only works reliably on lossless formats (PNG), JPEG's compression would
scramble these bits and destroy the hidden data.
"""

MAGIC = b"STG1"  # marks an image as "hidden data placed here by this tool"


def _bytes_to_bits(data: bytes) -> list:
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def _bits_to_bytes(bits: list) -> bytes:
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        byte = 0
        for bit in bits[i:i + 8]:
            byte = (byte << 1) | bit
        out.append(byte)
    return bytes(out)


def capacity_bytes(image) -> int:
    """How many bytes could theoretically fit in this image, header included."""
    width, height = image.size
    return (width * height * 3) // 8


def embed_data(image, payload: bytes):
    """
    Hides payload inside a copy of the image. Returns a new PIL Image,
    the original is left untouched.
    """
    img = image.convert("RGB")
    header = MAGIC + len(payload).to_bytes(4, "big")
    bits = _bytes_to_bits(header + payload)

    if len(bits) > capacity_bytes(img) * 8:
        raise ValueError(
            f"Message too large for this image. This image can hold about "
            f"{capacity_bytes(img)} bytes, the message needs {len(payload)}."
        )

    pixels = list(img.getdata())
    new_pixels = []
    bit_index = 0

    for r, g, b in pixels:
        if bit_index < len(bits):
            r = (r & ~1) | bits[bit_index]
            bit_index += 1
        if bit_index < len(bits):
            g = (g & ~1) | bits[bit_index]
            bit_index += 1
        if bit_index < len(bits):
            b = (b & ~1) | bits[bit_index]
            bit_index += 1
        new_pixels.append((r, g, b))

    out = img.copy()
    out.putdata(new_pixels)
    return out


def extract_data(image):
    """
    Pulls hidden data back out, if this image was actually embedded by this
    tool. Returns the payload bytes, or None if the magic header doesn't
    match (meaning: nothing hidden here, or hidden by something else).
    """
    img = image.convert("RGB")
    pixels = img.getdata()

    header_bits_needed = 8 * 8  # MAGIC (4 bytes) + length (4 bytes)
    bits = []
    for r, g, b in pixels:
        for channel in (r, g, b):
            bits.append(channel & 1)
            if len(bits) >= header_bits_needed:
                break
        if len(bits) >= header_bits_needed:
            break

    header = _bits_to_bytes(bits)
    if header[:4] != MAGIC:
        return None

    length = int.from_bytes(header[4:8], "big")
    total_bits_needed = (8 + length) * 8

    bits = []
    for r, g, b in pixels:
        for channel in (r, g, b):
            bits.append(channel & 1)
            if len(bits) >= total_bits_needed:
                break
        if len(bits) >= total_bits_needed:
            break

    all_bytes = _bits_to_bytes(bits)
    return all_bytes[8:8 + length]

"""
detector.py

The blue team half of this project: given an arbitrary image, how likely
is it that something's hidden inside it?

Two different techniques, because they catch different things:

1. Signature check - instant, 100% reliable, but only catches images
   this exact tool embedded (it looks for the MAGIC header from stego.py).

2. Chi-square / Pairs-of-Values analysis - a real steganalysis technique
   (Westfeld's chi-square attack), works on LSB steganography from ANY
   tool, not just this one, but it's a heuristic, not a certainty. LSB
   replacement tends to equalize the frequency of pixel values that only
   differ in their last bit (e.g. 100 and 101 start showing up almost
   equally often), which is a pattern natural, un-tampered images usually
   don't show as strongly. This gets less reliable the less of the image's
   capacity was actually used for hiding data.

Worth being upfront about: neither method involves visually eyeballing
the image for anything odd, encrypted payload bits look statistically
random, and so does a lot of natural sensor noise. That's exactly why
detection needs actual statistics instead of just looking at it.
"""

import numpy as np
from PIL import Image
from scipy import stats

from stego import extract_data


def has_signature(image) -> bool:
    """True if this exact tool hid something in this image."""
    return extract_data(image) is not None


def chi_square_score(image) -> float:
    """
    Returns a 0-100 suspicion score, based on a proper chi-square p-value
    rather than an arbitrary raw threshold. Raw chi-square magnitudes vary
    wildly between images depending on content, an unmodified photo can
    naturally score anywhere from near 0 to over 100 in raw terms, which
    makes a fixed cutoff unreliable. Converting to a p-value against the
    chi-square distribution (using the pair count as degrees of freedom)
    self-corrects for that, verified against several differently-generated
    test images before shipping this version.
    """
    arr = np.array(image.convert("RGB")).flatten()
    counts = np.bincount(arr, minlength=256).astype(float)

    chi2_stat = 0.0
    degrees_of_freedom = 0
    for i in range(0, 256, 2):
        expected = (counts[i] + counts[i + 1]) / 2
        if expected < 4:
            continue  # too few samples at this value to mean anything
        chi2_stat += ((counts[i] - expected) ** 2) / expected
        degrees_of_freedom += 1

    if degrees_of_freedom == 0:
        return 0.0

    # a high p-value here means "these pair frequencies are suspiciously
    # close to already-equalized", which is what LSB replacement causes
    p_value = stats.chi2.sf(chi2_stat, df=degrees_of_freedom)
    return round(p_value * 100, 1)


def extract_lsb_plane(image) -> Image.Image:
    """
    Pulls out just the last bit of every pixel and renders it as its own
    black-and-white image, the 'hidden layer' underneath what you'd
    normally see. A real forensic technique, shown here mostly for
    illustration since, as noted above, it doesn't reliably reveal
    tampering to the naked eye on its own.
    """
    arr = np.array(image.convert("RGB"))
    lsb = (arr & 1) * 255
    return Image.fromarray(lsb.astype("uint8"))


def scan_image(image) -> dict:
    """Runs both checks and returns a combined verdict for the API."""
    signature = has_signature(image)
    score = chi_square_score(image)

    if signature:
        verdict = "CONFIRMED - hidden data detected (matches this tool's signature)"
    elif score >= 70:
        verdict = "SUSPICIOUS - statistical analysis suggests possible LSB tampering"
    elif score >= 40:
        verdict = "UNCERTAIN - some irregularity, not conclusive"
    else:
        verdict = "CLEAN - no signs of LSB steganography"

    return {
        "signature_detected": signature,
        "chi_square_score": score,
        "verdict": verdict,
    }

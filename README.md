# Steganographic Exfil Simulator

A paired red team / blue team tool. Hides an encrypted message inside an
image using LSB steganography (the "how attackers actually exfiltrate
data past filters" side), and scans images to catch when that's been
done (the "how you'd actually detect it" side).

## How it works

**Conceal (red team)** — your message gets encrypted first (Fernet, with
a password-derived key, see `crypto_utils.py`), then the encrypted bytes
get hidden inside the image by overwriting the least significant bit of
each pixel's color channels. Changing a pixel's value by at most 1 out
of 255 is invisible to the eye, but it's a free bit of storage per
channel, chain enough of them together and you can hide a real message.

**Detect (blue team)** — two different checks, because they catch
different things:
- **Signature check** — exact and 100% reliable, but only for images this
  exact tool created (it looks for a header this tool embeds).
- **Chi-square analysis** — a real steganalysis technique (Westfeld's
  chi-square / Pairs-of-Values attack) that can flag LSB tampering from
  *any* tool, not just this one, based on how embedding data disrupts
  natural pixel-value statistics. It's a genuine probability calculation
  (a proper chi-square p-value, not an arbitrary threshold), but it's a
  heuristic, not a certainty, see the honest limitations below.

**Reveal** — proves the round trip actually works: given the right
password, recovers the original message from a concealed image.

## Install

Requires Python 3.9+.

```bash
cd stego-exfil-simulator
python -m venv venv
venv\Scripts\pip.exe install -r requirements.txt      # Windows, sidesteps PowerShell activation issues
venv\Scripts\python.exe app.py
```

Then open the local address shown in the terminal.

## Trying it out (for the best demo results)

1. Go to **Conceal**, upload a PNG, pick a real photo if you can, not a
   plain screenshot or a solid-color image. Type a message of a
   reasonable length (a sentence or two, not just three words), set a
   password, hit "Encrypt & Hide", and download the result.
2. Go to **Detect**, upload that downloaded image. You should see
   Signature Match = YES and a CONFIRMED verdict, that part is always
   reliable regardless of image or message size.
3. Go to **Reveal**, upload the same image with the same password, and
   you'll get your original message back exactly.

## Being honest about the chi-square score

Real camera photos naturally have compression-related patterns in their
pixel statistics that LSB embedding disrupts, which is exactly what the
chi-square test is designed to catch. Very smooth, synthetic, or
already-flat images (think: a plain gradient, a screenshot of a solid
UI) often don't have those patterns to begin with, so the test has much
less signal to work with on them, and a small message barely touches
enough pixels to register statistically either way.

This isn't a bug, it's genuinely how this class of steganalysis
technique behaves, real security tools have the same content-dependent
blind spots. That's exactly why this project pairs it with the
signature check instead of relying on statistics alone, one method
covers what the other can miss.

## Project structure

```
stego-exfil-simulator/
├── app.py               Flask routes for conceal / detect / reveal
├── stego.py              LSB embed/extract engine
├── crypto_utils.py       Fernet encryption with a password-derived key
├── detector.py            signature check + chi-square analysis + bit-plane extraction
├── templates/
│   └── dashboard.html
└── static/
    ├── style.css          darkroom/forensics theme
    └── dashboard.js
```

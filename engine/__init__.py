"""VeriDoc validation engine.

Deterministic checks only: Tesseract OCR, OpenCV, Pillow, rules and statistics.
No Generative AI or LLM libraries are used anywhere in this package (NFR-05).
"""

from PIL import Image as _Image

# Decompression-bomb guard: an A4 page at 600 dpi is ~35 million pixels.
# Anything larger is refused before it can exhaust memory.
MAX_PIXELS = 50_000_000
_Image.MAX_IMAGE_PIXELS = MAX_PIXELS

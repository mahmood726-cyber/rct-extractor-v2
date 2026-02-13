#!/usr/bin/env python3
"""
PDF Degradation Simulator for OCR Stress Testing
=================================================

Simulates common document scanning issues to test OCR robustness:
- Gaussian blur (focus issues)
- Salt-and-pepper noise (scanner noise)
- Contrast reduction (faded documents)
- Rotation skew (crooked scanning)
- JPEG compression artifacts
- Resolution reduction

Usage:
    python scripts/degrade_pdf.py input.pdf --output degraded.pdf --blur 2.0
    python scripts/degrade_pdf.py input.pdf --all-degradations
    python scripts/degrade_pdf.py input.pdf --preset low_quality
"""

import argparse
import logging
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageOps
    import numpy as np
except ImportError:
    print("Error: Required libraries not installed.")
    print("Install with: pip install Pillow numpy")
    sys.exit(1)

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF not installed.")
    print("Install with: pip install pymupdf")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DegradationConfig:
    """Configuration for PDF degradation"""
    # Blur (simulates focus issues)
    blur_radius: float = 0.0  # 0-5, typical scanned: 0.5-2

    # Noise (simulates scanner noise)
    noise_amount: float = 0.0  # 0-1, typical scanned: 0.01-0.05

    # Contrast (simulates faded documents)
    contrast_factor: float = 1.0  # 0.5-1.5, faded: 0.6-0.8

    # Brightness (simulates exposure issues)
    brightness_factor: float = 1.0  # 0.5-1.5

    # Rotation (simulates crooked scanning)
    rotation_angle: float = 0.0  # degrees, typical: -3 to 3

    # JPEG quality (simulates compression artifacts)
    jpeg_quality: int = 95  # 1-100, low quality: 30-60

    # Resolution (DPI reduction)
    target_dpi: int = 300  # typical scan: 150-300

    # Page background color (simulates paper aging)
    background_tint: Tuple[int, int, int] = (255, 255, 255)  # RGB


# Preset degradation configurations
PRESETS = {
    "excellent": DegradationConfig(
        blur_radius=0.0,
        noise_amount=0.0,
        contrast_factor=1.0,
        jpeg_quality=95,
        target_dpi=300,
    ),
    "good": DegradationConfig(
        blur_radius=0.3,
        noise_amount=0.005,
        contrast_factor=0.95,
        jpeg_quality=85,
        target_dpi=300,
    ),
    "medium": DegradationConfig(
        blur_radius=0.8,
        noise_amount=0.02,
        contrast_factor=0.85,
        jpeg_quality=70,
        target_dpi=200,
    ),
    "low_quality": DegradationConfig(
        blur_radius=1.5,
        noise_amount=0.05,
        contrast_factor=0.7,
        jpeg_quality=50,
        target_dpi=150,
    ),
    "very_poor": DegradationConfig(
        blur_radius=2.5,
        noise_amount=0.1,
        contrast_factor=0.6,
        jpeg_quality=30,
        target_dpi=100,
        rotation_angle=1.5,
    ),
    "photocopy": DegradationConfig(
        blur_radius=1.0,
        noise_amount=0.03,
        contrast_factor=1.3,  # High contrast
        brightness_factor=1.1,
        jpeg_quality=60,
        target_dpi=150,
    ),
    "faded": DegradationConfig(
        blur_radius=0.5,
        noise_amount=0.01,
        contrast_factor=0.5,
        brightness_factor=1.2,
        jpeg_quality=70,
        target_dpi=200,
        background_tint=(255, 252, 240),  # Yellowed paper
    ),
    "skewed": DegradationConfig(
        blur_radius=0.3,
        noise_amount=0.01,
        rotation_angle=2.5,
        jpeg_quality=75,
        target_dpi=200,
    ),
}


class PDFDegrader:
    """Applies degradation effects to PDFs for OCR testing"""

    def __init__(self, config: DegradationConfig):
        self.config = config

    def degrade_image(self, image: Image.Image) -> Image.Image:
        """Apply degradation effects to a PIL Image"""
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Apply background tint (paper aging)
        if self.config.background_tint != (255, 255, 255):
            image = self._apply_background_tint(image)

        # Apply rotation (crooked scanning)
        if abs(self.config.rotation_angle) > 0.01:
            image = self._apply_rotation(image)

        # Apply blur (focus issues)
        if self.config.blur_radius > 0:
            image = self._apply_blur(image)

        # Apply noise (scanner noise)
        if self.config.noise_amount > 0:
            image = self._apply_noise(image)

        # Apply contrast adjustment
        if abs(self.config.contrast_factor - 1.0) > 0.01:
            image = self._apply_contrast(image)

        # Apply brightness adjustment
        if abs(self.config.brightness_factor - 1.0) > 0.01:
            image = self._apply_brightness(image)

        return image

    def _apply_background_tint(self, image: Image.Image) -> Image.Image:
        """Apply paper aging/tint effect"""
        # Create tinted background
        bg = Image.new('RGB', image.size, self.config.background_tint)

        # Blend with original (white areas get tinted)
        return Image.blend(image, bg, 0.1)

    def _apply_rotation(self, image: Image.Image) -> Image.Image:
        """Apply rotation to simulate crooked scanning"""
        return image.rotate(
            self.config.rotation_angle,
            resample=Image.BICUBIC,
            expand=False,
            fillcolor=(255, 255, 255)
        )

    def _apply_blur(self, image: Image.Image) -> Image.Image:
        """Apply Gaussian blur"""
        return image.filter(ImageFilter.GaussianBlur(radius=self.config.blur_radius))

    def _apply_noise(self, image: Image.Image) -> Image.Image:
        """Apply salt-and-pepper noise"""
        img_array = np.array(image)

        # Create noise mask
        noise = np.random.random(img_array.shape[:2])

        # Salt (white) noise
        salt_mask = noise < (self.config.noise_amount / 2)
        img_array[salt_mask] = 255

        # Pepper (black) noise
        pepper_mask = noise > (1 - self.config.noise_amount / 2)
        img_array[pepper_mask] = 0

        return Image.fromarray(img_array)

    def _apply_contrast(self, image: Image.Image) -> Image.Image:
        """Apply contrast adjustment"""
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(self.config.contrast_factor)

    def _apply_brightness(self, image: Image.Image) -> Image.Image:
        """Apply brightness adjustment"""
        enhancer = ImageEnhance.Brightness(image)
        return enhancer.enhance(self.config.brightness_factor)

    def degrade_pdf(self, input_path: Path, output_path: Path) -> None:
        """Degrade a PDF by converting to images and back"""
        logger.info(f"Degrading PDF: {input_path}")

        # Open source PDF
        doc = fitz.open(str(input_path))

        # Create output PDF
        output_doc = fitz.open()

        for page_num in range(len(doc)):
            page = doc[page_num]
            logger.info(f"Processing page {page_num + 1}/{len(doc)}")

            # Render page to image at target DPI
            zoom = self.config.target_dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Apply degradation
            degraded_img = self.degrade_image(img)

            # Apply JPEG compression if quality < 95
            if self.config.jpeg_quality < 95:
                # Save to temp JPEG and reload
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    degraded_img.save(tmp.name, 'JPEG', quality=self.config.jpeg_quality)
                    degraded_img = Image.open(tmp.name)
                    degraded_img.load()
                os.unlink(tmp.name)

            # Convert back to PDF page
            img_bytes = degraded_img.tobytes("raw", "RGB")
            img_pix = fitz.Pixmap(fitz.csRGB, degraded_img.width, degraded_img.height, img_bytes, 1)

            # Create new page with same size as original
            rect = page.rect
            new_page = output_doc.new_page(width=rect.width, height=rect.height)

            # Insert degraded image
            new_page.insert_image(rect, pixmap=img_pix)

        # Save output
        output_doc.save(str(output_path))
        output_doc.close()
        doc.close()

        logger.info(f"Degraded PDF saved: {output_path}")


def create_degradation_set(input_path: Path, output_dir: Path) -> List[Path]:
    """Create a full set of degraded versions"""
    output_dir.mkdir(parents=True, exist_ok=True)
    created_files = []

    stem = input_path.stem

    for preset_name, config in PRESETS.items():
        output_path = output_dir / f"{stem}_{preset_name}.pdf"
        degrader = PDFDegrader(config)
        degrader.degrade_pdf(input_path, output_path)
        created_files.append(output_path)

    return created_files


def main():
    parser = argparse.ArgumentParser(
        description="Degrade PDFs to simulate scanning/OCR issues"
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input PDF file"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output PDF file (default: input_degraded.pdf)"
    )
    parser.add_argument(
        "--preset", "-p",
        choices=list(PRESETS.keys()),
        help="Use preset degradation configuration"
    )
    parser.add_argument(
        "--all-presets",
        action="store_true",
        help="Generate all preset degradations"
    )

    # Individual degradation options
    parser.add_argument("--blur", type=float, default=0.0, help="Blur radius (0-5)")
    parser.add_argument("--noise", type=float, default=0.0, help="Noise amount (0-1)")
    parser.add_argument("--contrast", type=float, default=1.0, help="Contrast factor (0.5-1.5)")
    parser.add_argument("--brightness", type=float, default=1.0, help="Brightness factor (0.5-1.5)")
    parser.add_argument("--rotation", type=float, default=0.0, help="Rotation angle (degrees)")
    parser.add_argument("--jpeg-quality", type=int, default=95, help="JPEG quality (1-100)")
    parser.add_argument("--dpi", type=int, default=300, help="Target DPI")

    args = parser.parse_args()

    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)

    if args.all_presets:
        output_dir = args.output or args.input.parent / "degraded"
        created = create_degradation_set(args.input, output_dir)
        print(f"\nCreated {len(created)} degraded versions in: {output_dir}")
        for f in created:
            print(f"  - {f.name}")
    else:
        # Build config from args
        if args.preset:
            config = PRESETS[args.preset]
        else:
            config = DegradationConfig(
                blur_radius=args.blur,
                noise_amount=args.noise,
                contrast_factor=args.contrast,
                brightness_factor=args.brightness,
                rotation_angle=args.rotation,
                jpeg_quality=args.jpeg_quality,
                target_dpi=args.dpi,
            )

        output_path = args.output or args.input.parent / f"{args.input.stem}_degraded.pdf"

        degrader = PDFDegrader(config)
        degrader.degrade_pdf(args.input, output_path)

        print(f"\nDegraded PDF saved: {output_path}")


if __name__ == "__main__":
    main()

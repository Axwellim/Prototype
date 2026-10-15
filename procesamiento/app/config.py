from pathlib import Path
from typing import Literal
import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseModel):
    api_token: str = Field(min_length=32, max_length=256)
    ocr_enabled: bool = True
    tesseract_cmd: str = 'tesseract'
    tessdata_dir: str = ''
    refinement_tessdata_dir: str = ''
    ocr_mode: Literal['automatico', 'original', 'preprocesado', 'comparar'] = 'automatico'
    generate_pdf: bool = False
    max_pdf_bytes: int = Field(default=40 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024)
    input_mime: Literal['application/pdf', 'image/jpeg', 'image/png'] = 'application/pdf'
    ocr_timeout_seconds: int = Field(default=40, ge=1, le=120)
    render_dpi: int = Field(default=250, ge=100, le=400)
    max_image_pixels: int = Field(default=12000000, ge=10000, le=25000000)
    correct_orientation: bool = True
    osd_min_confidence: float = Field(default=5.0, ge=0)
    preprocess_grayscale: bool = True
    preprocess_contrast: bool = True
    preprocess_deskew: bool = True
    preprocess_denoise: bool = False
    preprocess_binarize: bool = False
    preprocess_upscale: bool = True
    max_bytes: int = Field(default=20 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024)
    max_pages: int = Field(default=100, ge=1, le=1000)
    timeout_seconds: int = Field(default=120, ge=1, le=600)
    max_text_chars: int = Field(default=1000000, ge=100, le=5000000)
    min_chars: int = Field(default=80, ge=1)
    min_words: int = Field(default=12, ge=1)
    min_printable_ratio: float = Field(default=0.95, ge=0, le=1)
    min_alnum_ratio: float = Field(default=0.55, ge=0, le=1)
    max_image_coverage: float = Field(default=0.65, ge=0, le=1)


def load_settings() -> Settings:
    load_dotenv(ROOT / '.env', override=False)
    values = {name: os.environ['PROCESSOR_' + name.upper()]
              for name in Settings.model_fields if 'PROCESSOR_' + name.upper() in os.environ}
    return Settings.model_validate(values)

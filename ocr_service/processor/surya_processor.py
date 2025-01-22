from typing import List

from PIL import Image
from surya.model.detection.model import (
    load_model as load_det_model,
    load_processor as load_det_processor,
)
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor
from surya.ocr import run_ocr

from ocr_service.supports import env


class SuryaProcessor:
    def __init__(self):
        pass

    @staticmethod
    def recognize_image(image: Image.Image):
        return SuryaProcessor.recognize_images([image])

    @staticmethod
    def recognize_images(images: List[Image.Image]):
        langs = env.SUPPORTED_LANGUAGES
        det_processor, det_model = load_det_processor(), load_det_model()
        rec_model, rec_processor = load_rec_model(), load_rec_processor()
        predictions = run_ocr(
            images=images,
            langs=[langs] * len(images),
            det_model=det_model,
            det_processor=det_processor,
            rec_model=rec_model,
            rec_processor=rec_processor,
        )
        results = []
        for index, prediction in enumerate(predictions):
            text = "\n".join(tl.text for tl in prediction.text_lines)
            results.append(
                {
                    "page_no": index,
                    "text": text,
                }
            )
        return results

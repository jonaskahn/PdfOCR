import io
import os
import re
from datetime import datetime

import fitz
import magic
from PIL import Image
from huggingface_hub.commands.upload_large_folder import logger
from sanic.request import File

from ocr_service.processor.surya_processor import SuryaProcessor
from ocr_service.supports import env, constants
from ocr_service.supports.errors import LogicError
from ocr_service.supports.utils import get_word_count
from sanic.log import logger


class OCRService:
    def __init__(self):
        pass

    @staticmethod
    async def recognize(file: File):
        if len(file.body) > env.MAX_FILE_SIZE:
            raise LogicError("File is too big")
        mime = magic.Magic(mime=True)
        file_type = mime.from_buffer(file.body)

        if file_type not in constants.ALLOWED_FILE_EXTENSIONS:
            raise LogicError(f"File type ({file_type}) is not allowed")
        file_extension = constants.ALLOWED_FILE_EXTENSIONS[file_type]
        output_filename, output_path = await OCRService.write_image(
            file, file_extension
        )
        try:
            match file_type:
                case "image/png":
                    return await OCRService.__recognize_image(output_path)
                case "image/jpeg":
                    return await OCRService.__recognize_image(output_path)
                case "application/pdf":
                    return await OCRService.__recognize_pdf(output_path)
                case _:
                    raise LogicError(f"Unsupported file type: {file_type}")
        finally:
            try:
                os.remove(output_path)
                logger.info(f"Removed file {output_path}")
            except FileNotFoundError:
                pass

    @staticmethod
    async def write_image(file: File, file_extension: str) -> tuple[str, str]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{timestamp}.{file_extension}"
        output_path = os.path.join(env.UPLOAD_DIR, output_filename)
        with open(output_path, "wb") as f:
            f.write(file.body)
        return output_filename, output_path

    @staticmethod
    async def __recognize_image(path: str):
        return SuryaProcessor.recognize_image(Image.open(path))

    @staticmethod
    async def __recognize_pdf(path: str):
        without_ocr_results = await OCRService.__extract_without_ocr(path)
        reprocessing_pages = []
        if len(without_ocr_results) == 0:
            return await OCRService.__extract_pdf_with_ocr(path)
        for result in without_ocr_results:
            page_no = int(result["page_no"])
            text = result["text"]
            if text is None or len(text) == 0:
                reprocessing_pages.append(page_no)
        if len(reprocessing_pages) == 0:
            return without_ocr_results
        with_ocr_result = await OCRService.__extract_pdf_with_ocr(
            path, reprocessing_pages
        )
        return OCRService.__filter_and_sort_data(with_ocr_result + without_ocr_results)


    @staticmethod
    def __filter_and_sort_data(data):
        # Filter out entries with None or empty text
        filtered_data = [entry for entry in data if entry.get('text')]

        # Sort by page number
        sorted_data = sorted(filtered_data, key=lambda x: x['page_no'])

        return sorted_data

    @staticmethod
    async def __extract_without_ocr(path: str) -> list[dict[str, str]]:
        text_by_page = []
        doc = fitz.open(path)
        try:
            # Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]

                # Remove annotations
                page.clean_contents()
                annots = page.annots()
                if annots:
                    for annot in annots:
                        page.delete_annot(annot)

                # Remove semi-transparent elements
                xrefs = page.get_contents()
                if xrefs:
                    for xref in xrefs:
                        content = doc.xref_stream(xref)
                        if content:
                            # Convert bytes to string
                            content_str = content.decode("utf-8", errors="ignore")

                            # Remove transparency operators
                            content_str = re.sub(
                                r"/Transparency\s*<<.*?>>", "", content_str
                            )
                            content_str = re.sub(
                                r"/CA\s+[0-9.]+", "/CA 1.0", content_str
                            )
                            content_str = re.sub(
                                r"/ca\s+[0-9.]+", "/ca 1.0", content_str
                            )

                            # Update stream content
                            doc.update_stream(xref, content_str.encode())

                # Handle watermarks in form XObjects
                for xref in page.get_contents():
                    cont = doc.xref_stream(xref)
                    if cont:
                        cont = re.sub(rb"/Watermark\s*<<.*?>>", b"", cont)
                        doc.update_stream(xref, cont)

                # Clean patterns
                page.clean_contents(sanitize=True)

                # 2. Extract text from cleaned page
                text = page.get_text()

                # 3. Post-process extracted text
                # Remove common watermark patterns
                text = re.sub(
                    f"(?i){env.WATERMARK_PATTERNS}",
                    "",
                    text,
                )
                # Remove excess whitespace
                text = re.sub(r"\s+", " ", text)
                text = text.strip()
                if text or get_word_count(text) >= env.MINIMUM_WORDS_PER_PAGE:
                    text_by_page.append(
                        {
                            "page_no": page_num,
                            "text": text,
                            "ocr": False
                        }
                    )
                else:
                    text_by_page.append(
                        {
                            "page_no": page_num,
                            "text": None,
                        }
                    )
            return text_by_page
        except Exception as e:
            logger.error(e)
            return []
        finally:
            doc.close()

    @staticmethod
    async def __extract_pdf_with_ocr(
        path: str, processing_page: list[int] | None = None
    ) -> list[dict[str, str]]:
        images: list[Image] = await OCRService.__convert_pdf_to_images(
            path, processing_page
        )
        result = SuryaProcessor.recognize_images(images)
        if processing_page is None:
            return result
        remapping_results = []
        index = 0
        for page_no in processing_page:
            remapping_results.append({
                "page_no": page_no,
                "text": result[index]["text"],
                "ocr": True
            })
            index += 1
        return remapping_results


    @staticmethod
    async def __convert_pdf_to_images(
        path: str, processing_page: list[int] | None, zoom_x=1.5, zoom_y=1.5
    ) -> list[Image]:
        pdf_document = fitz.open(path)
        try:
            images = []
            for page_num in range(pdf_document.page_count):
                if processing_page and (not page_num in processing_page):
                    continue
                page = pdf_document[page_num]
                mat = fitz.Matrix(zoom_x, zoom_y)
                pix = page.get_pixmap(matrix=mat)
                # Convert pixmap to PIL Image
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                images.append(img)
            return images
        except Exception as e:
            raise LogicError(f"Failed to extract images from PDF {path}: {e}")
        finally:
            pdf_document.close()

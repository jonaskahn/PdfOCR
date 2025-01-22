import platform
from json import dumps

from sanic import Sanic, Request
from sanic import json, text
from sanic.log import logger
from sanic.request import File
from sanic.worker.manager import WorkerManager
from sanic_cors import CORS

from ocr_service.services.ocr_service import OCRService
from ocr_service.supports import env
from ocr_service.supports.errors import LogicError
from ocr_service.supports.logger import setup_log

app = Sanic("OCR-SERVICE", dumps=dumps)
app.config.KEEP_ALIVE = False
app.config.REQUEST_TIMEOUT = 6000
app.config.RESPONSE_TIMEOUT = 6000

CORS(app)

WorkerManager.THRESHOLD = 600
if platform.system() == "Linux":
    logger.debug('use "fork" for multi-process')
    Sanic.start_method = "fork"
else:
    logger.debug('use "spawn" for multi-process')


@app.exception(Exception)
async def handle_exception(request: Request, exception: Exception):
    logger.error(exception, exc_info=True)
    return json(
        {"message": str(exception)},
        status=500,
    )


@app.exception(LogicError)
async def handle_exception(request: Request, exception: LogicError):
    logger.error(exception, exc_info=True)
    return json(
        {"message": str(exception)},
        status=400,
    )


@app.get("/api/health")
async def health(request: Request):
    return text("API is running!!!")


@app.post("/api/ocr")
async def ocr(request: Request):
    file: File = request.files.get("file")
    if not file:
        return json({"status_code": 400, "message": "No file provided"}, status=400)
    result = await OCRService.recognize(file)
    return json(
        {"message": "Successfully recognized!", "payload": result},
        status=200,
    )


if __name__ == "__main__":
    setup_log()
    app_debug_mode = True if env.DEBUG_MODE in ["on", "yes", "enabled"] else False
    app.run(
        host="0.0.0.0",
        port=8000,
        access_log=True,
        verbosity=True,
        dev=app_debug_mode,
        debug=app_debug_mode,
        workers=100,
    )

import asyncio
import os
import signal
from typing import Literal
import json
import logging
import secrets
import subprocess
import sys
import threading
import io
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import JSONResponse, Response

from .config import ROOT, Settings, load_settings
from .schemas import ProcessingResult
from .quality import QualityInput, evaluate
from .quality import QualityInput, evaluate

logger = logging.getLogger('uvicorn.error.procesamiento')


def stop_process_tree(process):
    # Termina también Tesseract antes de liberar el bloqueo y limpiar los temporales.
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
                       creationflags=subprocess.CREATE_NO_WINDOW, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    process.wait(timeout=10)


def run_worker(directory: Path, settings: Settings) -> ProcessingResult:
    result_path = directory / 'resultado.json'
    config_path = directory / 'config.json'
    config_path.write_text(settings.model_dump_json(), encoding='utf-8')
    process = subprocess.Popen([sys.executable, '-m', 'app.worker', str(directory / 'documento.bin'),
                                str(result_path), str(config_path)], cwd=ROOT,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               start_new_session=os.name != 'nt',
                               creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
    try:
        process.communicate(timeout=settings.timeout_seconds)
    except subprocess.TimeoutExpired:
        stop_process_tree(process)
        raise HTTPException(504, detail={'codigo': 'tiempo_excedido', 'mensaje': 'El procesamiento superó el tiempo permitido.'})
    if process.returncode or not result_path.exists():
        logger.error('El proceso de extracción terminó sin un resultado válido.')
        raise HTTPException(500, detail={'codigo': 'error_procesador', 'mensaje': 'No se pudo completar la extracción.'})
    try:
        data = json.loads(result_path.read_text(encoding='utf-8'))
        if not data['ok']:
            logger.warning('Documento rechazado: codigo=%s', data['codigo'])
            raise HTTPException(data['status'], detail={'codigo': data['codigo'], 'mensaje': data['mensaje']})
        return ProcessingResult.model_validate(data['resultado'])
    except HTTPException:
        raise
    except Exception:
        logger.exception('Respuesta inválida del proceso de extracción.')
        raise HTTPException(500, detail={'codigo': 'respuesta_invalida', 'mensaje': 'El procesador devolvió un resultado inválido.'})


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title='Procesamiento documental local', docs_url=None, redoc_url=None, openapi_url=None)
    busy = threading.Lock()

    @app.middleware('http')
    async def access(request: Request, call_next):
        if request.client and request.client.host not in ('127.0.0.1', '::1'):
            return JSONResponse({'detail': 'Solo se permiten conexiones locales.'}, status_code=403)
        supplied = request.headers.get('X-Processor-Token', '')
        if not secrets.compare_digest(supplied.encode(), settings.api_token.encode()):
            return JSONResponse({'detail': 'Credencial del servicio inválida.'}, status_code=401)
        return await call_next(request)

    @app.get('/salud')
    async def health():
        return {'estado': 'disponible', 'fase': 'extraccion_digital_y_ocr', 'ocr_habilitado': settings.ocr_enabled}

    @app.post('/procesar', response_model=ProcessingResult)
    async def process(request: Request, modo: Literal['automatico', 'original', 'preprocesado', 'comparar'] | None = Query(default=None), normalizar: bool = False):
        mime = request.headers.get('content-type', '').split(';')[0].strip().lower()
        if mime not in ('application/pdf', 'image/jpeg', 'image/png'):
            raise HTTPException(415, detail='Envía bytes PDF, JPG o PNG con su Content-Type correspondiente.')
        request_settings = settings.model_copy(update={'input_mime': mime, 'ocr_mode': modo or settings.ocr_mode, 'generate_pdf': normalizar})
        if not busy.acquire(blocking=False):
            raise HTTPException(503, detail='El procesador está ocupado. Reintenta más tarde.', headers={'Retry-After': '5'})
        started = perf_counter()
        try:
            length = request.headers.get('content-length')
            if length:
                try:
                    size = int(length)
                    if size < 0:
                        raise ValueError
                except ValueError:
                    raise HTTPException(400, detail='Content-Length no válido.')
                if size > settings.max_bytes:
                    raise HTTPException(413, detail='El archivo supera el tamaño permitido.')
            with TemporaryDirectory(prefix='imantag-') as temporary:
                directory = Path(temporary)
                count = 0
                with (directory / 'documento.bin').open('wb') as destination:
                    async with asyncio.timeout(30):
                        async for chunk in request.stream():
                            count += len(chunk)
                            if count > settings.max_bytes:
                                raise HTTPException(413, detail='El archivo supera el tamaño permitido.')
                            destination.write(chunk)
                if not count:
                    raise HTTPException(422, detail='El archivo está vacío.')
                # shield permite terminar/limpiar el hijo aunque se desconecte el cliente.
                task = asyncio.create_task(asyncio.to_thread(run_worker, directory, request_settings))
                try:
                    result = await asyncio.shield(task)
                except asyncio.CancelledError:
                    await task
                    raise
                result.duracion_total_ms = round((perf_counter() - started) * 1000)
                logger.info('Extracción finalizada: páginas=%s duración_ms=%s estado=%s', result.numero_paginas, result.duracion_total_ms, result.estado)
                if normalizar:
                    pdf = directory / 'normalizado.pdf'
                    if not pdf.is_file() or pdf.stat().st_size > settings.max_pdf_bytes:
                        raise HTTPException(500, detail='Falta el PDF normalizado o supera el límite.')
                    package = io.BytesIO()
                    with zipfile.ZipFile(package, 'w', compression=zipfile.ZIP_STORED) as archive:
                        archive.writestr('resultado.json', result.model_dump_json())
                        archive.write(pdf, 'documento.pdf')
                    return Response(content=package.getvalue(), media_type='application/zip')
                return result
        except TimeoutError:
            raise HTTPException(408, detail='La recepción del archivo superó el tiempo permitido.')
        except OSError:
            logger.exception('No se pudo utilizar el almacenamiento temporal o iniciar el proceso.')
            raise HTTPException(503, detail='No se pudo preparar el archivo para su procesamiento.')
        finally:
            busy.release()

    @app.post('/evaluar')
    async def quality(request: Request):
        # Mismo bloqueo que OCR; lectura acotada incluso sin Content-Length.
        if not busy.acquire(blocking=False):
            raise HTTPException(503, detail='El procesador está ocupado.')
        try:
            body = bytearray()
            async with asyncio.timeout(15):
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > 250000:
                        raise HTTPException(413, detail='La evaluación supera el tamaño permitido.')
            try:
                data = QualityInput.model_validate_json(body)
                task = asyncio.create_task(asyncio.to_thread(evaluate, data))
                try:
                    return await asyncio.shield(task)
                except asyncio.CancelledError:
                    await task
                    raise
            except ValueError:
                raise HTTPException(422, detail='Referencia o variantes inválidas; máximo 10 000 caracteres por texto.')
        except TimeoutError:
            raise HTTPException(408, detail='La recepción superó el tiempo permitido.')
        finally:
            busy.release()

    @app.post('/evaluar')
    async def quality(request: Request):
        # Mismo bloqueo que OCR; lectura acotada incluso sin Content-Length.
        if not busy.acquire(blocking=False):
            raise HTTPException(503, detail='El procesador está ocupado.')
        try:
            body = bytearray()
            async with asyncio.timeout(15):
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > 250000:
                        raise HTTPException(413, detail='La evaluación supera el tamaño permitido.')
            try:
                data = QualityInput.model_validate_json(body)
                task = asyncio.create_task(asyncio.to_thread(evaluate, data))
                try:
                    return await asyncio.shield(task)
                except asyncio.CancelledError:
                    await task
                    raise
            except ValueError:
                raise HTTPException(422, detail='Referencia o variantes inválidas; máximo 10 000 caracteres por texto.')
        except TimeoutError:
            raise HTTPException(408, detail='La recepción superó el tiempo permitido.')
        finally:
            busy.release()

    return app


def app_factory():
    return create_app(load_settings())

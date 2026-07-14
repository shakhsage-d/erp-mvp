"""
core/error_handlers.py
------------------------
Bitta joyda: barcha turdagi xatolarni bir xil JSON formatga keltiradi:

    {
      "error": {
        "code": "not_found",
        "message": "Mahsulot topilmadi",
        ...qo'shimcha maydonlar (masalan available/requested)...
      }
    }

Bu funksiya faqat main.py'da BIR MARTA chaqiriladi (register_error_handlers(app)).
Yangi modul qo'shilganda bu faylga tegilmaydi — u avtomatik barcha
routerlar uchun ishlaydi.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError

logger = logging.getLogger("mikroerp")


def register_error_handlers(app: FastAPI) -> None:

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, **exc.extra}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Pydantic/FastAPI'ning o'zi ko'targan validatsiya xatolari
        (masalan majburiy maydon yo'qligi, noto'g'ri tur) ham bir xil
        formatga keltiriladi.

        MUHIM NOZIK JOY: agar xato maxsus @field_validator ichida
        ko'tarilgan bo'lsa (masalan "nomi bo'sh bo'lmasin"), Pydantic v2
        xato tafsilotiga (`ctx.error`) xom Python `ValueError` obyektini
        qo'shib qo'yadi — bu JSON'ga aylanmaydi va serverni 500 xatoga
        olib kelardi. Shuning uchun har bir xato yozuvini "tozalab"
        (`ctx.error`ni matnga aylantirib) qaytaramiz.
        """
        cleaned_errors = []
        for err in exc.errors():
            err = dict(err)
            ctx = err.get("ctx")
            if ctx and "error" in ctx:
                ctx = dict(ctx)
                ctx["error"] = str(ctx["error"])
                err["ctx"] = ctx
            cleaned_errors.append(err)

        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Yuborilgan ma'lumotlarda xatolik bor",
                    "fields": cleaned_errors,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Agar biror joyda (yoki eski kodda) hali ham to'g'ridan-to'g'ri
        HTTPException ko'tarilsa, baribir bir xil formatga o'raladi."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": "http_error", "message": str(exc.detail)}},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Kutilmagan (dasturchi bashorat qilmagan) xatolar uchun so'nggi
        himoya qatlami. Mijozga texnik tafsilot (stack trace, SQL xatosi
        va h.k.) HECH QACHON ko'rsatilmaydi — faqat serverning o'z
        logiga to'liq yoziladi, buni faqat siz ko'rasiz (Render Logs)."""
        logger.exception("Kutilmagan xato: %s %s", request.method, request.url)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Serverda kutilmagan xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.",
                }
            },
        )

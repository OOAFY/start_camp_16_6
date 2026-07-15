from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class OpenAIServiceError(Exception):
    """OpenAI API를 호출하거나 응답을 처리하지 못했을 때 발생합니다."""


def _build_error_response(status_code: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "data": None,
            "message": "요청을 처리할 수 없습니다.",
            "error": {"code": code, "detail": detail},
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(OpenAIServiceError)
    async def openai_exception_handler(_: Request, exc: OpenAIServiceError) -> JSONResponse:
        return _build_error_response(500, "OPENAI_API_ERROR", str(exc))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        detail = "; ".join(error.get("msg", "입력값이 올바르지 않습니다.") for error in exc.errors())
        return _build_error_response(422, "VALIDATION_ERROR", detail)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        code_map = {
            400: "INVALID_REQUEST",
            403: "INVALID_PASSWORD",
            404: "NOT_FOUND",
            422: "VALIDATION_ERROR",
        }
        code = code_map.get(exc.status_code, "INTERNAL_SERVER_ERROR")
        detail = str(exc.detail) if exc.detail else "요청을 처리할 수 없습니다."
        return _build_error_response(exc.status_code, code, detail)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, __: Exception) -> JSONResponse:
        return _build_error_response(500, "INTERNAL_SERVER_ERROR", "서버 오류가 발생했습니다.")

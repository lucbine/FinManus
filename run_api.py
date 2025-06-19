import json
import os
import threading
import time
import tomllib
import webbrowser
from functools import partial
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.apis import router
from app.logger import logger

app = FastAPI()

# 跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    # 请求前逻辑
    start_time = time.time()

    if request.method == "POST" and request.headers.get("content-type", "").startswith(
        "application/json"
    ):
        # 读取请求体内容
        body_bytes = await request.body()
        try:
            body = json.loads(body_bytes)
            logger.info(f"收到请求：{request.method} {request.url} 请求参数: {body}")
        except json.JSONDecodeError:
            logger.error(
                f"收到请求：{request.method} {request.url} 请求参数: {body_bytes}"
            )

        # 由于请求体只能读取一次，需重新注入 body
        request = Request(
            request.scope, receive=lambda: {"type": "http.request", "body": body_bytes}
        )

    # 执行请求处理
    response: Response = await call_next(request)

    # 请求后逻辑
    duration = time.time() - start_time

    logger.info(f"请求处理完成：{request.method} {request.url} 用时 {duration:.4f}s")

    return response


# 注册路由
app.include_router(router)


# 格式化验证错误
def format_validation_error(errors: list[Any]) -> Dict[str, Any]:
    """Format validation error messages"""
    formatted_errors = []
    for error in errors:
        loc = ".".join(str(x) for x in error["loc"])
        msg = error["msg"]
        formatted_errors.append({"field": loc, "message": msg})
    return {
        "code": 400,
        "message": "Request parameter validation failed",
        "errors": formatted_errors,
    }


# 请求参数验证错误
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    """Handle request parameter validation errors"""
    logger.exception(f"请求参数验证错误: {exc.errors()}")
    return JSONResponse(status_code=400, content=format_validation_error(exc.errors()))


# Pydantic 模型验证错误
@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(_: Request, exc: ValidationError):
    """Handle Pydantic model validation errors"""
    logger.exception(f"Pydantic 模型验证错误: {exc.errors()}")
    return JSONResponse(status_code=400, content=format_validation_error(exc.errors()))


# HTTP 异常
@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.exception(f"HTTP 异常: {exc.status_code} {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail},
    )


# 其他异常
@app.exception_handler(Exception)
async def generic_exception_handler(_: Request, exc: Exception):
    """Handle other exceptions"""
    logger.exception(f"其他异常: {exc}")
    return JSONResponse(
        status_code=500, content={"code": 500, "message": f"Server error: {str(exc)}"}
    )


# 打开本地浏览器
def open_local_browser(config):
    webbrowser.open_new_tab(
        f"http://{config.get('host', 'localhost')}:{config.get('port', 5172)}"
    )


# 加载配置
def load_config():
    try:
        config_path = Path(__file__).parent / "config" / "config.toml"

        if not config_path.exists():
            return {"host": "localhost", "port": 5172}

        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        return {"host": config["server"]["host"], "port": config["server"]["port"]}
    except FileNotFoundError:
        return {"host": "localhost", "port": 5172}
    except KeyError as e:
        print(
            f"The configuration file is missing necessary fields: {str(e)}, use default configuration"
        )
        return {"host": "localhost", "port": 5172}


# 启动 API 服务
if __name__ == "__main__":
    import uvicorn

    # 加载配置
    config = load_config()
    uvicorn.run(app, host=config["host"], port=config["port"])

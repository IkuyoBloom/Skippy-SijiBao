import asyncio
import base64
import json
import os
import ssl
from typing import Optional
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse
from ai_engine import stream_agri_ai

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# SSL配置
SSL_KEYFILE = os.getenv("SSL_KEYFILE", "key.pem")
SSL_CERTFILE = os.getenv("SSL_CERTFILE", "cert.pem")


def get_ssl_context():
    if os.path.exists(SSL_KEYFILE) and os.path.exists(SSL_CERTFILE):
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(SSL_CERTFILE, SSL_KEYFILE)
        return ssl_context
    return None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.post("/chat-stream")
async def chat_endpoint(
        request: Request,
        prompt: Optional[str] = Form(None),
        image: Optional[UploadFile] = File(None),
        audio: Optional[UploadFile] = File(None)
):
    if not prompt and not image and not audio:
        async def empty_generator():
            yield {"data": json.dumps({"type": "answer", "content": "您好像什么都没输入呢..."})}

        return EventSourceResponse(empty_generator())

    image_base64 = None
    if image:
        image_bytes = await image.read()
        MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
        if len(image_bytes) > MAX_IMAGE_SIZE:
            async def error_generator():
                yield {"data": json.dumps({"type": "error", "content": "图片文件过大，请控制在10MB以内"})}

            return EventSourceResponse(error_generator())
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    audio_base64 = None
    if audio:
        audio_bytes = await audio.read()
        MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10MB
        if len(audio_bytes) > MAX_AUDIO_SIZE:
            async def error_generator():
                yield {"data": json.dumps({"type": "error", "content": "音频文件过大，请控制在10MB以内"})}

            return EventSourceResponse(error_generator())
        if len(audio_bytes) > 0:
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    if not prompt:
        if image:
            safe_prompt = "【用户上传了一张图片】。"
        elif audio:
            safe_prompt = "【用户上传了一段语音，内容已完成转文字，可能包含方言结果】。"
        else:
            safe_prompt = "【用户上传了内容】。"
    else:
        safe_prompt = prompt

    async def event_generator():
        try:
            print(
                f"DEBUG: 开始处理请求，prompt: {safe_prompt[:50]}..., 有图片: {bool(image_base64)}, 有音频: {bool(audio_base64)}")

            async for chunk in stream_agri_ai(safe_prompt, image_base64, audio_base64):

                if await request.is_disconnected():
                    print("DEBUG: 客户端已断开，停止生成。")
                    break


                yield {
                    "data": json.dumps(chunk, ensure_ascii=False)
                }

                await asyncio.sleep(0.01)

            print("DEBUG: 请求处理完成")

        except Exception as e:
            print(f"ERROR: 处理请求时发生致命错误: {str(e)}")
            import traceback
            traceback.print_exc()
            yield {"data": json.dumps({"type": "error", "content": f"系统服务异常: {type(e).__name__}"},
                                      ensure_ascii=False)}

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    import uvicorn

    HOST = "127.0.0.1"
    PORT = 8000

    ssl_context = get_ssl_context()
    if ssl_context:
        print(f"--- 四季宝农技大脑已启动 (HTTPS) ---")
        uvicorn.run(app, host=HOST, port=PORT, ssl_certfile=SSL_CERTFILE, ssl_keyfile=SSL_KEYFILE)
    else:
        print(f"--- 四季宝农技大脑已启动 ---")
        print(f"访问地址: http://{HOST}:{PORT}")
        uvicorn.run(app, host=HOST, port=PORT)
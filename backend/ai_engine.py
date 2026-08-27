import asyncio
import base64
import hashlib
import hmac
import json
import re
import time
from datetime import datetime
from wsgiref.handlers import format_date_time
import requests
import websockets
from dotenv import load_dotenv
from openai import AsyncOpenAI
load_dotenv()

import os
import io


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_BIN_PATH = os.path.normpath(os.path.join(BASE_DIR, "bin"))


os.environ["PATH"] = FFMPEG_BIN_PATH + os.pathsep + os.environ["PATH"]

ffmpeg_exe = os.path.join(FFMPEG_BIN_PATH, "ffmpeg.exe")
ffprobe_exe = os.path.join(FFMPEG_BIN_PATH, "ffprobe.exe")

if not os.path.exists(ffmpeg_exe):
    print(f"[ERROR]")
else:
    print(f"[OK] {ffmpeg_exe}")


from pydub import AudioSegment
from pydub.utils import which

AudioSegment.converter = ffmpeg_exe
AudioSegment.ffprobe = ffprobe_exe

if which("ffmpeg") is None:
    print("[WARN]")

    import pydub.utils
    pydub.utils.get_encoder_name = lambda: ffmpeg_exe
api_key = os.getenv("DASHSCOPE_API_KEY")
qweather_key = os.getenv("QWEATHER_KEY")
xf_app_id = os.getenv("XFYUN_APP_ID")
xf_api_key = os.getenv("XFYUN_API_KEY")
xf_api_secret = os.getenv("XFYUN_API_SECRET")

client = AsyncOpenAI(
    api_key=api_key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


def get_comprehensive_weather(full_prompt: str) -> str:
    if not qweather_key: return ""
    match = re.search(r"地区：(.*?)[\|】\n]", full_prompt)
    if not match: return ""
    city_name = match.group(1).strip()
    search_name = re.sub(r"省|市|自治区|特别行政区|区|县", "", city_name)
    try:
        geo_url = "https://geoapi.qweather.com/v2/city/lookup"
        geo_resp = requests.get(geo_url, params={'location': search_name, 'key': qweather_key}, timeout=5)
        geo_data = geo_resp.json()
        if geo_data.get("code") != "200" or not geo_data.get("location"): return ""
        loc = geo_data['location'][0]
        city_id, actual_name = loc['id'], loc['name']

        n_data = requests.get('https://devapi.qweather.com/v7/weather/now',
                              params={'location': city_id, 'key': qweather_key}, timeout=5).json()
        f_data = requests.get('https://devapi.qweather.com/v7/weather/3d',
                              params={'location': city_id, 'key': qweather_key}, timeout=5).json()
        g_data = requests.get(f'https://devapi.qweather.com/v7/grid-weather/7d',
                              params={'location': city_id, 'key': qweather_key}, timeout=5).json()

        weather_context = f"\n--- 农事气象决策参考 ({actual_name}) ---\n"
        weather_context += f"状态码：实时={n_data.get('code', '?')} | 3天={f_data.get('code', '?')} | 7天={g_data.get('code', '?')}\n"
        weather_context += f"数据更新时间：{n_data.get('updateTime', '未知')}\n"
        fx_link = g_data.get('fxLink', '')
        if fx_link:
            weather_context += f"数据页面：{fx_link}\n"

        if n_data.get("code") == "200":
            now = n_data['now']
            weather_context += f"【当前实况】\n"
            weather_context += f"  天气：{str(now.get('text', '未知'))}，气温：{str(now.get('temp', '?'))}°C\n"
            weather_context += f"  湿度：{str(now.get('humidity', '?'))}%，风速：{str(now.get('windSpeed', '?'))}公里/小时（{str(now.get('windDir', ''))}，{str(now.get('wind360', '?'))}°）\n"
            weather_context += f"  大气压强：{str(now.get('pressure', '?'))}百帕\n"

        if f_data.get("code") == "200":
            weather_context += "【未来3天城市预报】\n"
            for day in f_data.get('daily', []):
                weather_context += f"  【{str(day.get('fxDate', '未知'))}】\n"
                weather_context += f"    白天：{str(day.get('textDay', '未知'))}，{str(day.get('tempMin', '?'))}~{str(day.get('tempMax', '?'))}°C\n"
                weather_context += f"    夜间：{str(day.get('textNight', '未知'))}，风力{str(day.get('windScaleDay', '?'))}级（{str(day.get('windDirDay', ''))}，{str(day.get('wind360Day', '?'))}°，{str(day.get('windSpeedDay', '?'))}公里/小时）\n"
                weather_context += f"    夜间风力：{str(day.get('windScaleNight', '?'))}级（{str(day.get('windDirNight', ''))}，{str(day.get('wind360Night', '?'))}°，{str(day.get('windSpeedNight', '?'))}公里/小时）\n"
                weather_context += f"    降水量：{str(day.get('precip', '?'))}毫米，湿度：{str(day.get('humidity', '?'))}%，气压：{str(day.get('pressure', '?'))}百帕\n"

        if g_data.get("code") == "200":
            weather_context += "【未来7天精细化网格预报】\n"
            for i, day in enumerate(g_data.get('daily', [])):
                weather_context += f"  【第{i+1}天 {str(day.get('fxDate', '未知'))}】\n"
                weather_context += f"    白天：{str(day.get('textDay', '未知'))}，{str(day.get('tempMin', '?'))}~{str(day.get('tempMax', '?'))}°C\n"
                weather_context += f"    夜间：{str(day.get('textNight', '未知'))}\n"
                weather_context += f"    白天风向：{str(day.get('wind360Day', '?'))}° {str(day.get('windDirDay', ''))}，风力{str(day.get('windScaleDay', '?'))}级，风速{str(day.get('windSpeedDay', '?'))}公里/小时\n"
                weather_context += f"    夜间风向：{str(day.get('wind360Night', '?'))}° {str(day.get('windDirNight', ''))}，风力{str(day.get('windScaleNight', '?'))}级，风速{str(day.get('windSpeedNight', '?'))}公里/小时\n"
                weather_context += f"    降水量：{str(day.get('precip', '?'))}毫米，湿度：{str(day.get('humidity', '?'))}%，气压：{str(day.get('pressure', '?'))}百帕\n"
            sources = g_data.get('refer', {}).get('sources', [])
            license_info = g_data.get('refer', {}).get('license', [])
            if sources:
                weather_context += f"数据来源：{', '.join(sources)}\n"
            if license_info:
                weather_context += f"数据许可：{', '.join(license_info)}\n"

        return weather_context
    except Exception as e:
        print(f"[ERROR] 天气获取失败: {e}")
        return ""


async def recognize_speech(audio_base64: str) -> str:
    if not audio_base64: return ""
    if "," in audio_base64: audio_base64 = audio_base64.split(",")[1]

    try:
        raw_audio_bytes = base64.b64decode(audio_base64)
        audio_file = io.BytesIO(raw_audio_bytes)
        audio_segment = AudioSegment.from_file(audio_file)
        audio_segment = audio_segment.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        audio_bytes = audio_segment.raw_data
        print(f"[DEBUG] 转码成功，PCM长度: {len(audio_bytes)}")
    except Exception as e:
        print(f"[ERROR] 音频转码失败: {e}。请确认 bin 文件夹下有 ffmpeg.exe")
        return ""

    host = "iat.cn-huabei-1.xf-yun.com"
    path = "/v1"
    now = datetime.now()
    date = format_date_time(time.mktime(now.timetuple()))
    signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
    signature_sha = hmac.new(xf_api_secret.encode('utf-8'), signature_origin.encode('utf-8'), hashlib.sha256).digest()
    signature_sha_base64 = base64.b64encode(signature_sha).decode('utf-8')
    auth_str = f'api_key="{xf_api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
    authorization = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
    wss_url = f"wss://{host}{path}?authorization={authorization}&date={date.replace(' ', '%20')}&host={host}"

    final_text = []

    try:
        async with websockets.connect(wss_url) as ws:
            async def send_audio():
                await ws.send(json.dumps({
                    "header": {"app_id": xf_app_id, "status": 0},
                    "parameter": {"iat": {"language": "zh_cn", "accent": "mulacc", "domain": "slm",
                                          "result": {"encoding": "utf8", "compress": "raw", "format": "json"}}},
                    "payload": {
                        "audio": {"encoding": "raw", "sample_rate": 16000, "channels": 1, "bit_depth": 16, "status": 0,
                                  "audio": base64.b64encode(audio_bytes[:1280]).decode('utf-8')}}
                }))
                offset = 1280
                while offset < len(audio_bytes):
                    chunk = audio_bytes[offset:offset + 1280]
                    status = 1 if (offset + 1280 < len(audio_bytes)) else 2
                    await ws.send(json.dumps({
                        "header": {"app_id": xf_app_id, "status": status},
                        "payload": {"audio": {"status": status, "audio": base64.b64encode(chunk).decode('utf-8')}}
                    }))
                    offset += 1280
                    await asyncio.sleep(0.02)

            async def receive_result():
                async for message in ws:
                    resp = json.loads(message)
                    if resp["header"]["code"] != 0:
                        print(f"[ERROR] 讯飞识别错误: {resp['header']['message']}")
                        break
                    payload = resp.get("payload", {}).get("result", {})
                    if payload:
                        res = json.loads(base64.b64decode(payload["text"]).decode('utf-8'))
                        for ws_obj in res.get("ws", []):
                            for cw_obj in ws_obj.get("cw", []):
                                final_text.append(cw_obj.get("w", ""))
                    if resp["header"]["status"] == 2:
                        break

            await asyncio.gather(send_audio(), receive_result())

    except Exception as e:
        print(f"[DEBUG] 语音识别通讯异常: {e}")

    return "".join(final_text)


async def stream_agri_ai(prompt: str, image_base64: str = None, audio_base64: str = None):
    try:
        nick_match = re.search(r"用户：(.*?)[\|】\n]", prompt)
        nickname = nick_match.group(1).strip() if nick_match else "农户"
        crops_match = re.search(r"种植：(.*?)[\|】\n]", prompt)
        crops = crops_match.group(1).strip() if crops_match else "作物"
        remarks_match = re.search(r"备注：(.*?)[\|】\n]", prompt)
        remarks = remarks_match.group(1).strip() if remarks_match else ""
        weather_info = get_comprehensive_weather(prompt)
        if weather_info:
            weather_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{weather_time}] [DEBUG] 天气信息获取成功:\n{weather_info}\n")
        clean_user_prompt = re.sub(r"【.*?】", "", prompt).strip()

        if audio_base64:
            print("[DEBUG] 正在进行语音识别...")
            speech_text = await recognize_speech(audio_base64)
            print(f"[DEBUG] 识别结果: '{speech_text}'")
            if speech_text:
                clean_user_prompt = f"{clean_user_prompt}\n[语音输入] {speech_text}"
                yield {"type": "transcript", "content": speech_text}
            elif not clean_user_prompt and not image_base64:
                yield {"type": "answer", "content": "四季宝没听清您的声音，能请您大声再说一遍吗？"}
                return

        weather_info_str = str(weather_info) if weather_info else ""
        
        system_content = f"""你是'四季宝'，一位专业的智能农业技术专家。你的核心使命是为中国农户提供精准、实用、及时的农技支持。

【角色定位】
- 身份：资深农业技术顾问，具备丰富的作物栽培、病虫害防治、土壤肥料、气象农事等专业知识
- 服务对象：农户{nickname}，主要种植{crops}
- 用户备注：{remarks if remarks else "无"}
- 服务风格：亲切易懂、务实高效、因地制宜

【核心能力】
1. 作物全周期管理：播种、育苗、移栽、田间管理、收获等各阶段技术指导
2. 病虫害诊断与防治：基于症状描述或图片识别病虫害，提供绿色防控方案
3. 气象农事决策：结合天气数据，给出灌溉、施肥、打药等农事活动建议
4. 土壤与营养管理：测土配方、肥料选择、施用时机与方法
5. 应急处理：旱涝、霜冻、风雹等灾害的预防和补救措施

【输出规范】
1. 结构清晰：使用标题、分点、表格等方式组织内容，便于农户快速获取关键信息
2. 语言通俗：避免过于学术化的术语，必要时解释专业词汇
3. 操作性强：给出具体的时间、用量、方法等可执行建议
4. 本地化适配：结合{weather_info_str}等环境信息，提供因地制宜的方案
5. 安全优先：农药使用严格遵守安全间隔期，优先推荐绿色防控技术

【多模态处理】
- 图片分析：仔细观察作物形态、病斑特征、虫害痕迹、土壤状况等视觉信息
- 语音输入：理解农户的口语化描述，提取关键症状和诉求
- 综合分析：结合文字、图像、环境数据做出全面判断

【思考原则】
1. 先分析后建议：充分理解问题本质，再给出解决方案
2. 多问少猜：信息不足时，主动询问关键细节（如发病时间、蔓延速度等）
3. 预防为主：不仅解决当前问题，更要提供预防复发的长期策略
4. 风险提示：明确指出潜在风险和注意事项

请基于以上定位，为农户提供专业、可靠的农业技术支持。"""
        messages = [{"role": "system", "content": system_content}]

        user_msg_content = [{"type": "text", "text": clean_user_prompt or "请分析这张图片的内容。"}]
        if image_base64:
            if "," in image_base64: image_base64 = image_base64.split(",")[1]
            user_msg_content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}})

        messages.append({"role": "user", "content": user_msg_content})

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("\n" + "="*60)
        print(f"[{timestamp}] 【发送给模型的完整提示词】")
        print("="*60)
        for msg in messages:
            print(f"\n[Role: {msg['role']}]")
            if isinstance(msg['content'], list):
                for item in msg['content']:
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            print(f"Text: {item['text']}")
                        elif item.get('type') == 'image_url':
                            print(f"Image: [base64 image data]")
            else:
                print(f"Content: {msg['content']}")
        print("\n" + "="*60 + "\n")

        request_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{request_time}] [DEBUG] 正在请求大模型...")
        completion = await client.chat.completions.create(
            model="qwen3.6-plus",
            messages=messages,
            extra_body={"enable_thinking": True},
            stream=True
        )

        async for chunk in completion:
            delta = chunk.choices[0].delta
            if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                yield {"type": "reasoning", "content": delta.reasoning_content}
            if hasattr(delta, "content") and delta.content:
                yield {"type": "answer", "content": delta.content}

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        yield {"type": "error", "content": f"服务出现了一点小状况: {str(e)}"}
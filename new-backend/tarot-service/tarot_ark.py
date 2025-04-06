from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

# 配置API密钥（推荐使用环境变量）
os.environ["ARK_API_KEY"] = "b8630f89-673f-4ebb-ac6f-821b95442cbf"  # 替换成你的实际密钥

app = FastAPI()

# CORS 中间件配置（允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法（包括 HEAD）
    allow_headers=["*"],
    expose_headers=["*"]
)

# 健康检查路由
@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Tarot Service is running"}

# 显式处理 HEAD 请求
@app.head("/")
async def head_root():
    return {"status": "ok"}

class TarotRequest(BaseModel):
    question: str
    card_name: str
    position: str

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def call_volcengine_api(system_prompt: str, user_prompt: str):
    """
    直接调用火山引擎豆包API的核心函数
    """
    try:
        # API配置
        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('ARK_API_KEY')}"
        }
        payload = {
            "model": "ep-20250311174845-dzj2f",  # 替换成你的模型ID
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 1,
            "top_p": 0.7,
            "max_tokens": 2025
        }

        # 发送请求
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # 自动处理HTTP错误
        
        # 解析响应
        return response.json()["choices"][0]["message"]["content"]
        
    except requests.exceptions.HTTPError as e:
        print(f"火山引擎API错误详情: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        print(f"API调用失败: {str(e)}")
        raise

@app.post("/api/tarot")
async def get_tarot_reading(request: TarotRequest):
    try:
        # 系统提示词
        system_prompt = """# Role: Tarot Master (STRICTLY ENGLISH ONLY)
You are an AI that MUST respond in **English only**. 
**Absolutely DO NOT use any Chinese characters** in your response.

## Core Task:
Interpret the tarot card strictly in English based on traditional tarot principles.

## Response Format:
[Card Meaning]
One clear English sentence describing the card's meaning.

[Current Situation]
Three distinct points in English explaining the current situation.
Each point should be clear and specific.

[Guidance]
Three practical recommendations in English.
Make them specific and actionable.

## Critical Rules:
1. Use ONLY English for all content
2. Format sections with square brackets [ ]
3. If any Chinese characters appear, the system will crash
4. Keep responses clear and direct
5. Use standard English terminology for tarot concepts"""

        # 用户提示词
        user_prompt = f"""**CRITICAL: RESPOND IN ENGLISH ONLY. CHINESE CHARACTERS ARE STRICTLY FORBIDDEN.**

Tarot Information:
- Card: {request.card_name}
- Position: {request.position}
- Question: {request.question}

Response Requirements:
1. Use clear, professional English only
2. Format all sections with [ ]
3. NO Chinese characters allowed
4. Structure your response as:
   [Card Meaning]
   [Current Situation]
   [Guidance]

Verification Steps:
1. Confirm all text is in English
2. Verify no Chinese characters are present
3. Check section formatting with [ ]
4. Ensure clarity and professionalism

IMPORTANT: Any Chinese characters will cause system failure."""

        # 调用API
        print("正在请求火山引擎API...")
        interpretation = call_volcengine_api(system_prompt, user_prompt)
        
        # 验证响应是否含中文
        if any('\u4e00' <= char <= '\u9fff' for char in interpretation):
            raise HTTPException(status_code=500, detail="响应包含中文字符")
        
        return {
            "card_name": request.card_name,
            "position": request.position,
            "interpretation": interpretation
        }
    except Exception as e:
        print("发生错误:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(
        "tarot_ark:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        workers=1,
        log_level="info",
        proxy_headers=True,
        forwarded_allow_ips="*"
    ) 
        proxy_headers=True,
        forwarded_allow_ips="*"
    ) 

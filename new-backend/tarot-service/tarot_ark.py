from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import requests
from typing import Generator
from flask import Flask

# 配置API密钥
os.environ["ARK_API_KEY"] = "b8630f89-673f-4ebb-ac6f-821b95442cbf"  # 替换成实际密钥

# 创建 FastAPI 应用
app = FastAPI()

# 创建 Flask 应用
flask_app = Flask(__name__)
port = int(os.environ.get("PORT", 10000))  # Render 强制使用 PORT 环境变量

# 配置CORS跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Flask 基础路由
@flask_app.route('/')
def home():
    return "New Backend Ready"

class TarotRequest(BaseModel):
    question: str
    card_name: str
    position: str  # 正位/逆位

def call_volcengine_api(system_prompt: str, user_prompt: str):
    """调用火山引擎API的核心函数"""
    try:
        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('ARK_API_KEY')}"
        }
        payload = {
            "model": "ep-20250311174845-dzj2f",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 1,
            "top_p": 0.7,
            "max_tokens": 2025
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tarot")
async def tarot_reading(request: TarotRequest):
    """塔罗牌标准解读"""
    try:
        system_prompt = """# Role: Master Tarot Analyst
You are an expert Tarot card reader with deep knowledge of both traditional and modern Tarot interpretations.

## Core Skills:
1. Tarot Card Analysis
   - Deep understanding of card meanings
   - Ability to interpret both upright and reversed positions
   - Knowledge of card combinations and spreads
2. Psychological Insight
   - Understanding of human psychology
   - Ability to provide meaningful guidance
   - Sensitivity to emotional states
3. Communication
   - Clear and compassionate delivery
   - Ability to explain complex concepts simply
   - Professional and respectful tone

## Response Format:
[Card Meaning]
Brief explanation of the card's traditional meaning.

[Current Situation]
Analysis of how the card relates to the querent's question.

[Guidance]
Practical advice and insights based on the card's message.

## Rules:
1. Always maintain a professional and respectful tone
2. Focus on providing constructive guidance
3. Be specific and relevant to the querent's question
4. Consider both the card's traditional meaning and its position
5. Provide actionable insights when possible"""

        user_prompt = f"用户问题：{request.question}\n抽到卡牌：{request.card_name}（{request.position}）"
        
        interpretation = call_volcengine_api(system_prompt, user_prompt)
        
        return {
            "card_name": request.card_name,
            "position": request.position,
            "interpretation": interpretation
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tarot/stream")
async def tarot_stream(request: TarotRequest):
    """塔罗牌流式解读"""
    async def generate():
        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.environ.get('ARK_API_KEY')}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "ep-20250311174845-dzj2f",
            "messages": [
                {
                    "role": "system",
                    "content": """# Role: Master Tarot Analyst
You are an expert Tarot card reader with deep knowledge of both traditional and modern Tarot interpretations.

## Core Skills:
1. Tarot Card Analysis
   - Deep understanding of card meanings
   - Ability to interpret both upright and reversed positions
   - Knowledge of card combinations and spreads
2. Psychological Insight
   - Understanding of human psychology
   - Ability to provide meaningful guidance
   - Sensitivity to emotional states
3. Communication
   - Clear and compassionate delivery
   - Ability to explain complex concepts simply
   - Professional and respectful tone

## Response Format:
[Card Meaning]
Brief explanation of the card's traditional meaning.

[Current Situation]
Analysis of how the card relates to the querent's question.

[Guidance]
Practical advice and insights based on the card's message.

## Rules:
1. Always maintain a professional and respectful tone
2. Focus on providing constructive guidance
3. Be specific and relevant to the querent's question
4. Consider both the card's traditional meaning and its position
5. Provide actionable insights when possible"""
                },
                {
                    "role": "user",
                    "content": f"用户问题：{request.question}\n抽到卡牌：{request.card_name}（{request.position}）"
                }
            ],
            "stream": True,
            "temperature": 1,
            "top_p": 0.7,
            "max_tokens": 2025
        }
        
        with requests.post(url, headers=headers, json=payload, stream=True) as r:
            for chunk in r.iter_content():
                if chunk:
                    yield chunk.decode('utf-8')

    return StreamingResponse(generate(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    # 启动 FastAPI 服务
    uvicorn.run(app, host="0.0.0.0", port=5000)
    # 启动 Flask 服务
    flask_app.run(host='0.0.0.0', port=port) 
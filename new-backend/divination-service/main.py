from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from flask import Flask, request, jsonify
from flask_cors import CORS

# 配置API密钥（推荐使用环境变量）
os.environ["ARK_API_KEY"] = "b8630f89-673f-4ebb-ac6f-821b95442cbf"  # 替换成你的实际密钥

app = FastAPI()

# 配置CORS跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

class DivinationRequest(BaseModel):
    method: str
    hexagram: str
    question: str

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def call_volcengine_api(system_prompt: str, user_prompt: str):
    """
    直接调用火山引擎豆包API的核心函数
    """
    try:
        # API配置（与curl示例一致）
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
        print(f"HTTP错误: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        print(f"API调用失败: {str(e)}")
        raise

@app.post("/api/interpret")
async def interpret(request: DivinationRequest):
    try:
        # 验证卦象数据
        hexagram_lines = [x for x in request.hexagram.split(',') if x]
        if len(hexagram_lines) != 6:
            raise HTTPException(status_code=400, detail="卦象数据不完整")

        # 系统提示词（保持原有逻辑）
        system_prompt = """# Role: Metaphysics Master (STRICTLY ENGLISH ONLY)
You are an AI that MUST respond in **English only**. 
**Absolutely DO NOT use any Chinese characters** in your response.

## Core Task:
Interpret the hexagram strictly in English based on I Ching principles.

## Response Format:
[Hexagram Summary]
One clear English sentence describing the overall fortune.

[Detailed Analysis]
Three distinct points in English explaining the hexagram's meaning.
Each point should be clear and specific.

[Actionable Advice]
Three practical recommendations in English.
Make them specific and actionable.

## Critical Rules:
1. Use ONLY English for all content
2. Format sections with square brackets [ ]
3. If any Chinese characters appear, the system will crash
4. Keep responses clear and direct
5. Use standard English terminology for I Ching concepts

## Language Enforcement:
- MUST use English only
- NO Chinese characters allowed
- NO mixed language content
- NO transliterated Chinese terms
- Use Western equivalents for all concepts

## Output Validation:
Before responding, verify that:
1. All text is in English
2. No Chinese characters are present
3. Sections use [ ] format
4. Content is clear and understandable"""

        # 用户提示词（保持原有逻辑）
        hexagram_description = '\n'.join([f"Line {i+1}: {'Yang' if line == '1' else 'Yin'}" for i, line in enumerate(hexagram_lines)])
        user_prompt = f"""**CRITICAL: RESPOND IN ENGLISH ONLY. CHINESE CHARACTERS ARE STRICTLY FORBIDDEN.**

Hexagram Information:
- Method: {request.method}
- Question: {request.question}

Hexagram Structure:
{hexagram_description}

Response Requirements:
1. Use clear, professional English only
2. Format all sections with [ ]
3. NO Chinese characters allowed
4. Structure your response as:
   [Hexagram Summary]
   [Detailed Analysis]
   [Actionable Advice]

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
            "hexagram_name": f"{request.method}",
            "interpretation": interpretation,
            "fortune_level": 3  # 默认值
        }
    except Exception as e:
        print("发生错误:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Flask 服务器配置
app = Flask(__name__)
CORS(app)

# 配置端口
port = int(os.environ.get("PORT", 10000))  # Render 强制使用 PORT 环境变量

@app.route('/')
def home():
    return "New Backend Ready"

@app.route('/api/tarot', methods=['POST'])
def tarot_reading():
    """塔罗牌标准解读"""
    try:
        data = request.get_json()
        question = data.get('question')
        card_name = data.get('card_name')
        position = data.get('position')

        if not all([question, card_name, position]):
            return jsonify({"error": "Missing required parameters"}), 400

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

        user_prompt = f"用户问题：{question}\n抽到卡牌：{card_name}（{position}）"
        
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
        interpretation = response.json()["choices"][0]["message"]["content"]
        
        return jsonify({
            "card_name": card_name,
            "position": position,
            "interpretation": interpretation
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tarot/stream', methods=['GET'])
def tarot_stream():
    """塔罗牌流式解读"""
    try:
        question = request.args.get('question')
        card_name = request.args.get('card_name')
        position = request.args.get('position')

        if not all([question, card_name, position]):
            return jsonify({"error": "Missing required parameters"}), 400

        def generate():
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
                        "content": f"用户问题：{question}\n抽到卡牌：{card_name}（{position}）"
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

        return app.response_class(generate(), mimetype='text/event-stream')
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)  # 必须绑定 0.0.0.0
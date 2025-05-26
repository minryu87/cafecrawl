import os
import pandas as pd
import time
from tqdm import tqdm
import requests

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")  # 실제 키로 교체 필요
MODEL = "gemini-2.0-flash"

def call_gemini_api(prompt: str, model: str) -> dict:
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ]
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        import json, re
        cleaned = text.strip()
        if cleaned.startswith('```'):
            cleaned = re.sub(r'^```[a-zA-Z]*', '', cleaned).strip()
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3].strip()
        return json.loads(cleaned)
    except Exception as e:
        return {"is_relevant": None, "reason": str(e)}

def create_relevance_prompt(post: str, query: str) -> str:
    return f"""
# 페르소나\n당신은 병원 카페글 분석 전문가 AI입니다. 아래 카페글이 실제로 '{query}'와 관련된 환자 질문/후기인지, 무관한지, 마케팅/도배성 글인지 판별해 주세요.\n\n# 지시사항\n- 글의 실제 맥락, 키워드, 문장 구조, 반복성, 자연스러움 등을 종합적으로 고려하세요.\n- 아래 항목만 JSON으로 반환하세요.\n\n```json\n{{\n  \"is_relevant\": 1,  // 1=관련, 0=무관, -1=마케팅/도배\n  \"reason\": \"\"       // 판별 근거를 간단히 서술\n}}\n```\n\n# 카페글:\n{post}\n"""

from datetime import datetime

def analyze_cafe_file(input_path: str, output_path: str, query: str, text_col: str = 'summary', sleep_sec: float = 1.2):
    df = pd.read_csv(input_path)
    results = []
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="카페글 관련도 분석", ncols=80):
        try:
            post = str(row.get(text_col, ''))
            prompt = create_relevance_prompt(post, query)
            result = call_gemini_api(prompt, MODEL)
            results.append(result)
        except Exception as e:
            results.append({"is_relevant": None, "reason": str(e)})
        time.sleep(sleep_sec)
    result_df = pd.DataFrame(results)
    merged = pd.concat([df, result_df], axis=1)
    merged.to_csv(output_path, index=False)
    print(f"분석 결과가 {output_path}에 저장되었습니다.")

if __name__ == "__main__":
    query = "대구 치과 추천"
    input_dir = "crawled_csv"
    output_dir = "analyzed_csv"
    os.makedirs(output_dir, exist_ok=True)
    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    query_str = query.replace(' ', '').replace('+', '')
    for fname in os.listdir(input_dir):
        if fname.endswith('.csv'):
            output_path = os.path.join(
                output_dir,
                f"analyzed_{query_str}_{now}_{fname}"
            )
            input_path = os.path.join(input_dir, fname)
            print(f"분석 시작: {input_path}")
            analyze_cafe_file(input_path, output_path, query)

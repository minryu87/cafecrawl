from fastapi import FastAPI, Query, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from typing import Optional, List
import pandas as pd
import shutil
from medilawyer_sales.hospital_cafe_crawl.server_host.python_app.cafe_crawler import crawl_cafe, get_driver, make_search_url, scroll_down, parse_li
from medilawyer_sales.hospital_cafe_crawl.server_host.python_app.cafe_text_analyzer import analyze_cafe_file, call_gemini_api, create_relevance_prompt
import time
from datetime import datetime
import traceback
import json

load_dotenv()

app = FastAPI()

# CORS 허용 (Gradio/HF Spaces 연동용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

@app.get("/")
def root():
    return {"message": "Cafe Crawl API 서버가 정상적으로 동작 중입니다."}

@app.get("/search-logs/")
def get_search_logs():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, search_query, period, min_li_count, requested_at, status, error_message
        FROM cafe_search_log
        ORDER BY requested_at DESC
        LIMIT 100
    """)
    logs = cur.fetchall()
    cur.close()
    conn.close()
    return {"logs": logs}

@app.get("/analysis-result/")
def get_analysis_result(search_log_id: int = Query(...)):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT user_name, title, date, summary, is_relevant, reason, link
        FROM cafe_analysis_result
        WHERE search_log_id = %s
        ORDER BY date_dt DESC NULLS LAST, id ASC
        LIMIT 2000
    """, (search_log_id,))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return {"data": data}

@app.post("/crawl")
def crawl_endpoint(query: str = Form(...), min_li_count: int = Form(100), period: str = Form('1y')):
    try:
        crawl_cafe(query, min_li_count=min_li_count, period=period)
        return {"status": "success", "message": "크롤링 완료"}
    except Exception as e:
        return {"status": "fail", "message": str(e)}

@app.post("/analyze")
async def analyze_endpoint(request: Request):
    try:
        body = await request.json()
        search_queries = body.get("search_queries", [])
        period = body.get("period", "1y")
        min_li_count = int(body.get("min_li_count", 100))
        if not search_queries:
            return {"status": "fail", "message": "search_queries 필수"}
        if isinstance(search_queries, str):
            search_queries = [search_queries]
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # 1. cafe_search_log insert
        cur.execute("""
            INSERT INTO cafe_search_log (search_query, period, min_li_count, requested_at, status)
            VALUES (%s, %s, %s, NOW(), %s) RETURNING id
        """, ("; ".join(search_queries), period, min_li_count, "pending"))
        search_log_id = cur.fetchone()["id"]
        conn.commit()
        all_results = []
        for query in search_queries:
            # 2. 크롤링 (메모리 내 DataFrame)
            # 기존 crawl_cafe는 파일 저장이므로, 크롤링 로직을 직접 이식/수정 필요
            # 아래는 간단화 예시 (실제 크롤링 함수에서 DataFrame 반환하도록 리팩토링 필요)
            driver = get_driver()
            url = make_search_url(query, period)
            driver.get(url)
            time.sleep(2)
            page_source = scroll_down(driver, min_li_count)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(page_source, 'html.parser')
            li_list = soup.select('div.api_subject_bx ul.lst_view li.bx._bx')
            data = []
            for li in li_list[:min_li_count]:
                data.append(parse_li(li))
            driver.quit()
            # 3. LLM 분석
            analyzed = []
            for row in data:
                post = str(row.get('summary', ''))
                prompt = create_relevance_prompt(post, query)
                result = call_gemini_api(prompt, model="gemini-2.0-flash")
                analyzed.append({
                    "user_name": row.get("user", ""),
                    "title": row.get("title", ""),
                    "date": row.get("date", ""),
                    "summary": row.get("summary", ""),
                    "is_relevant": result.get("is_relevant"),
                    "reason": result.get("reason"),
                    "link": row.get("link", "")
                })
            # 4. cafe_analysis_result bulk insert
            for row in analyzed:
                cur.execute("""
                    INSERT INTO cafe_analysis_result (search_log_id, user_name, title, date, summary, is_relevant, reason, link)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    search_log_id,
                    row["user_name"], row["title"], row["date"], row["summary"],
                    row["is_relevant"], row["reason"], row["link"]
                ))
            conn.commit()
            all_results.extend(analyzed)
        # 5. status update
        cur.execute("UPDATE cafe_search_log SET status=%s WHERE id=%s", ("success", search_log_id))
        conn.commit()
        cur.close()
        conn.close()
        # 6. 결과 반환
        return {
            "status": "success",
            "search_log_id": search_log_id,
            "data": [
                {
                    "user": r["user_name"],
                    "title": r["title"],
                    "date": r["date"],
                    "summary": r["summary"],
                    "relevance": r["is_relevant"],
                    "reason": r["reason"],
                    "link": r["link"]
                } for r in all_results
            ]
        }
    except Exception as e:
        # 실패시 status update
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("UPDATE cafe_search_log SET status=%s, error_message=%s WHERE id=currval('cafe_search_log_id_seq')", ("fail", str(e)))
            conn.commit()
            cur.close()
            conn.close()
        except:
            pass
        return {"status": "fail", "message": str(e), "trace": traceback.format_exc()}

@app.post("/upload-cafe-csv/")
def upload_cafe_csv(file: UploadFile = File(...)):
    try:
        save_dir = "uploaded_csv"
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"status": "success", "file_path": file_path}
    except Exception as e:
        return {"status": "fail", "message": str(e)}

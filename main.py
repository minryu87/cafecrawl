from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from typing import Optional

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

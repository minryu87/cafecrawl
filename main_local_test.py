from fastapi import FastAPI, Query, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
import os
# import psycopg2  # 주석 처리
# import psycopg2.extras  # 주석 처리
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

# def get_conn(): # 주석 처리
#     return psycopg2.connect(
#         host=os.getenv("DB_HOST"),
#         port=os.getenv("DB_PORT"),
#         dbname=os.getenv("DB_NAME"),
#         user=os.getenv("DB_USER"),
#         password=os.getenv("DB_PASSWORD")
#     )

@app.get("/")
def root():
    return {"message": "Cafe Crawl API 서버가 정상적으로 동작 중입니다. (로컬 테스트 버전)"}

@app.get("/search-logs/")
def get_search_logs():
    # conn = get_conn() # 주석 처리
    # cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # 주석 처리
    # cur.execute("""
    #     SELECT id, search_query, period, min_li_count, requested_at, status, error_message
    #     FROM cafe_search_log
    #     ORDER BY requested_at DESC
    #     LIMIT 100
    # """) # 주석 처리
    # logs = cur.fetchall() # 주석 처리
    # cur.close() # 주석 처리
    # conn.close() # 주석 처리
    # return {"logs": logs} # 주석 처리
    return {"message": "DB 연동 제외된 로컬 테스트 버전입니다."}


@app.get("/analysis-result/")
def get_analysis_result(search_log_id: int = Query(...)):
    # conn = get_conn() # 주석 처리
    # cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # 주석 처리
    # cur.execute("""
    #     SELECT user_name, title, date, summary, is_relevant, reason, link
    #     FROM cafe_analysis_result
    #     WHERE search_log_id = %s
    #     ORDER BY date_dt DESC NULLS LAST, id ASC
    #     LIMIT 2000
    # """, (search_log_id,)) # 주석 처리
    # data = cur.fetchall() # 주석 처리
    # cur.close() # 주석 처리
    # conn.close() # 주석 처리
    # return {"data": data} # 주석 처리
    return {"message": f"DB 연동 제외된 로컬 테스트 버전입니다. search_log_id: {search_log_id} 요청"}


@app.post("/crawl")
def crawl_endpoint(query: str = Form(...), min_li_count: int = Form(100), period: str = Form('1y')):
    try:
        crawl_cafe(query, min_li_count=min_li_count, period=period) # 이 함수는 파일 저장 기반, 필요시 수정
        return {"status": "success", "message": "크롤링 완료 (파일 저장)"}
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
        
        # conn = get_conn() # 주석 처리
        # cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # 주석 처리
        # # 1. cafe_search_log insert
        # cur.execute("""
        #     INSERT INTO cafe_search_log (search_query, period, min_li_count, requested_at, status)
        #     VALUES (%s, %s, %s, NOW(), %s) RETURNING id
        # """, ("; ".join(search_queries), period, min_li_count, "pending")) # 주석 처리
        # search_log_id = cur.fetchone()["id"] # 주석 처리
        # conn.commit() # 주석 처리
        search_log_id = 0 # 임시 search_log_id

        all_results = []
        for query in search_queries:
            # 2. 크롤링 (메모리 내 DataFrame)
            driver = get_driver()
            url = make_search_url(query, period)
            driver.get(url)
            time.sleep(2) # 페이지 로딩 대기
            page_source = scroll_down(driver, min_li_count)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(page_source, 'html.parser')
            li_list = soup.select('div.api_subject_bx ul.lst_view li.bx._bx')
            
            data = []
            for li_element in li_list[:min_li_count]: # min_li_count 만큼만 가져오도록 수정
                parsed_data = parse_li(li_element)
                if parsed_data: # parse_li가 None을 반환하지 않는 경우에만 추가
                     data.append(parsed_data)
            driver.quit()
            
            # 3. LLM 분석
            analyzed = []
            for row in data:
                # summary가 없거나 None일 경우 빈 문자열로 처리
                post_summary = str(row.get('summary', '')) if row.get('summary') is not None else ''
                
                # title이 없거나 None일 경우 빈 문자열로 처리
                post_title = str(row.get('title', '')) if row.get('title') is not None else ''

                # user가 없거나 None일 경우 빈 문자열로 처리
                user_name = str(row.get('user', '')) if row.get('user') is not None else ''
                
                # date가 없거나 None일 경우 빈 문자열로 처리
                post_date = str(row.get('date', '')) if row.get('date') is not None else ''

                # link가 없거나 None일 경우 빈 문자열로 처리
                post_link = str(row.get('link', '')) if row.get('link') is not None else ''


                # prompt 생성 시 title과 summary를 합쳐서 전달하거나, 둘 중 하나만 사용
                # 여기서는 title + summary를 사용
                full_post_content = f"제목: {post_title}\n내용: {post_summary}"

                prompt = create_relevance_prompt(full_post_content, query)
                # Gemini API 호출 전 로그 (디버깅용)
                # print(f"Gemini API 호출. Query: {query}, Post: {full_post_content[:100]}...")
                
                # 실제 Gemini API 호출 (비용 발생 가능성 있음)
                # 현재는 로컬 테스트이므로, 실제 API 호출을 건너뛰고 더미 데이터 반환하도록 수정 가능
                # gemini_response = call_gemini_api(prompt, model="gemini-1.5-flash-latest") # 모델명 확인 필요

                # --- 로컬 테스트용 더미 Gemini 응답 ---
                gemini_response = {"is_relevant": 1, "reason": "테스트용 더미 응답"}
                # --- 로컬 테스트용 더미 Gemini 응답 ---

                analyzed.append({
                    "user_name": user_name,
                    "title": post_title,
                    "date": post_date,
                    "summary": post_summary, # 원본 요약 저장
                    "is_relevant": gemini_response.get("is_relevant"),
                    "reason": gemini_response.get("reason"),
                    "link": post_link
                })
            
            # 4. cafe_analysis_result bulk insert # 주석 처리
            # for row in analyzed:
            #     cur.execute("""
            #         INSERT INTO cafe_analysis_result (search_log_id, user_name, title, date, summary, is_relevant, reason, link)
            #         VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            #     """, (
            #         search_log_id,
            #         row["user_name"], row["title"], row["date"], row["summary"],
            #         row["is_relevant"], row["reason"], row["link"]
            #     ))
            # conn.commit() # 주석 처리
            all_results.extend(analyzed)
        
        # 5. status update # 주석 처리
        # cur.execute("UPDATE cafe_search_log SET status=%s WHERE id=%s", ("success", search_log_id))
        # conn.commit() # 주석 처리
        # cur.close() # 주석 처리
        # conn.close() # 주석 처리
        
        # 6. 결과 반환
        return {
            "status": "success",
            "search_log_id": search_log_id, # 임시 ID
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
        # 실패시 status update # 주석 처리
        # try:
        #     conn = get_conn()
        #     cur = conn.cursor()
        #     cur.execute("UPDATE cafe_search_log SET status=%s, error_message=%s WHERE id=currval('cafe_search_log_id_seq')", ("fail", str(e)))
        #     conn.commit()
        #     cur.close()
        #     conn.close()
        # except:
        #     pass
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

# 로컬 테스트를 위해 uvicorn 직접 실행 코드 추가 (Postman 테스트용)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
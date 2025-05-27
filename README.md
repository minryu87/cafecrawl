# Cafe Crawl API 서버 (elestio용)

- FastAPI 기반의 네이버 카페글 크롤링/분석/DB저장 API 서버 예시
- elestio의 Python+PostgreSQL 서비스에 배포할 때 사용

## 주요 파일
- main.py : FastAPI 엔드포인트 구현 (크롤링, 분석, DB저장)
- cafe_crawler.py : 네이버 카페 크롤러
- cafe_text_analyzer.py : Gemini 기반 텍스트 관련도 분석기
- requirements.txt : 의존성 패키지

## 실행 예시
```
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 기본 엔드포인트
- GET / : 서버 상태 확인
- GET /search-logs/ : 최근 검색 이력 100개 조회
- GET /analysis-result/?search_log_id= : 특정 검색 이력의 분석 결과 조회
- POST /crawl : 검색어(query), 기간(period), 최소글수(min_li_count) 입력받아 카페글 크롤링
  - 입력: form-data (query, period, min_li_count)
  - 출력: {"status": "success", "message": "크롤링 완료"}
- POST /analyze : 검색어(query)와 카페글 CSV 업로드 시 관련도 분석
  - 입력: form-data (query, input_csv)
  - 출력: {"status": "success", "output_csv": "분석결과경로"}
- POST /upload-cafe-csv/ : 카페글 CSV 업로드
  - 입력: form-data (file)
  - 출력: {"status": "success", "file_path": "저장경로"}


  ## 수정 확인
  
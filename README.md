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
- POST /crawl : 검색어/기간 등 입력받아 카페글 크롤링
- POST /analyze : 텍스트/리스트 업로드 시 관련도 분석
- POST /upload-cafe-csv/ : 카페글 CSV 업로드 및 처리

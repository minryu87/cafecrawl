# Cafe Crawl API 서버 (elestio용)

- FastAPI 기반의 카페글 분석/수집 API 서버 예시
- elestio의 Python+PostgreSQL 서비스에 배포할 때 사용

## 주요 파일
- main.py : FastAPI 엔드포인트 구현
- requirements.txt : 의존성 패키지

## 실행 예시
```
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 기본 엔드포인트
- GET / : 서버 상태 확인
- POST /upload-cafe-csv/ : 카페글 CSV 업로드 및 처리

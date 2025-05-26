from fastapi import FastAPI, UploadFile, File
import pandas as pd
from typing import List

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Cafe Crawl API 서버가 정상적으로 동작 중입니다."}

@app.post("/upload-cafe-csv/")
async def upload_cafe_csv(file: UploadFile = File(...)):
    df = pd.read_csv(file.file)
    # TODO: 분석/DB 저장/후처리 등 추가 구현
    return {"rows": len(df), "columns": list(df.columns)}

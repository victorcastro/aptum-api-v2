from fastapi import FastAPI

app = FastAPI(title="Aptum Agent")


@app.get("/health")
def health():
    return {"status": "ok"}

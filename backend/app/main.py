from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import router
from config import settings

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(router)

@app.head('/health')
@app.get('/health')
def health_check():
    return 'ok'
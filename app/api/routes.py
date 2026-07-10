from fastapi import APIRouter

router = APIRouter()


@router.get("/hello", tags=["example"])
def hello() -> dict[str, str]:
    return {"message": "Hello from Mahsol API"}

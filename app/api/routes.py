from fastapi import APIRouter

from app.core.models import SignUpRequest

router = APIRouter()



@router.get("/hello", tags=["example"])
def hello() -> dict[str, str]:
    return {"message": "Hello from Mahsol API"}


@router.post("/signup", tags=["auth"])
def sign_up(request: SignUpRequest) -> dict[str, str]:
    # TODO do one way encryption of password and save user to database
    print(f"Sign up: email={request.email} password={request.password} role={request.role.value}")
    return {"message": f"Received sign up for {request.email} as {request.role.value}"}

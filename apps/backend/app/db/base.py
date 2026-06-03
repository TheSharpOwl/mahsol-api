from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models import user, land_info, conversation, message, report  # noqa: F401, E402

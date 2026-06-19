from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

Base = declarative_base()
SessionLocal = scoped_session(sessionmaker(autoflush=False, autocommit=False))

_engine = None


def init_engine(database_url, echo=False):
    global _engine
    _engine = create_engine(database_url, echo=echo, future=True)
    SessionLocal.configure(bind=_engine)
    return _engine


def get_engine():
    return _engine


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

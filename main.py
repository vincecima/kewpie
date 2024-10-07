import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, schemas
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)
from fastapi_users_db_sqlalchemy import (
    SQLAlchemyBaseUserTableUUID,
    SQLAlchemyUserDatabase,
)
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "sqlite+aiosqlite:///kewpie.db"
SECRET = "SECRET"


class Settings(BaseSettings):
    otel_service_name: str
    otel_exporter_endpoint: str
    honeycomb_api_key: str


class Base(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    pass


def configure_tracing(
    app: FastAPI, serviceName: str, endpoint: str, honeycomb_api_key: str
):
    FastAPIInstrumentor.instrument_app(app)
    resource = Resource(
        attributes={
            SERVICE_NAME: serviceName,
        }
    )
    traceProvider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint=f"{endpoint}/v1/traces",
            headers={"x-honeycomb-team": honeycomb_api_key},
        )
    )
    # TODO: Can we do this on traceProvider init?
    traceProvider.add_span_processor(processor)
    trace.set_tracer_provider(traceProvider)

    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(
            endpoint=f"{endpoint}/v1/metrics",
            # TODO: Not setting x-honeycomb-dataset results in a new dataset even though
            # Resource is passed
            headers={
                "x-honeycomb-team": honeycomb_api_key,
                "x-honeycomb-dataset": serviceName,
            },
        ),
    )
    meterProvider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meterProvider)


engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


# TODO: Replace with actual migrations before deploying
async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)


cookie_transport = CookieTransport()


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_login(
        self,
        user: User,
        request: Optional[Request] = None,
        response: Optional[Response] = None,
    ):
        if response is None:
            return
        else:
            response.status_code = 303
            response.headers["Location"] = "/"


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


class UserRead(schemas.BaseUser[uuid.UUID]):
    pass


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass


fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)
current_user = fastapi_users.current_user(optional=True)

settings = Settings()
app = FastAPI(lifespan=lifespan)
configure_tracing(
    app,
    settings.otel_service_name,
    settings.otel_exporter_endpoint,
    settings.honeycomb_api_key,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/cookie",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request, user: User = Depends(current_user)):
    if user:
        return RedirectResponse("/home")
    else:
        return RedirectResponse("/login")


@app.get("/home", response_class=HTMLResponse)
def read_home(request: Request, user: User = Depends(current_user)):
    return templates.TemplateResponse(request=request, name="home.html")


@app.get("/login", response_class=HTMLResponse)
def read_login(request: Request, user: User = Depends(current_user)):
    return templates.TemplateResponse(request=request, name="login.html")

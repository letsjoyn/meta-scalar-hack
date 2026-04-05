import os

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:  # pragma: no cover
    raise ImportError(
        "openenv is required. Install dependencies with: pip install -e ."
    ) from e


os.environ.setdefault("ENABLE_WEB_INTERFACE", "true")

try:
    from ..models import SupportOpsAction, SupportOpsObservation
    from .support_ops_environment import SupportOpsEnvironment
except ImportError:
    from models import SupportOpsAction, SupportOpsObservation
    from server.support_ops_environment import SupportOpsEnvironment


app = create_app(
    SupportOpsEnvironment,
    SupportOpsAction,
    SupportOpsObservation,
    env_name="support_ops_env",
    max_concurrent_envs=2,
)


def main(host: str = "0.0.0.0", port: int = 8000) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()

"""
Friday MCP Server entry point.
Run with: python server/server.py
"""

import json
import os

import anyio
import uvicorn
from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response

from friday.app.computer.exceptions import ComputerError
from friday.app.agent_console import get_console_greeting, get_console_snapshot, send_console_message
from friday.app.agent_console.schemas import ConsoleChatRequest
from friday.app.computer.router.routes import execute_computer_action, observe_computer, plan_computer, run_computer_cycle
from friday.app.computer.schemas.requests import ExecuteRequest, ObserveRequest, PlanRequest, RunRequest
from friday.app.facebook.exceptions import (
    FacebookConfigurationError,
    FacebookWebhookSignatureError,
    FacebookWebhookVerificationError,
)
from friday.app.facebook.router.routes import receive_messenger_webhook, verify_webhook_subscription
from friday.app.facebook.schemas.requests import ReceiveWebhookRequest, VerifyWebhookRequest
from friday.config import config
from friday.prompts import register_all_prompts
from friday.resources import register_all_resources
from friday.tools import register_all_tools

# Create the MCP server instance.
mcp = FastMCP(
    name=config.SERVER_NAME,
    instructions=(
        "You are FRIDAY, a Tony Stark-inspired AI assistant. "
        "Use the available tools to help the user. "
        "Respond in concise, accurate, useful English."
    ),
)

# Register tools, prompts, and resources.
register_all_tools(mcp)
register_all_prompts(mcp)
register_all_resources(mcp)


async def _read_json_payload(request: Request) -> dict:
    raw_body = await request.body()
    if not raw_body:
        return {}
    try:
        return json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON payload.") from exc


async def _load_model(request: Request, model_cls):
    payload = await _read_json_payload(request)
    return model_cls.model_validate(payload)


@mcp.custom_route("/facebook/webhook", methods=["GET"], name="facebook-webhook-verify")
async def facebook_webhook_verify(request: Request) -> Response:
    try:
        response = verify_webhook_subscription(
            VerifyWebhookRequest(
                mode=request.query_params.get("hub.mode", ""),
                verify_token=request.query_params.get("hub.verify_token", ""),
                challenge=request.query_params.get("hub.challenge", ""),
            )
        )
    except FacebookWebhookVerificationError as exc:
        return PlainTextResponse(str(exc), status_code=403)
    except FacebookConfigurationError as exc:
        return PlainTextResponse(str(exc), status_code=500)

    return PlainTextResponse(response.challenge, status_code=200)


@mcp.custom_route("/facebook/webhook", methods=["POST"], name="facebook-webhook-ingest")
async def facebook_webhook_ingest(request: Request) -> Response:
    try:
        raw_body = (await request.body()).decode("utf-8")
        payload = json.loads(raw_body or "{}")
        signature = request.headers.get("x-hub-signature-256")
        response = receive_messenger_webhook(
            ReceiveWebhookRequest(
                payload=payload,
                signature=signature,
                raw_body=raw_body,
            )
        )
    except json.JSONDecodeError:
        return JSONResponse({"ok": False, "message": "Invalid JSON payload."}, status_code=400)
    except FacebookWebhookSignatureError as exc:
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=403)
    except FacebookWebhookVerificationError as exc:
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=400)
    except FacebookConfigurationError as exc:
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=500)

    return JSONResponse(
        {
            "ok": response.accepted,
            "stored_event_count": response.stored_event_count,
            "stored_message_count": response.stored_message_count,
            "stored_notification_count": response.stored_notification_count,
            "message": response.message,
        },
        status_code=200,
    )


@mcp.custom_route("/computer/observe", methods=["POST"], name="computer-observe")
async def computer_observe(request: Request) -> Response:
    try:
        response = observe_computer(await _load_model(request, ObserveRequest))
    except ValueError as exc:
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=400)
    except ValidationError as exc:
        return JSONResponse({"ok": False, "message": "Invalid observe payload.", "details": exc.errors()}, status_code=422)
    except ComputerError as exc:
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=400)

    return JSONResponse(response.model_dump(by_alias=True, mode="json"), status_code=200)


@mcp.custom_route("/computer/plan", methods=["POST"], name="computer-plan")
async def computer_plan(request: Request) -> Response:
    try:
        response = plan_computer(await _load_model(request, PlanRequest))
    except ValueError as exc:
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=400)
    except ValidationError as exc:
        return JSONResponse({"ok": False, "message": "Invalid plan payload.", "details": exc.errors()}, status_code=422)
    except ComputerError as exc:
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=400)

    return JSONResponse(response.model_dump(by_alias=True, mode="json"), status_code=200)


@mcp.custom_route("/computer/execute", methods=["POST"], name="computer-execute")
async def computer_execute(request: Request) -> Response:
    try:
        response = execute_computer_action(await _load_model(request, ExecuteRequest))
    except ValueError as exc:
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=400)
    except ValidationError as exc:
        return JSONResponse({"ok": False, "message": "Invalid execute payload.", "details": exc.errors()}, status_code=422)
    except ComputerError as exc:
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=400)

    return JSONResponse(response.model_dump(by_alias=True, mode="json"), status_code=200)


@mcp.custom_route("/computer/run", methods=["POST"], name="computer-run")
async def computer_run(request: Request) -> Response:
    try:
        response = run_computer_cycle(await _load_model(request, RunRequest))
    except ValueError as exc:
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=400)
    except ValidationError as exc:
        return JSONResponse({"ok": False, "message": "Invalid run payload.", "details": exc.errors()}, status_code=422)
    except ComputerError as exc:
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=400)

    return JSONResponse(response.model_dump(by_alias=True, mode="json"), status_code=200)


@mcp.custom_route("/agent/console", methods=["GET"], name="agent-console")
async def agent_console(_: Request) -> Response:
    return JSONResponse(get_console_snapshot(), status_code=200)


@mcp.custom_route("/agent/chat", methods=["POST"], name="agent-chat")
async def agent_chat(request: Request) -> Response:
    try:
        response = send_console_message(await _load_model(request, ConsoleChatRequest))
    except ValueError as exc:
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=400)
    except ValidationError as exc:
        return JSONResponse({"ok": False, "message": "Invalid chat payload.", "details": exc.errors()}, status_code=422)

    return JSONResponse(response, status_code=200)


@mcp.custom_route("/agent/greeting", methods=["GET"], name="agent-greeting")
async def agent_greeting(_: Request) -> Response:
    return JSONResponse(await get_console_greeting(), status_code=200)


async def _run_sse() -> None:
    app = mcp.sse_app()
    config = uvicorn.Config(
        app,
        host=os.getenv("FRIDAY_MCP_HOST", mcp.settings.host),
        port=int(os.getenv("FRIDAY_MCP_PORT", str(mcp.settings.port))),
        log_level=mcp.settings.log_level.lower(),
        http="h11",
    )
    server = uvicorn.Server(config)
    await server.serve()


def main() -> None:
    anyio.run(_run_sse)


if __name__ == "__main__":
    main()

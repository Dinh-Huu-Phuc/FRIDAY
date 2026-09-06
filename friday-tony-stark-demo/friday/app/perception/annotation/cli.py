from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import UUID

from friday.app.perception.annotation import (
    AnnotationBox,
    AnnotationError,
    AnnotationSource,
    AnnotationStatus,
    get_annotation_service,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="friday-vision-annotate",
        description="Create and review Grounding DINO annotation proposals.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    propose = commands.add_parser("propose", help="Annotate a local image.")
    propose.add_argument("--image", required=True, type=Path)
    propose.add_argument("--labels", required=True, nargs="+")

    propose_camera = commands.add_parser(
        "propose-camera",
        help="Annotate the current FRIDAY camera keyframe.",
    )
    propose_camera.add_argument("--labels", required=True, nargs="+")
    propose_camera.add_argument(
        "--api-url",
        default=_default_api_url(),
        help="Running FRIDAY API base URL.",
    )

    listing = commands.add_parser("list", help="List annotation proposals.")
    listing.add_argument(
        "--status",
        choices=[item.value for item in AnnotationStatus],
    )
    commands.add_parser("summary", help="Show review queue counts.")

    show = commands.add_parser("show", help="Show one annotation proposal.")
    show.add_argument("proposal_id", type=UUID)

    correct = commands.add_parser(
        "correct",
        help="Replace boxes using a reviewed JSON array.",
    )
    correct.add_argument("proposal_id", type=UUID)
    correct.add_argument("--boxes", required=True, type=Path)
    correct.add_argument("--note", default=None)

    approve = commands.add_parser("approve", help="Approve and export a proposal.")
    approve.add_argument("proposal_id", type=UUID)
    approve.add_argument("--note", default=None)

    reject = commands.add_parser("reject", help="Reject a proposal.")
    reject.add_argument("proposal_id", type=UUID)
    reject.add_argument("--reason", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "propose-camera":
        try:
            print(_to_json(_propose_camera_via_api(args.api_url, args.labels)))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise SystemExit(f"Annotation command failed: {exc}") from exc
        return

    service = get_annotation_service()
    try:
        if args.command == "propose":
            result = service.propose_from_image(args.image, tuple(args.labels))
        elif args.command == "list":
            selected = AnnotationStatus(args.status) if args.status else None
            result = service.list(selected)
        elif args.command == "summary":
            result = service.summary()
        elif args.command == "show":
            result = service.get(args.proposal_id)
        elif args.command == "correct":
            result = service.correct(
                args.proposal_id,
                boxes=_load_boxes(args.boxes),
                review_note=args.note,
            )
        elif args.command == "approve":
            result = service.approve(args.proposal_id, review_note=args.note)
        else:
            result = service.reject(args.proposal_id, args.reason)
    except (AnnotationError, OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Annotation command failed: {exc}") from exc
    print(_to_json(result))


def _load_boxes(path: Path) -> tuple[AnnotationBox, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise TypeError("The boxes file must contain a JSON array.")
    return tuple(
        AnnotationBox(
            label=item["label"],
            confidence=item.get("confidence", 1.0),
            x1=item["x1"],
            y1=item["y1"],
            x2=item["x2"],
            y2=item["y2"],
            source=AnnotationSource.HUMAN,
        )
        for item in payload
    )


def _to_json(value) -> str:
    if isinstance(value, list):
        payload = [item.model_dump(mode="json") for item in value]
    elif isinstance(value, dict):
        payload = value
    else:
        payload = value.model_dump(mode="json")
    return json.dumps(payload, indent=2)


def _propose_camera_via_api(api_url: str, labels: list[str]) -> dict:
    endpoint = f"{api_url.rstrip('/')}/api/v1/vision-annotations/proposals/camera"
    request = Request(
        endpoint,
        data=json.dumps({"labels": labels}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=180) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("FRIDAY returned an invalid annotation response.")
    return payload


def _default_api_url() -> str:
    configured = (os.getenv("FRIDAY_LOCAL_API_URL") or "").strip()
    if configured:
        return configured
    port = (os.getenv("FRIDAY_API_PORT") or "8001").strip()
    return f"http://127.0.0.1:{port}"


if __name__ == "__main__":
    main()

from datetime import datetime, timedelta, timezone
import hmac
from json import JSONDecodeError
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.websockets import WebSocketDisconnect

from venus_protocol.schemas.commands import (
    CommandResult,
    NodeCommand,
    OpenApplicationCommand,
    OpenProjectCommand,
    OpenUrlCommand,
)
from venus_protocol.schemas.connections import NodeHello

from features.auth.dependencies import require_owner
from features.commands.result_registry import (
    CommandResultRegistry,
    get_command_result_registry,
)
from features.commands.dependencies import get_command_record_repository
from features.commands.models.command_record import CommandRecord
from features.commands.repository import (
    ApprovalExpiredError,
    CommandNotDispatchedError,
    CommandRecordRepository,
)
from features.commands.schemas import (
    ApprovalDecision,
    ProposeCommandRequest,
    ProposeProjectRequest,
    ProposeTextRequest,
    ProposeUrlRequest,
)
from features.commands.text_parser import (
    SEARCH_SITES,
    CommandTextError,
    ParsedCommand,
    SearchSite,
    parse_command_text,
)
from features.nodes.connection_registry import (
    NodeConnectionRegistry,
    get_connection_registry,
)
from features.settings.dependencies import get_settings_repository
from features.settings.repository import SettingsRepository
from features.shortcuts.dependencies import get_shortcut_repository
from features.shortcuts.models.site_shortcut import SiteShortcut
from features.shortcuts.repository import ShortcutRepository
from config import CoreSettings, get_settings


router = APIRouter()

@router.get("/nodes", dependencies=[Depends(require_owner)])
async def list_connected_nodes(
    registry: Annotated[
        NodeConnectionRegistry,
        Depends(get_connection_registry),
    ],
):
    return {"device_ids": registry.connected_device_ids()}


@router.get("/nodes/{device_id}/connection", dependencies=[Depends(require_owner)])
async def get_node_connection_status(
    device_id: str,
    registry: Annotated[
        NodeConnectionRegistry,
        Depends(get_connection_registry),
    ],
):
    return {
        "device_id": device_id,
        "connected": registry.get(device_id) is not None,
    }


@router.get("/nodes/{device_id}/apps", dependencies=[Depends(require_owner)])
async def list_node_apps(
    device_id: str,
    registry: Annotated[
        NodeConnectionRegistry,
        Depends(get_connection_registry),
    ],
):
    apps = registry.apps_for(device_id)

    if apps is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node is not connected",
        )

    return {"device_id": device_id, "apps": [app.model_dump() for app in apps]}


@router.get("/nodes/{device_id}/projects", dependencies=[Depends(require_owner)])
async def list_node_projects(
    device_id: str,
    registry: Annotated[
        NodeConnectionRegistry,
        Depends(get_connection_registry),
    ],
):
    projects = registry.projects_for(device_id)

    if projects is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node is not connected",
        )

    return {"device_id": device_id, "projects": projects}


@router.websocket("/nodes/connect")
async def connect_node(
    websocket: WebSocket,
    settings: Annotated[CoreSettings, Depends(get_settings)],
    registry: Annotated[
        NodeConnectionRegistry,
        Depends(get_connection_registry),
    ],
    result_registry: Annotated[
        CommandResultRegistry,
        Depends(get_command_result_registry),
    ],
    command_records: Annotated[
        CommandRecordRepository,
        Depends(get_command_record_repository),
    ],
):
    authorization = websocket.headers.get("authorization", "")
    expected_authorization = f"Bearer {settings.dev_node_token}"

    # Compare secrets safely even when an attacker controls the header.
    if not hmac.compare_digest(authorization, expected_authorization):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    try:
        hello_payload = await websocket.receive_json()
        hello = NodeHello.model_validate(hello_payload)
    except WebSocketDisconnect:
        return
    except (JSONDecodeError, KeyError, ValidationError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await registry.register(hello.device_id, websocket, hello.apps, hello.projects)

    try:
        # Confirm the device only; echoing hundreds of apps back is useless
        await websocket.send_json({"device_id": hello.device_id})

        while True:
            try:
                result_payload = await websocket.receive_json()
                result = CommandResult.model_validate(result_payload)
            except WebSocketDisconnect:
                return
            except (JSONDecodeError, KeyError, ValidationError):
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

            try:
                accepted = result_registry.accept_result(
                    result,
                    hello.device_id,
                    websocket,
                    persist=lambda accepted_result: command_records.complete(
                        command_id=accepted_result.command_id,
                        state=accepted_result.status,
                        detail=accepted_result.detail,
                        completed_at=datetime.now(timezone.utc),
                    ),
                )
            except (SQLAlchemyError, LookupError, CommandNotDispatchedError):
                # No confirmed result is published and no command is replayed.
                # Core's later timeout/recovery policy owns the unknown outcome.
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
                return

            if not accepted:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

    finally:
        await registry.unregister(hello.device_id, websocket)


async def approve_and_dispatch(
    command: NodeCommand,
    registry: NodeConnectionRegistry,
    result_registry: CommandResultRegistry,
    command_records: CommandRecordRepository,
) -> dict:
    websocket = registry.get(command.device_id)

    if websocket is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Node is not connected",
        )

    # Mark it dispatched before Node can receive the command.
    try:
        command_records.decide_approval(
            command.command_id,
            approved=True,
            decided_at=datetime.now(timezone.utc),
        )
    except ApprovalExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Command has expired",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Command is not awaiting approval",
        ) from exc
    result_registry.expect(command, websocket)
    await websocket.send_json(command.model_dump(mode="json"))

    return command.model_dump(mode="json")


async def propose(
    command: NodeCommand,
    registry: NodeConnectionRegistry,
    result_registry: CommandResultRegistry,
    command_records: CommandRecordRepository,
    settings_repository: SettingsRepository,
) -> dict:
    command_records.create(record_from_command(command))

    # Full mode (D-34): apps, links and project folders are all low-risk.
    if settings_repository.get_mode() == "full":
        return await approve_and_dispatch(
            command, registry, result_registry, command_records,
        )
    return command.model_dump(mode="json")


@router.post("/nodes/{device_id}/commands", dependencies=[Depends(require_owner)])
async def propose_command(
    device_id: str,
    request: ProposeCommandRequest,
    command_records: Annotated[
        CommandRecordRepository,
        Depends(get_command_record_repository),
    ],
    registry: Annotated[
        NodeConnectionRegistry,
        Depends(get_connection_registry),
    ],
    result_registry: Annotated[
        CommandResultRegistry,
        Depends(get_command_result_registry),
    ],
    settings_repository: Annotated[
        SettingsRepository,
        Depends(get_settings_repository),
    ],
):
    apps = registry.apps_for(device_id)

    if apps is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Node is not connected",
        )

    # Only apps this PC reported can be proposed
    if request.application_id not in {app.app_id for app in apps}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Application is not on this PC",
        )

    command = OpenApplicationCommand(
        command_id=uuid4(),
        device_id=device_id,
        application_id=request.application_id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )

    return await propose(
        command, registry, result_registry, command_records, settings_repository,
    )


@router.post(
    "/nodes/{device_id}/commands/open-url",
    dependencies=[Depends(require_owner)],
)
async def propose_url_command(
    device_id: str,
    request: ProposeUrlRequest,
    command_records: Annotated[
        CommandRecordRepository,
        Depends(get_command_record_repository),
    ],
    registry: Annotated[
        NodeConnectionRegistry,
        Depends(get_connection_registry),
    ],
    result_registry: Annotated[
        CommandResultRegistry,
        Depends(get_command_result_registry),
    ],
    settings_repository: Annotated[
        SettingsRepository,
        Depends(get_settings_repository),
    ],
):
    if registry.apps_for(device_id) is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Node is not connected",
        )

    command = OpenUrlCommand(
        command_id=uuid4(),
        device_id=device_id,
        url=request.url,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )

    return await propose(
        command, registry, result_registry, command_records, settings_repository,
    )


@router.post(
    "/nodes/{device_id}/commands/open-project",
    dependencies=[Depends(require_owner)],
)
async def propose_project_command(
    device_id: str,
    request: ProposeProjectRequest,
    command_records: Annotated[
        CommandRecordRepository,
        Depends(get_command_record_repository),
    ],
    registry: Annotated[
        NodeConnectionRegistry,
        Depends(get_connection_registry),
    ],
    result_registry: Annotated[
        CommandResultRegistry,
        Depends(get_command_result_registry),
    ],
    settings_repository: Annotated[
        SettingsRepository,
        Depends(get_settings_repository),
    ],
):
    projects = registry.projects_for(device_id)

    if projects is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Node is not connected",
        )

    # Only folders this PC reported can be proposed; the Node re-checks too
    if request.project_name not in projects:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Project is not on this PC",
        )

    command = OpenProjectCommand(
        command_id=uuid4(),
        device_id=device_id,
        project_name=request.project_name,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )

    return await propose(
        command, registry, result_registry, command_records, settings_repository,
    )


@router.post(
    "/nodes/{device_id}/commands/text",
    dependencies=[Depends(require_owner)],
)
async def propose_text_command(
    device_id: str,
    request: ProposeTextRequest,
    command_records: Annotated[
        CommandRecordRepository,
        Depends(get_command_record_repository),
    ],
    registry: Annotated[
        NodeConnectionRegistry,
        Depends(get_connection_registry),
    ],
    result_registry: Annotated[
        CommandResultRegistry,
        Depends(get_command_result_registry),
    ],
    settings_repository: Annotated[
        SettingsRepository,
        Depends(get_settings_repository),
    ],
    shortcuts: Annotated[
        ShortcutRepository,
        Depends(get_shortcut_repository),
    ],
):
    apps = registry.apps_for(device_id)
    projects = registry.projects_for(device_id)

    if apps is None or projects is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Node is not connected",
        )

    try:
        parsed = parse_command_text(
            request.text, apps, projects, search_sites(shortcuts.list_all()),
        )
    except CommandTextError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    # Text like "a.b:99999" passes the parser but is not a valid link.
    try:
        command = command_from_parsed(parsed, device_id)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="That link doesn't look right",
        ) from exc

    response = await propose(
        command, registry, result_registry, command_records, settings_repository,
    )
    response["label"] = parsed.label
    return response


def record_from_command(command: NodeCommand) -> CommandRecord:
    # Mirror of command_from_record: each kind saves its own target column.
    if isinstance(command, OpenUrlCommand):
        return CommandRecord(
            command_id=command.command_id,
            device_id=command.device_id,
            application_id=None,
            expires_at=command.expires_at,
            kind="open_url",
            url=str(command.url),
        )
    if isinstance(command, OpenProjectCommand):
        return CommandRecord(
            command_id=command.command_id,
            device_id=command.device_id,
            application_id=None,
            expires_at=command.expires_at,
            kind="open_project",
            project_name=command.project_name,
        )
    return CommandRecord(
        command_id=command.command_id,
        device_id=command.device_id,
        application_id=command.application_id,
        expires_at=command.expires_at,
    )


def command_from_record(record: CommandRecord, expires_at: datetime) -> NodeCommand:
    # The record remembers the kind so approval rebuilds the same command.
    if record.kind == "open_url":
        return OpenUrlCommand(
            command_id=record.command_id,
            device_id=record.device_id,
            url=record.url,
            expires_at=expires_at,
        )
    if record.kind == "open_project":
        return OpenProjectCommand(
            command_id=record.command_id,
            device_id=record.device_id,
            project_name=record.project_name,
            expires_at=expires_at,
        )
    return OpenApplicationCommand(
        command_id=record.command_id,
        device_id=record.device_id,
        application_id=record.application_id,
        expires_at=expires_at,
    )


def command_from_parsed(parsed: ParsedCommand, device_id: str) -> NodeCommand:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    if parsed.application_id is not None:
        return OpenApplicationCommand(
            command_id=uuid4(),
            device_id=device_id,
            application_id=parsed.application_id,
            expires_at=expires_at,
        )
    if parsed.project_name is not None:
        return OpenProjectCommand(
            command_id=uuid4(),
            device_id=device_id,
            project_name=parsed.project_name,
            expires_at=expires_at,
        )
    return OpenUrlCommand(
        command_id=uuid4(),
        device_id=device_id,
        url=parsed.url,
        expires_at=expires_at,
    )


def search_sites(shortcuts: list[SiteShortcut]) -> dict[str, SearchSite]:
    # The owner's shortcuts go on top, so one called "youtube" replaces ours.
    sites = dict(SEARCH_SITES)
    for shortcut in shortcuts:
        sites[shortcut.keyword] = SearchSite(
            label=shortcut.label,
            home_url=shortcut.home_url,
            search_url=shortcut.search_url,
        )
    return sites


@router.post("/commands/{command_id}/approval", dependencies=[Depends(require_owner)])
async def decide_command_approval(
    command_id: UUID,
    decision: ApprovalDecision,
    registry: Annotated[
        NodeConnectionRegistry,
        Depends(get_connection_registry),
    ],
    result_registry: Annotated[
        CommandResultRegistry,
        Depends(get_command_result_registry),
    ],
    command_records: Annotated[
        CommandRecordRepository,
        Depends(get_command_record_repository),
    ],
):
    record = command_records.get(command_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Command not found",
        )

    if record.state != "awaiting_approval":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Command is not awaiting approval",
        )

    expires_at = record.expires_at

    # SQLite drops timezone information in tests; PostgreSQL keeps it.
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Command has expired",
        )

    if not decision.approved:
        try:
            command_records.decide_approval(
                command_id,
                approved=False,
                decided_at=datetime.now(timezone.utc),
            )
        except ApprovalExpiredError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Command has expired",
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Command is not awaiting approval",
            ) from exc

        return {"command_id": str(command_id), "status": "denied"}

    command = command_from_record(record, expires_at)
    return await approve_and_dispatch(
        command, registry, result_registry, command_records,
    )

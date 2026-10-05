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

from features.auth.dependencies import require_owner, require_owner_or_node
from features.chat.dependencies import get_chat_provider
from features.chat.prompt import build_instructions
from features.chat.provider import ChatProvider
from features.chat.schemas import ChatRequest
from features.conversations.dependencies import get_conversation_repository
from features.conversations.repository import ConversationRepository
from features.memories.dependencies import get_memory_repository
from features.memories.repository import MemoryRepository
from features.memories.rule import memory_from_message
from features.personalities.dependencies import get_personality_repository
from features.personalities.repository import PersonalityRepository
from features.projects.dependencies import get_project_repository
from features.projects.repository import ProjectRepository
from features.projects.router import require_open_project
from features.voice.live import LiveVoice, get_live_voice
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
    NotUnderstoodError,
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


async def propose_parsed(
    parsed: ParsedCommand,
    device_id: str,
    registry: NodeConnectionRegistry,
    result_registry: CommandResultRegistry,
    command_records: CommandRecordRepository,
    settings_repository: SettingsRepository,
) -> dict:
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

    return await propose_parsed(
        parsed, device_id, registry, result_registry, command_records, settings_repository,
    )


@router.post("/nodes/{device_id}/chat", dependencies=[Depends(require_owner_or_node)])
async def chat(
    device_id: str,
    request: ChatRequest,
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
    provider: Annotated[ChatProvider, Depends(get_chat_provider)],
    conversations: Annotated[
        ConversationRepository,
        Depends(get_conversation_repository),
    ],
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
    personalities: Annotated[
        PersonalityRepository,
        Depends(get_personality_repository),
    ],
    memories: Annotated[MemoryRepository, Depends(get_memory_repository)],
    live: Annotated[LiveVoice, Depends(get_live_voice)],
):
    if request.conversation_id is not None and not conversations.exists(
        request.conversation_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    new_in_project = request.conversation_id is None and request.project_id is not None
    if new_in_project:
        require_open_project(projects, request.project_id)

    apps = registry.apps_for(device_id)
    # VS Code folders on the PC; not the same thing as chat projects.
    folders = registry.projects_for(device_id)

    if apps is None or folders is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Node is not connected",
        )

    # Core holds the history: the saved lines before this one.
    history = []
    if request.conversation_id is not None:
        history = conversations.recent_turns(request.conversation_id)
    # Your line is saved now, before Luna answers: the web (polling) shows it
    # while she is still thinking, e.g. after "Hey Venus" on the PC.
    conversation_id = request.conversation_id
    if conversation_id is None:
        conversation_id = conversations.create(request.message, request.project_id)
    conversations.add_message(conversation_id, "user", request.message)
    if request.voice:
        live.voice_chat(str(conversation_id))

    full_mode = settings_repository.get_mode() == "full"

    def instructions() -> str:
        return chat_instructions(
            request, conversations, projects, personalities,
            list(search_sites(shortcuts.list_all())),
            folders,
            memories,
            full_mode,
        )

    # Rules answer first; the brain only gets what they don't understand.
    answer = None
    to_open: list[ParsedCommand] = []  # commands to propose, in order
    facts: list[str] = []  # facts saved during this message
    failures: list[str] = []  # why a command Luna chose can't run
    brain_line = None  # Luna's line written with her tool call
    fact = memory_from_message(request.message)
    if fact is not None:
        facts.append(memories.create(fact).text)
    else:
        try:
            to_open.append(parse_command_text(
                request.message, apps, folders, search_sites(shortcuts.list_all()),
            ))
        except NotUnderstoodError:
            brain = await provider.reply(request.message, history, instructions())
            facts = [memories.create(fact).text for fact in brain.memories]
            if brain.commands:
                brain_line = brain.text
            # Luna picked tools: run each choice through the same parser.
            for text in brain.commands:
                try:
                    to_open.append(parse_command_text(
                        text, apps, folders, search_sites(shortcuts.list_all()),
                    ))
                except CommandTextError as exc:
                    failures.append(str(exc))
            if not to_open and not failures:
                if not facts:
                    answer = {"type": "reply", "reply": brain.text, "actions": []}
                elif brain.text:
                    # Her own answer stays; the facts are actions.
                    answer = memory_answer(facts, brain.text)
            elif not to_open and not facts:
                # "No app called ..." is an answer in a chat.
                answer = {"type": "reply", "reply": " ".join(failures), "actions": []}
        except CommandTextError as exc:
            # "Which one: ...?" and "No app called ..." are answers in a chat.
            answer = {"type": "reply", "reply": str(exc), "actions": []}

    if answer is None:
        # Each command is its own record with its own Approve.
        proposals = [
            await propose_parsed(
                parsed, device_id, registry, result_registry, command_records,
                settings_repository,
            )
            for parsed in to_open
        ]
        labels = [proposal["label"] for proposal in proposals]
        done, fallback = action_summary(labels, facts, failures, full_mode)
        if brain_line and proposals and not facts and not failures:
            # She already said it with the tool call; saves a second model call.
            line = brain_line
        else:
            # One line from Luna about everything she did.
            line = await luna_line(provider, request.message, instructions(), done, fallback)
        actions = [
            {"kind": "command", "command_id": proposal["command_id"], "label": proposal["label"]}
            for proposal in proposals
        ] + [{"kind": "memory", "text": fact} for fact in facts]
        if proposals:
            # The web waits on the newest command before unlocking the input.
            answer = {"type": "command", **proposals[-1], "reply": line, "actions": actions}
        else:
            answer = {"type": "reply", "reply": line, "actions": actions}

    conversations.add_message(
        conversation_id, "assistant", answer["reply"] or "", answer["actions"],
    )
    return {**answer, "conversation_id": str(conversation_id)}


def chat_instructions(
    request: ChatRequest,
    conversations: ConversationRepository,
    projects: ProjectRepository,
    personalities: PersonalityRepository,
    sites: list[str],
    folders: list[str],
    memories: MemoryRepository,
    full_mode: bool = True,
) -> str:
    # Looked up on every message, so a chat moved into a project
    # follows that project's instructions from its next message.
    project_id = request.project_id
    if request.conversation_id is not None:
        project_id = conversations.get(request.conversation_id).project_id
    project = projects.get(project_id) if project_id is not None else None
    personality = personalities.active()
    return build_instructions(
        personality.text if personality is not None else None,
        project.instructions if project is not None else None,
        sites,
        folders,
        [memory.text for memory in memories.newest(50)],
        approve_first=not full_mode,
    )


def memory_answer(facts: list[str], reply: str) -> dict:
    # Kept by Core itself: no PC command, nothing to approve.
    return {
        "type": "reply",
        "reply": reply,
        "actions": [{"kind": "memory", "text": fact} for fact in facts],
    }


def and_list(items: list[str]) -> str:
    # ["A", "B", "C"] -> "A, B and C"
    if len(items) < 2:
        return "".join(items)
    return f"{', '.join(items[:-1])} and {items[-1]}"


def action_summary(
    labels: list[str], facts: list[str], failures: list[str], full_mode: bool,
) -> tuple[str, str]:
    # What Luna is told she did, and the plain line if she can't answer.
    done: list[str] = []
    fallback: list[str] = []
    if labels:
        if full_mode:
            done.append(f"You are opening {and_list(labels)} on the owner's PC right now.")
        else:
            done.append(
                f"You want to open {and_list(labels)} on the owner's PC and are "
                "waiting for them to press Approve below."
            )
        fallback.append(f"On it: {', '.join(labels)}")
    if facts:
        done.append(f"You just saved this about the owner: {'; '.join(facts)}.")
        fallback.append(f"Saved: {', '.join(facts)}")
    if failures:
        done.append(f"You couldn't do this part: {' '.join(failures)}")
        fallback.append(" ".join(failures))
    return " ".join(done), ". ".join(fallback)


async def luna_line(
    provider: ChatProvider,
    message: str,
    instructions: str,
    done: str,
    fallback: str,
) -> str:
    # Luna tells the owner what she did, in the active personality.
    line = await provider.say(
        message,
        f"{instructions}\n\n{done} Tell the owner in one short sentence. "
        "Don't repeat the details shown below your reply.",
    )
    return line or fallback


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

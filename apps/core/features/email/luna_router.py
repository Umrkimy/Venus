import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from features.auth.dependencies import require_owner
from features.chat.dependencies import get_chat_provider
from features.chat.provider import ChatProvider
from features.email import assistant
from features.email.dependencies import MailBackend, get_email_account, get_mail_backend
from features.email.mailbox import MailError
from features.email.models.email_account import EmailAccount
from features.email.router import fetch, mail_problem
from features.email.schemas import DraftRequest, MessageUid, NewDraftRequest

# Luna's help with mail: summaries and drafts. Nothing here can send.
router = APIRouter(prefix="/email", dependencies=[Depends(require_owner)])

NO_LUNA = "Luna needs an AI model to do that. Add one in Settings, AI model."


@router.post("/accounts/{account_id}/messages/{uid}/summary")
async def summarize_message(
    uid: MessageUid,
    backend: Annotated[MailBackend, Depends(get_mail_backend)],
    provider: Annotated[ChatProvider, Depends(get_chat_provider)],
):
    text = await assistant.summarize(provider, await fetch(backend, uid))
    if not text:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=NO_LUNA)
    return {"summary": text}


@router.post("/accounts/{account_id}/summary")
async def summarize_inbox(
    backend: Annotated[MailBackend, Depends(get_mail_backend)],
    provider: Annotated[ChatProvider, Depends(get_chat_provider)],
):
    try:
        found = await backend.inbox(30)
    except MailError as exc:
        raise mail_problem(exc) from exc
    if not found:
        return {"groups": []}
    text = await assistant.summarize_inbox(provider, found)
    if not text:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=NO_LUNA)
    groups = assistant.overview_groups(text, found)
    # If Luna didn't answer in the expected shape, show her words as they are.
    return {"groups": groups} if groups is not None else {"groups": [], "summary": text}


@router.post("/accounts/{account_id}/messages/{uid}/draft")
async def draft_reply(
    uid: MessageUid,
    body: DraftRequest,
    account: Annotated[EmailAccount, Depends(get_email_account)],
    backend: Annotated[MailBackend, Depends(get_mail_backend)],
    provider: Annotated[ChatProvider, Depends(get_chat_provider)],
):
    """Luna's reply, for the owner to read and change. Nothing is sent."""
    message = await fetch(backend, uid)
    text = await assistant.draft_reply(provider, message, account.display_name, body.tone, body.wish)
    if not text:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=NO_LUNA)
    subject = message.subject if re.match(r"(?i)^re:", message.subject) else f"Re: {message.subject}"
    return {"to": [message.sender_address], "cc": [], "subject": subject, "body": text, "reply_to": uid}


@router.post("/accounts/{account_id}/draft")
async def draft_new(
    body: NewDraftRequest,
    account: Annotated[EmailAccount, Depends(get_email_account)],
    provider: Annotated[ChatProvider, Depends(get_chat_provider)],
):
    text = await assistant.draft_new(provider, account.display_name, body.to, body.wish, body.tone)
    if not text:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=NO_LUNA)
    return {"body": text}

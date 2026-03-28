"""
Processing logs and run history endpoints for users.

Users can view the full history of processing runs and per-email logs
for their own mailboxes.  Admin equivalents live in admin.py.
"""

from __future__ import annotations

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.database_models import (
    MailAccount,
    ProcessingLog,
    ProcessingRun,
    User,
)
from app.models.schemas import (
    PaginatedProcessingLogsResponse,
    PaginatedProcessingRunsResponse,
    ProcessingLogDetailResponse,
    ProcessingRunDetailResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _paginate(total: int, page: int, page_size: int) -> dict:
    pages = max(1, math.ceil(total / page_size)) if total else 1
    return {"total": total, "page": page, "page_size": page_size, "pages": pages}


# ---------------------------------------------------------------------------
# Processing Runs (all accounts belonging to the current user)
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=PaginatedProcessingRunsResponse,
    summary="List processing runs for the current user",
)
async def list_processing_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    account_id: Optional[int] = Query(None, description="Filter by mail account ID"),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by run status (completed, failed, partial_failure, running)",
    ),
    has_emails: Optional[bool] = Query(
        None,
        description="When true, only return runs that fetched at least one email",
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return a paginated list of processing runs for all mail accounts owned by
    the authenticated user, optionally filtered by account, status, or whether
    any emails were fetched (has_emails=true reduces log noise by hiding empty
    polling cycles).
    """
    # Base query: join with MailAccount to enforce ownership
    base = (
        select(ProcessingRun, MailAccount.name, MailAccount.email_address)
        .join(MailAccount, ProcessingRun.mail_account_id == MailAccount.id)
        .where(MailAccount.user_id == current_user.id)  # type: ignore[arg-type]
    )

    if account_id is not None:
        base = base.where(ProcessingRun.mail_account_id == account_id)
    if status_filter:
        base = base.where(ProcessingRun.status == status_filter)
    if has_emails is True:
        base = base.where(ProcessingRun.emails_fetched > 0)

    # Total count
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    offset = (page - 1) * page_size
    rows = (
        await db.execute(
            base.order_by(ProcessingRun.started_at.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).all()

    items = [
        ProcessingRunDetailResponse(
            id=row.ProcessingRun.id,  # type: ignore[arg-type]
            mail_account_id=row.ProcessingRun.mail_account_id,  # type: ignore[arg-type]
            started_at=row.ProcessingRun.started_at,  # type: ignore[arg-type]
            completed_at=row.ProcessingRun.completed_at,  # type: ignore[arg-type]
            duration_seconds=row.ProcessingRun.duration_seconds,  # type: ignore[arg-type]
            emails_fetched=row.ProcessingRun.emails_fetched,  # type: ignore[arg-type]
            emails_forwarded=row.ProcessingRun.emails_forwarded,  # type: ignore[arg-type]
            emails_failed=row.ProcessingRun.emails_failed,  # type: ignore[arg-type]
            status=row.ProcessingRun.status,  # type: ignore[arg-type]
            error_message=row.ProcessingRun.error_message,  # type: ignore[arg-type]
            account_name=row.name,
            account_email=row.email_address,
        )
        for row in rows
    ]

    return PaginatedProcessingRunsResponse(
        items=items, **_paginate(total, page, page_size)  # type: ignore[arg-type]
    )


@router.get(
    "/{run_id}",
    response_model=ProcessingRunDetailResponse,
    summary="Get a single processing run",
)
async def get_processing_run(
    run_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return details for a single processing run owned by the current user."""
    row = (
        await db.execute(
            select(ProcessingRun, MailAccount.name, MailAccount.email_address)
            .join(MailAccount, ProcessingRun.mail_account_id == MailAccount.id)
            .where(
                ProcessingRun.id == run_id,
                MailAccount.user_id == current_user.id,  # type: ignore[arg-type]
            )
        )
    ).one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Processing run not found"
        )

    return ProcessingRunDetailResponse(
        id=row.ProcessingRun.id,  # type: ignore[arg-type]
        mail_account_id=row.ProcessingRun.mail_account_id,  # type: ignore[arg-type]
        started_at=row.ProcessingRun.started_at,  # type: ignore[arg-type]
        completed_at=row.ProcessingRun.completed_at,  # type: ignore[arg-type]
        duration_seconds=row.ProcessingRun.duration_seconds,  # type: ignore[arg-type]
        emails_fetched=row.ProcessingRun.emails_fetched,  # type: ignore[arg-type]
        emails_forwarded=row.ProcessingRun.emails_forwarded,  # type: ignore[arg-type]
        emails_failed=row.ProcessingRun.emails_failed,  # type: ignore[arg-type]
        status=row.ProcessingRun.status,  # type: ignore[arg-type]
        error_message=row.ProcessingRun.error_message,  # type: ignore[arg-type]
        account_name=row.name,
        account_email=row.email_address,
    )


@router.get(
    "/{run_id}/logs",
    response_model=PaginatedProcessingLogsResponse,
    summary="Get per-email logs for a processing run",
)
async def get_run_logs(
    run_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the detailed per-email log entries recorded during a specific
    processing run.  Ownership is verified by joining with MailAccount.
    """
    # Verify the run belongs to this user
    run_row = (
        await db.execute(
            select(ProcessingRun)
            .join(MailAccount, ProcessingRun.mail_account_id == MailAccount.id)
            .where(
                ProcessingRun.id == run_id,
                MailAccount.user_id == current_user.id,  # type: ignore[arg-type]
            )
        )
    ).scalar_one_or_none()

    if not run_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Processing run not found"
        )

    count_q = select(func.count(ProcessingLog.id)).where(
        ProcessingLog.processing_run_id == run_id
    )
    total = (await db.execute(count_q)).scalar_one()

    offset = (page - 1) * page_size
    logs = (
        (
            await db.execute(
                select(ProcessingLog)
                .where(ProcessingLog.processing_run_id == run_id)
                .order_by(ProcessingLog.timestamp.asc())
                .offset(offset)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )

    items = [
        ProcessingLogDetailResponse(
            id=log.id,  # type: ignore[arg-type]
            timestamp=log.timestamp,  # type: ignore[arg-type]
            level=log.level,  # type: ignore[arg-type]
            message=log.message,  # type: ignore[arg-type]
            email_subject=log.email_subject,  # type: ignore[arg-type]
            email_from=log.email_from,  # type: ignore[arg-type]
            success=log.success,  # type: ignore[arg-type]
            mail_account_id=log.mail_account_id,  # type: ignore[arg-type]
            processing_run_id=log.processing_run_id,  # type: ignore[arg-type]
            email_size_bytes=log.email_size_bytes,  # type: ignore[arg-type]
            error_details=log.error_details,  # type: ignore[arg-type]
        )
        for log in logs
    ]

    return PaginatedProcessingLogsResponse(
        items=items, **_paginate(total, page, page_size)  # type: ignore[arg-type]
    )

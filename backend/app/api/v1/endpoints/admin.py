"""Admin endpoints"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.deps import get_current_superuser
from app.models.database_models import User, MailAccount, ProcessingRun

router = APIRouter()


@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get overall system statistics (admin only)"""
    
    # Count users
    user_count = await db.execute(select(func.count(User.id)))
    total_users = user_count.scalar()
    
    # Count accounts
    account_count = await db.execute(select(func.count(MailAccount.id)))
    total_accounts = account_count.scalar()
    
    # Count processing runs
    run_count = await db.execute(select(func.count(ProcessingRun.id)))
    total_runs = run_count.scalar()
    
    return {
        "total_users": total_users,
        "total_mail_accounts": total_accounts,
        "total_processing_runs": total_runs
    }

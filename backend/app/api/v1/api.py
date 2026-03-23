"""
API v1 router aggregation.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    mail_accounts,
    notifications,
    subscriptions,
    admin,
    providers,
    app_settings,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(
    mail_accounts.router, prefix="/mail-accounts", tags=["Mail Accounts"]
)
api_router.include_router(
    providers.router, prefix="/providers", tags=["Providers & Gmail"]
)
api_router.include_router(
    notifications.router, prefix="/notifications", tags=["Notifications"]
)
api_router.include_router(
    subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"]
)
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(app_settings.router, prefix="/settings", tags=["Settings"])

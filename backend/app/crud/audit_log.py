from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog

async def create_audit_log(db: AsyncSession, user_id: str, entity_type: str, entity_id: str, action: str, detail: str = ""):
    entry = AuditLog(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        detail=detail,
    )
    db.add(entry)
    await db.commit()
    return entry

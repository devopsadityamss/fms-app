# import uuid
# from app.core.logger import logger

# def generate_request_id():
#     return str(uuid.uuid4())

# def log_user_action(user_id: str, action: str, detail: str):
#     logger.info(
#         f"User action: {action}",
#         extra={"user_id": user_id, "detail": detail}
#     )

import uuid

def generate_request_id() -> str:
    return str(uuid.uuid4())

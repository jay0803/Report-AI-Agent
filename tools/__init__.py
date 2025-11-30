"""
Tool Layer for External Service Integration
완전히 모듈화된 독립형 Tool Layer

사용법:
    from tools import drive_tool, gmail_tool, slack_tool, notion_tool
    from tools.router import tools_router
    
    # FastAPI 앱에 라우터 추가 (선택적)
    app.include_router(tools_router, prefix="/api/tools", tags=["tools"])
"""

from .drive_tool import (
    create_folder,
    upload_file,
    search_files,
    download_file,
)

from .gmail_tool import (
    send_email,
    list_messages,
    get_message,
)

from .slack_tool import (
    send_dm,
    send_channel_message,
)

from .notion_tool import (
    create_page,
    add_database_item,
)

from .schemas import function_definitions

__all__ = [
    # Drive
    "create_folder",
    "upload_file",
    "search_files",
    "download_file",
    # Gmail
    "send_email",
    "list_messages",
    "get_message",
    # Slack
    "send_dm",
    "send_channel_message",
    # Notion
    "create_page",
    "add_database_item",
    # Schemas
    "function_definitions",
]


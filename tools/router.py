"""FastAPI Router for Tools - 모든 Tool 기능을 REST API로 노출"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from . import drive_tool, gmail_tool, slack_tool, notion_tool

tools_router = APIRouter()

# Request Models
class CreateFolderRequest(BaseModel):
    user_id: str
    name: str
    parent_id: Optional[str] = None

class SearchFilesRequest(BaseModel):
    user_id: str
    query: str
    max_results: int = 20

class SendEmailRequest(BaseModel):
    user_id: str
    to: str
    subject: str
    body: str

class SendDMRequest(BaseModel):
    user_id: str
    to_user: str
    text: str

class SendChannelMessageRequest(BaseModel):
    user_id: str
    channel_id: str
    text: str

class CreatePageRequest(BaseModel):
    user_id: str
    parent_page_id: str
    title: str

class AddDatabaseItemRequest(BaseModel):
    user_id: str
    database_id: str
    properties_dict: Dict[str, Any]

# Google Drive Endpoints
@tools_router.post("/drive/create-folder")
async def api_create_folder(request: CreateFolderRequest):
    return await drive_tool.create_folder(request.user_id, request.name, request.parent_id)

@tools_router.post("/drive/search-files")
async def api_search_files(request: SearchFilesRequest):
    return await drive_tool.search_files(request.user_id, request.query, request.max_results)

# Gmail Endpoints
@tools_router.post("/gmail/send-email")
async def api_send_email(request: SendEmailRequest):
    return await gmail_tool.send_email(request.user_id, request.to, request.subject, request.body)

# Slack Endpoints
@tools_router.post("/slack/send-dm")
async def api_send_dm(request: SendDMRequest):
    return await slack_tool.send_dm(request.user_id, request.to_user, request.text)

@tools_router.post("/slack/send-channel-message")
async def api_send_channel_message(request: SendChannelMessageRequest):
    return await slack_tool.send_channel_message(request.user_id, request.channel_id, request.text)

# Notion Endpoints
@tools_router.post("/notion/create-page")
async def api_create_page(request: CreatePageRequest):
    return await notion_tool.create_page(request.user_id, request.parent_page_id, request.title)

@tools_router.post("/notion/add-database-item")
async def api_add_database_item(request: AddDatabaseItemRequest):
    return await notion_tool.add_database_item(request.user_id, request.database_id, request.properties_dict)

# Health Check
@tools_router.get("/health")
async def health_check():
    return {"status": "healthy", "services": ["google_drive", "gmail", "slack", "notion"], "version": "1.0.0"}


"""Function Calling Schemas - LLM Function Calling을 위한 Tool 함수 스키마 정의"""

# 모든 스키마 통합
function_definitions = [
    # Google Drive
    {"name": "create_folder", "description": "Google Drive에 새 폴더를 생성합니다.", "parameters": {"type": "object", "properties": {"name": {"type": "string", "description": "생성할 폴더 이름"}, "parent_id": {"type": "string", "description": "부모 폴더 ID (선택적)"}}, "required": ["name"]}},
    {"name": "upload_file", "description": "로컬 파일을 Google Drive에 업로드합니다.", "parameters": {"type": "object", "properties": {"local_path": {"type": "string", "description": "업로드할 로컬 파일 경로"}, "folder_id": {"type": "string", "description": "업로드할 Drive 폴더 ID (선택적)"}, "file_name": {"type": "string", "description": "업로드 시 사용할 파일명 (선택적)"}}, "required": ["local_path"]}},
    {"name": "search_files", "description": "Google Drive에서 파일을 검색합니다.", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "검색 쿼리 (예: \"name contains 'report'\")"}, "max_results": {"type": "integer", "description": "최대 결과 수 (기본값: 20)", "default": 20}}, "required": ["query"]}},
    {"name": "download_file", "description": "Google Drive에서 파일을 다운로드합니다.", "parameters": {"type": "object", "properties": {"file_id": {"type": "string", "description": "다운로드할 파일 ID"}, "save_path": {"type": "string", "description": "저장할 로컬 경로 (선택적)"}}, "required": ["file_id"]}},
    
    # Gmail
    {"name": "send_email", "description": "Gmail로 이메일을 전송합니다.", "parameters": {"type": "object", "properties": {"to": {"type": "string", "description": "수신자 이메일 주소"}, "subject": {"type": "string", "description": "이메일 제목"}, "body": {"type": "string", "description": "이메일 본문"}, "attachment_path": {"type": "string", "description": "첨부파일 경로 (선택적)"}}, "required": ["to", "subject", "body"]}},
    {"name": "list_messages", "description": "Gmail 메시지 목록을 조회합니다.", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "검색 쿼리 (예: 'is:unread')", "default": "is:unread"}, "max_results": {"type": "integer", "description": "최대 결과 수 (기본값: 20)", "default": 20}}, "required": []}},
    {"name": "get_message", "description": "Gmail 메시지의 상세 정보를 조회합니다.", "parameters": {"type": "object", "properties": {"message_id": {"type": "string", "description": "조회할 메시지 ID"}, "format": {"type": "string", "description": "응답 형식 ('full', 'metadata', 'minimal', 'raw')", "default": "full"}}, "required": ["message_id"]}},
    
    # Slack
    {"name": "send_dm", "description": "Slack DM (Direct Message)을 전송합니다.", "parameters": {"type": "object", "properties": {"to_user": {"type": "string", "description": "수신자 Slack User ID"}, "text": {"type": "string", "description": "메시지 텍스트"}}, "required": ["to_user", "text"]}},
    {"name": "send_channel_message", "description": "Slack 채널에 메시지를 전송합니다.", "parameters": {"type": "object", "properties": {"channel_id": {"type": "string", "description": "채널 ID"}, "text": {"type": "string", "description": "메시지 텍스트"}}, "required": ["channel_id", "text"]}},
    
    # Notion
    {"name": "create_page", "description": "Notion에 새 페이지를 생성합니다.", "parameters": {"type": "object", "properties": {"parent_page_id": {"type": "string", "description": "부모 페이지 ID"}, "title": {"type": "string", "description": "페이지 제목"}}, "required": ["parent_page_id", "title"]}},
    {"name": "add_database_item", "description": "Notion 데이터베이스에 항목을 추가합니다.", "parameters": {"type": "object", "properties": {"database_id": {"type": "string", "description": "데이터베이스 ID"}, "properties_dict": {"type": "object", "description": "속성 딕셔너리 (Notion properties 형식)"}}, "required": ["database_id", "properties_dict"]}},
]

def get_all_schemas():
    """모든 Function Calling 스키마 반환"""
    return function_definitions

def get_schema_by_name(function_name: str):
    """함수 이름으로 스키마 검색"""
    for schema in function_definitions:
        if schema["name"] == function_name:
            return schema
    return None


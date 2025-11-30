"""Gmail API Tool (공식 SDK 사용)"""
import os
import base64
from typing import Optional, Dict, Any, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from .token_manager import load_token

def _get_credentials(token_data: Dict[str, Any]) -> Credentials:
    """토큰 데이터를 Google Credentials 객체로 변환"""
    return Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    )

def _create_message(to: str, subject: str, body: str, attachment_path: Optional[str] = None) -> Dict[str, str]:
    """이메일 메시지 생성"""
    if attachment_path:
        message = MIMEMultipart()
    else:
        message = MIMEText(body, "plain", "utf-8")
    
    message["to"] = to
    message["subject"] = subject
    
    if attachment_path:
        message.attach(MIMEText(body, "plain", "utf-8"))
        if os.path.exists(attachment_path):
            filename = os.path.basename(attachment_path)
            with open(attachment_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={filename}")
                message.attach(part)
    
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return {"raw": raw_message}

async def send_email(user_id: str, to: str, subject: str, body: str, attachment_path: Optional[str] = None) -> Dict[str, Any]:
    """Gmail로 이메일 전송"""
    try:
        token_data = await load_token(user_id, "google")
        if not token_data:
            return {"success": False, "data": None, "error": "Google 토큰을 찾을 수 없습니다."}
        
        creds = _get_credentials(token_data)
        service = build('gmail', 'v1', credentials=creds)
        
        message = _create_message(to, subject, body, attachment_path)
        result = service.users().messages().send(userId='me', body=message).execute()
        
        return {"success": True, "data": {"message_id": result.get('id'), "thread_id": result.get('threadId'), "to": to, "subject": subject}, "error": None}
    except Exception as e:
        return {"success": False, "data": None, "error": f"이메일 전송 중 오류: {str(e)}"}

async def list_messages(user_id: str, query: str = "is:unread", max_results: int = 20, label_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Gmail 메시지 목록 조회"""
    try:
        token_data = await load_token(user_id, "google")
        if not token_data:
            return {"success": False, "data": None, "error": "Google 토큰을 찾을 수 없습니다."}
        
        creds = _get_credentials(token_data)
        service = build('gmail', 'v1', credentials=creds)
        
        results = service.users().messages().list(userId='me', q=query, maxResults=max_results, labelIds=label_ids).execute()
        messages = results.get('messages', [])
        
        message_details = []
        for msg in messages:
            msg_id = msg['id']
            detail = service.users().messages().get(userId='me', id=msg_id, format='metadata', metadataHeaders=['From', 'Subject', 'Date']).execute()
            headers = {h['name']: h['value'] for h in detail.get('payload', {}).get('headers', [])}
            message_details.append({
                "id": msg_id,
                "thread_id": detail.get('threadId'),
                "from": headers.get('From', ''),
                "subject": headers.get('Subject', ''),
                "date": headers.get('Date', ''),
                "snippet": detail.get('snippet', ''),
            })
        
        return {"success": True, "data": {"count": len(message_details), "messages": message_details, "result_size_estimate": results.get('resultSizeEstimate', 0)}, "error": None}
    except Exception as e:
        return {"success": False, "data": None, "error": f"메시지 목록 조회 중 오류: {str(e)}"}

async def get_message(user_id: str, message_id: str, format: str = "full") -> Dict[str, Any]:
    """Gmail 메시지 상세 조회"""
    try:
        token_data = await load_token(user_id, "google")
        if not token_data:
            return {"success": False, "data": None, "error": "Google 토큰을 찾을 수 없습니다."}
        
        creds = _get_credentials(token_data)
        service = build('gmail', 'v1', credentials=creds)
        
        message = service.users().messages().get(userId='me', id=message_id, format=format).execute()
        
        headers = {}
        if 'payload' in message and 'headers' in message['payload']:
            headers = {h['name']: h['value'] for h in message['payload']['headers']}
        
        body = ""
        if 'payload' in message:
            payload = message['payload']
            if 'body' in payload and 'data' in payload['body']:
                body_data = payload['body']['data']
                body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
            elif 'parts' in payload:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain':
                        if 'data' in part.get('body', {}):
                            body_data = part['body']['data']
                            body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                            break
        
        return {"success": True, "data": {"id": message.get('id'), "thread_id": message.get('threadId'), "from": headers.get('From', ''), "to": headers.get('To', ''), "subject": headers.get('Subject', ''), "date": headers.get('Date', ''), "snippet": message.get('snippet', ''), "body": body, "label_ids": message.get('labelIds', [])}, "error": None}
    except Exception as e:
        return {"success": False, "data": None, "error": f"메시지 조회 중 오류: {str(e)}"}


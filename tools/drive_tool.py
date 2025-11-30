"""Google Drive API Tool (공식 SDK 사용)"""
import os
from typing import Optional, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials
import io
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

async def create_folder(user_id: str, name: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
    """Google Drive에 폴더 생성"""
    try:
        token_data = await load_token(user_id, "google")
        if not token_data:
            return {"success": False, "data": None, "error": "Google 토큰을 찾을 수 없습니다."}
        
        creds = _get_credentials(token_data)
        service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {'name': name, 'mimeType': 'application/vnd.google-apps.folder'}
        if parent_id:
            file_metadata['parents'] = [parent_id]
        
        folder = service.files().create(body=file_metadata, fields='id, name, webViewLink').execute()
        
        return {
            "success": True,
            "data": {"folder_id": folder.get('id'), "name": folder.get('name'), "web_view_link": folder.get('webViewLink')},
            "error": None
        }
    except Exception as e:
        return {"success": False, "data": None, "error": f"폴더 생성 중 오류: {str(e)}"}

async def upload_file(user_id: str, local_path: str, folder_id: Optional[str] = None, file_name: Optional[str] = None) -> Dict[str, Any]:
    """로컬 파일을 Google Drive에 업로드"""
    try:
        if not os.path.exists(local_path):
            return {"success": False, "data": None, "error": f"파일을 찾을 수 없습니다: {local_path}"}
        
        token_data = await load_token(user_id, "google")
        if not token_data:
            return {"success": False, "data": None, "error": "Google 토큰을 찾을 수 없습니다."}
        
        creds = _get_credentials(token_data)
        service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {'name': file_name or os.path.basename(local_path)}
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        media = MediaFileUpload(local_path, resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id, name, mimeType, webViewLink, size').execute()
        
        return {
            "success": True,
            "data": {"file_id": file.get('id'), "name": file.get('name'), "mime_type": file.get('mimeType'), "web_view_link": file.get('webViewLink'), "size": file.get('size')},
            "error": None
        }
    except Exception as e:
        return {"success": False, "data": None, "error": f"파일 업로드 중 오류: {str(e)}"}

async def search_files(user_id: str, query: str, max_results: int = 20, order_by: str = "modifiedTime desc") -> Dict[str, Any]:
    """Google Drive에서 파일 검색"""
    try:
        token_data = await load_token(user_id, "google")
        if not token_data:
            return {"success": False, "data": None, "error": "Google 토큰을 찾을 수 없습니다."}
        
        creds = _get_credentials(token_data)
        service = build('drive', 'v3', credentials=creds)
        
        results = service.files().list(
            q=query, pageSize=max_results, orderBy=order_by,
            fields='files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink, iconLink)'
        ).execute()
        
        files = results.get('files', [])
        return {"success": True, "data": {"count": len(files), "files": files}, "error": None}
    except Exception as e:
        return {"success": False, "data": None, "error": f"파일 검색 중 오류: {str(e)}"}

async def download_file(user_id: str, file_id: str, save_path: Optional[str] = None) -> Dict[str, Any]:
    """Google Drive에서 파일 다운로드"""
    try:
        token_data = await load_token(user_id, "google")
        if not token_data:
            return {"success": False, "data": None, "error": "Google 토큰을 찾을 수 없습니다."}
        
        creds = _get_credentials(token_data)
        service = build('drive', 'v3', credentials=creds)
        
        file_meta = service.files().get(fileId=file_id, fields='id, name, mimeType, size').execute()
        file_name = file_meta.get('name', 'downloaded_file')
        
        request = service.files().get_media(fileId=file_id)
        
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            fh = io.FileIO(save_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            fh.close()
            return {"success": True, "data": {"file_id": file_id, "name": file_name, "size": file_meta.get('size'), "saved_path": save_path}, "error": None}
        else:
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            file_content = fh.getvalue()
            return {"success": True, "data": {"file_id": file_id, "name": file_name, "size": len(file_content), "content": file_content}, "error": None}
    except Exception as e:
        return {"success": False, "data": None, "error": f"파일 다운로드 중 오류: {str(e)}"}


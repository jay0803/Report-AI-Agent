"""Slack API Tool (공식 SDK 사용)"""
from typing import Optional, Dict, Any, List
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from .token_manager import load_token

async def send_dm(user_id: str, to_user: str, text: str, blocks: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Slack DM (Direct Message) 전송"""
    try:
        token_data = await load_token(user_id, "slack")
        if not token_data:
            return {"success": False, "data": None, "error": "Slack 토큰을 찾을 수 없습니다."}
        
        access_token = token_data.get("access_token")
        client = AsyncWebClient(token=access_token)
        
        open_response = await client.conversations_open(users=to_user)
        if not open_response["ok"]:
            return {"success": False, "data": None, "error": f"DM 채널 열기 실패: {open_response.get('error', 'Unknown error')}"}
        
        channel_id = open_response["channel"]["id"]
        send_response = await client.chat_postMessage(channel=channel_id, text=text, blocks=blocks)
        
        if send_response["ok"]:
            return {"success": True, "data": {"channel": channel_id, "ts": send_response.get("ts"), "message": send_response.get("message", {})}, "error": None}
        else:
            return {"success": False, "data": None, "error": f"메시지 전송 실패: {send_response.get('error', 'Unknown error')}"}
    except SlackApiError as e:
        return {"success": False, "data": None, "error": f"Slack API 오류: {e.response['error']}"}
    except Exception as e:
        return {"success": False, "data": None, "error": f"DM 전송 중 오류: {str(e)}"}

async def send_channel_message(user_id: str, channel_id: str, text: str, blocks: Optional[List[Dict]] = None, thread_ts: Optional[str] = None) -> Dict[str, Any]:
    """Slack 채널에 메시지 전송"""
    try:
        token_data = await load_token(user_id, "slack")
        if not token_data:
            return {"success": False, "data": None, "error": "Slack 토큰을 찾을 수 없습니다."}
        
        access_token = token_data.get("access_token")
        client = AsyncWebClient(token=access_token)
        
        response = await client.chat_postMessage(channel=channel_id, text=text, blocks=blocks, thread_ts=thread_ts)
        
        if response["ok"]:
            return {"success": True, "data": {"channel": response.get("channel"), "ts": response.get("ts"), "message": response.get("message", {})}, "error": None}
        else:
            return {"success": False, "data": None, "error": f"메시지 전송 실패: {response.get('error', 'Unknown error')}"}
    except SlackApiError as e:
        return {"success": False, "data": None, "error": f"Slack API 오류: {e.response['error']}"}
    except Exception as e:
        return {"success": False, "data": None, "error": f"채널 메시지 전송 중 오류: {str(e)}"}

async def list_channels(user_id: str, types: str = "public_channel,private_channel", limit: int = 100) -> Dict[str, Any]:
    """Slack 채널 목록 조회"""
    try:
        token_data = await load_token(user_id, "slack")
        if not token_data:
            return {"success": False, "data": None, "error": "Slack 토큰을 찾을 수 없습니다."}
        
        access_token = token_data.get("access_token")
        client = AsyncWebClient(token=access_token)
        
        response = await client.conversations_list(types=types, limit=limit)
        
        if response["ok"]:
            channels = response.get("channels", [])
            return {"success": True, "data": {"count": len(channels), "channels": [{"id": ch.get("id"), "name": ch.get("name"), "is_private": ch.get("is_private", False), "is_member": ch.get("is_member", False), "num_members": ch.get("num_members", 0)} for ch in channels]}, "error": None}
        else:
            return {"success": False, "data": None, "error": f"채널 목록 조회 실패: {response.get('error', 'Unknown error')}"}
    except SlackApiError as e:
        return {"success": False, "data": None, "error": f"Slack API 오류: {e.response['error']}"}
    except Exception as e:
        return {"success": False, "data": None, "error": f"채널 목록 조회 중 오류: {str(e)}"}

async def get_user_info(user_id: str, slack_user_id: str) -> Dict[str, Any]:
    """Slack 사용자 정보 조회"""
    try:
        token_data = await load_token(user_id, "slack")
        if not token_data:
            return {"success": False, "data": None, "error": "Slack 토큰을 찾을 수 없습니다."}
        
        access_token = token_data.get("access_token")
        client = AsyncWebClient(token=access_token)
        
        response = await client.users_info(user=slack_user_id)
        
        if response["ok"]:
            user = response.get("user", {})
            profile = user.get("profile", {})
            return {"success": True, "data": {"id": user.get("id"), "name": user.get("name"), "real_name": user.get("real_name"), "display_name": profile.get("display_name"), "email": profile.get("email"), "is_bot": user.get("is_bot", False)}, "error": None}
        else:
            return {"success": False, "data": None, "error": f"사용자 정보 조회 실패: {response.get('error', 'Unknown error')}"}
    except SlackApiError as e:
        return {"success": False, "data": None, "error": f"Slack API 오류: {e.response['error']}"}
    except Exception as e:
        return {"success": False, "data": None, "error": f"사용자 정보 조회 중 오류: {str(e)}"}


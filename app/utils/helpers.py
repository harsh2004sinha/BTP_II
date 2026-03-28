import os
import uuid
from datetime import datetime
from typing import Optional
import aiofiles

def generate_unique_filename(original_filename: str) -> str:
    """Generate unique filename preserving extension"""
    ext = os.path.splitext(original_filename)[1].lower()
    unique_name = f"{uuid.uuid4()}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
    return unique_name


def validate_file_extension(filename: str, allowed: list) -> bool:
    """Check if file has allowed extension"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed


def format_file_size(size_bytes: int) -> str:
    """Format bytes to human readable size"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f} KB"
    else:
        return f"{size_bytes/(1024*1024):.1f} MB"


async def save_upload_file(
    file_content: bytes,
    filename: str,
    upload_dir: str
) -> str:
    """
    Save uploaded file to disk asynchronously.
    
    Returns:
        Full path of saved file
    """
    os.makedirs(upload_dir, exist_ok=True)
    unique_filename = generate_unique_filename(filename)
    file_path = os.path.join(upload_dir, unique_filename)
    
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(file_content)
    
    return file_path


def create_api_response(
    success: bool,
    message: str,
    data: Optional[dict] = None,
    status_code: int = 200
) -> dict:
    """Standard API response format"""
    response = {
        "success": success,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    if data is not None:
        response["data"] = data
    return response
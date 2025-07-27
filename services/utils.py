import os
import re
import hashlib
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

def validate_pdf_file(file_path: str) -> Tuple[bool, str]:
    """
    Validate PDF file for processing
    Returns: (is_valid, message)
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        # Check file size (max 50MB)
        file_size = os.path.getsize(file_path)
        if file_size > 50 * 1024 * 1024:
            return False, "File size exceeds 50MB limit"
        
        # Check file extension
        if not file_path.lower().endswith('.pdf'):
            return False, "File is not a PDF"
        
        # Try to open with PyMuPDF to check if it's a valid PDF
        import fitz
        try:
            doc = fitz.open(file_path)
            if doc.needs_pass:
                doc.close()
                return False, "PDF is password protected"
            
            # Check if PDF has content
            text_content = ""
            for page in doc:
                text_content += page.get_text()
            
            doc.close()
            
            if len(text_content.strip()) < 100:
                return False, "PDF contains insufficient text content"
            
            return True, "PDF is valid"
            
        except Exception as e:
            return False, f"Invalid PDF file: {str(e)}"
    
    except Exception as e:
        return False, f"Error validating file: {str(e)}"

def clean_filename(filename: str) -> str:
    """Clean filename for safe storage"""
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    # Limit length
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:95] + ext
    return filename

def generate_file_hash(file_path: str) -> str:
    """Generate SHA-256 hash of file content"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def format_time_duration(seconds: int) -> str:
    """Format time duration in human readable format"""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"

def extract_text_chunks(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks"""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            sentence_end = text.rfind('.', start, end)
            if sentence_end > start + chunk_size // 2:
                end = sentence_end + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks

def sanitize_text(text: str) -> str:
    """Sanitize text for safe processing"""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    return text.strip()

def calculate_reading_time(text: str, words_per_minute: int = 200) -> int:
    """Calculate estimated reading time in minutes"""
    word_count = len(text.split())
    return max(1, word_count // words_per_minute)

def generate_unique_id(prefix: str = "id") -> str:
    """Generate unique identifier"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    random_suffix = os.urandom(4).hex()
    return f"{prefix}_{timestamp}_{random_suffix}"

def is_valid_language_code(lang_code: str) -> bool:
    """Check if language code is supported"""
    supported_languages = {
        'en', 'hi', 'ta', 'te', 'bn', 'mr', 'gu', 'kn', 'ml', 'pa'
    }
    return lang_code.lower() in supported_languages

def get_language_name(lang_code: str) -> str:
    """Get language name from code"""
    language_names = {
        'en': 'English',
        'hi': 'Hindi',
        'ta': 'Tamil',
        'te': 'Telugu',
        'bn': 'Bengali',
        'mr': 'Marathi',
        'gu': 'Gujarati',
        'kn': 'Kannada',
        'ml': 'Malayalam',
        'pa': 'Punjabi'
    }
    return language_names.get(lang_code.lower(), 'Unknown')

def create_directory_if_not_exists(directory_path: str) -> bool:
    """Create directory if it doesn't exist"""
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {directory_path}: {e}")
        return False

def cleanup_old_files(directory: str, days: int = 7) -> int:
    """Clean up old files in directory"""
    try:
        cutoff_time = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff_time:
                    os.remove(file_path)
                    deleted_count += 1
        
        return deleted_count
    except Exception as e:
        print(f"Error cleaning up files: {e}")
        return 0

def save_json_data(data: Dict, file_path: str) -> bool:
    """Save data to JSON file"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving JSON data: {e}")
        return False

def load_json_data(file_path: str) -> Optional[Dict]:
    """Load data from JSON file"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"Error loading JSON data: {e}")
        return None

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_password_hash(password: str) -> str:
    """Generate password hash"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_internet_connection() -> bool:
    """Check if internet connection is available"""
    try:
        import requests
        response = requests.get("https://www.google.com", timeout=3)
        return response.status_code == 200
    except:
        return False

def get_system_info() -> Dict[str, str]:
    """Get system information"""
    import platform
    import psutil
    
    return {
        'platform': platform.system(),
        'platform_version': platform.version(),
        'python_version': platform.python_version(),
        'cpu_count': str(psutil.cpu_count()),
        'memory_total': format_file_size(psutil.virtual_memory().total),
        'disk_usage': f"{psutil.disk_usage('/').percent:.1f}%"
    } 
import os
from typing import List, Dict, Tuple, Optional
import re
from dataclasses import dataclass
import json

# Try to import PyMuPDF
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
    print("✅ PyMuPDF (fitz) is available")
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("❌ PyMuPDF (fitz) is not available. Please install: pip install PyMuPDF")

@dataclass
class ContentSection:
    """Represents a structured section of content"""
    title: str
    content: str
    level: int  # 1=chapter, 2=topic, 3=subtopic
    page_start: int
    page_end: int
    parent: Optional[str] = None
    children: List[str] = None

class PDFService:
    def __init__(self):
        self.supported_languages = ['en', 'hi', 'ta', 'te', 'bn', 'mr', 'gu', 'kn', 'ml', 'pa']
    
    def extract_text_from_pdf(self, filepath: str) -> Dict:
        """Extract text and structure from PDF"""
        try:
            print(f"📄 Starting PDF extraction for: {filepath}")
            
            # Check if PyMuPDF is available
            if not PYMUPDF_AVAILABLE:
                return {
                    'success': False,
                    'error': 'PyMuPDF is not available. Please install: pip install PyMuPDF'
                }
            
            # Check if file exists
            if not os.path.exists(filepath):
                return {
                    'success': False,
                    'error': f'PDF file not found: {filepath}'
                }
            
            # Open PDF document
            doc = fitz.open(filepath)
            print(f"✅ PDF opened successfully, pages: {len(doc)}")
            
            full_text = ""
            structured_content = []
            
            # Extract full text and detect structure
            for page_num in range(len(doc)):
                try:
                    page = doc.load_page(page_num)
                    text = page.get_text()
                    full_text += text + "\n"
                    
                    # Detect structured content on this page
                    sections = self._detect_sections(text, page_num)
                    structured_content.extend(sections)
                    
                    print(f"📄 Page {page_num + 1}: {len(text)} characters, {len(sections)} sections")
                    
                except Exception as page_error:
                    print(f"⚠️ Error processing page {page_num + 1}: {page_error}")
                    # Continue with other pages
                    continue
            
            print(f"📊 Total text extracted: {len(full_text)} characters")
            
            # Organize content hierarchy
            organized_content = self._organize_content_hierarchy(structured_content)
            print(f"📊 Organized content sections: {len(organized_content.get('chapters', []))} chapters, {len(organized_content.get('topics', []))} topics")
            
            # Extract metadata and get page count before closing
            metadata = self._extract_metadata(doc)
            total_pages = len(doc)
            
            doc.close()
            print("✅ PDF extraction completed successfully")
            
            return {
                'success': True,
                'text': full_text,
                'structured_content': organized_content,
                'metadata': metadata,
                'total_pages': total_pages,
                'language': self._detect_language(full_text)
            }
            
        except Exception as e:
            print(f"❌ PDF extraction failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': f'PDF processing failed: {str(e)}'
            }
    
    def _clean_text(self, text: str) -> str:
        """Clean and preprocess extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers and headers/footers
        text = re.sub(r'^\d+$', '', text, flags=re.MULTILINE)
        
        # Remove special characters but keep important punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]]', '', text)
        
        # Clean up line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection based on character sets"""
        # Count Devanagari characters (Hindi, Marathi, etc.)
        devanagari_chars = len(re.findall(r'[\u0900-\u097F]', text))
        
        # Count Tamil characters
        tamil_chars = len(re.findall(r'[\u0B80-\u0BFF]', text))
        
        # Count Telugu characters
        telugu_chars = len(re.findall(r'[\u0C00-\u0C7F]', text))
        
        # Count Bengali characters
        bengali_chars = len(re.findall(r'[\u0980-\u09FF]', text))
        
        # Count English characters
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        
        total_chars = len(text)
        
        if total_chars == 0:
            return 'en'
        
        # Calculate percentages
        if devanagari_chars / total_chars > 0.1:
            return 'hi'  # Hindi
        elif tamil_chars / total_chars > 0.1:
            return 'ta'  # Tamil
        elif telugu_chars / total_chars > 0.1:
            return 'te'  # Telugu
        elif bengali_chars / total_chars > 0.1:
            return 'bn'  # Bengali
        else:
            return 'en'  # Default to English
    
    def _detect_sections(self, text: str, page_num: int) -> List[ContentSection]:
        """Detect chapters, topics, and subtopics from text"""
        sections = []
        
        # Common patterns for section headers
        patterns = [
            # Chapter patterns (level 1)
            (r'^Chapter\s+(\d+)[:\s]*(.+)$', 1),
            (r'^Unit\s+(\d+)[:\s]*(.+)$', 1),
            (r'^Lesson\s+(\d+)[:\s]*(.+)$', 1),
            (r'^(\d+)\.\s*([A-Z][^.]{5,})$', 1),
            
            # Topic patterns (level 2)
            (r'^(\d+)\.(\d+)\s*([A-Z][^.]{5,})$', 2),
            (r'^([A-Z][a-z]+)\s*[:\s]*(.+)$', 2),
            
            # Subtopic patterns (level 3)
            (r'^(\d+)\.(\d+)\.(\d+)\s*([A-Z][^.]{3,})$', 3),
            (r'^[a-z]\)\s*([A-Z][^.]{3,})$', 3),
        ]
        
        lines = text.split('\n')
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            for pattern, level in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    try:
                        if level == 1:
                            if len(match.groups()) >= 2:
                                title = f"Chapter {match.group(1)}: {match.group(2)}"
                            else:
                                title = f"Chapter {match.group(1)}"
                        elif level == 2:
                            if len(match.groups()) >= 2:
                                title = f"{match.group(1)}: {match.group(2)}"
                            else:
                                title = match.group(1)
                        elif level == 3:
                            title = match.group(1)
                        else:
                            title = line
                    except (IndexError, AttributeError):
                        # Fallback if regex groups don't match expected pattern
                        title = line
                    
                    section = ContentSection(
                        title=title.strip(),
                        content="",
                        level=level,
                        page_start=page_num,
                        page_end=page_num,
                        children=[]
                    )
                    sections.append(section)
                    break
        
        return sections
    
    def _organize_content_hierarchy(self, sections: List[ContentSection]) -> Dict:
        """Organize sections into a hierarchical structure"""
        hierarchy = {
            'chapters': [],
            'topics': [],
            'subtopics': []
        }
        
        # Group by level
        for section in sections:
            if section.level == 1:
                hierarchy['chapters'].append({
                    'id': f"chapter_{len(hierarchy['chapters'])+1}",
                    'title': section.title,
                    'page_start': section.page_start,
                    'page_end': section.page_end,
                    'topics': []
                })
            elif section.level == 2:
                hierarchy['topics'].append({
                    'id': f"topic_{len(hierarchy['topics'])+1}",
                    'title': section.title,
                    'page_start': section.page_start,
                    'page_end': section.page_end,
                    'subtopics': []
                })
            elif section.level == 3:
                hierarchy['subtopics'].append({
                    'id': f"subtopic_{len(hierarchy['subtopics'])+1}",
                    'title': section.title,
                    'page_start': section.page_start,
                    'page_end': section.page_end
                })
        
        return hierarchy
    
    def get_content_by_section(self, filepath: str, section_id: str) -> Dict:
        """Get content for a specific section"""
        try:
            doc = fitz.open(filepath)
            result = self.extract_text_from_pdf(filepath)
            
            if not result['success']:
                return result
            
            # Find the section
            section_content = ""
            for section_type, sections in result['structured_content'].items():
                for section in sections:
                    if section['id'] == section_id:
                        # Extract content for this section's page range
                        for page_num in range(section['page_start'], section['page_end'] + 1):
                            if page_num < len(doc):
                                page = doc.load_page(page_num)
                                section_content += page.get_text() + "\n"
                        break
            
            doc.close()
            
            return {
                'success': True,
                'section_id': section_id,
                'content': section_content,
                'metadata': result['metadata']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Section extraction failed: {str(e)}'
            }
    
    def _extract_metadata(self, doc) -> Dict:
        """Extract metadata from PDF document"""
        return {
            'title': doc.metadata.get('title', ''),
            'author': doc.metadata.get('author', ''),
            'subject': doc.metadata.get('subject', ''),
            'pages': len(doc)
        }
    
    def chunk_text(self, text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
        """
        Split text into overlapping chunks for better processing
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
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
    
    def extract_key_topics(self, text: str) -> List[str]:
        """
        Extract key topics from text for categorization
        """
        # Simple keyword extraction
        common_topics = [
            'mathematics', 'math', 'algebra', 'geometry', 'calculus',
            'science', 'physics', 'chemistry', 'biology',
            'history', 'geography', 'civics', 'economics',
            'english', 'literature', 'grammar', 'vocabulary',
            'hindi', 'sanskrit', 'computer', 'technology'
        ]
        
        text_lower = text.lower()
        found_topics = []
        
        for topic in common_topics:
            if topic in text_lower:
                found_topics.append(topic.title())
        
        return list(set(found_topics))[:5]  # Return unique topics, max 5
    
    def validate_pdf(self, filepath: str) -> Tuple[bool, str]:
        """
        Validate if PDF is suitable for processing
        """
        try:
            # Check if PyMuPDF is available
            if not PYMUPDF_AVAILABLE:
                return False, "PyMuPDF is not available. Please install: pip install PyMuPDF"
            
            doc = fitz.open(filepath)
            
            # Check if PDF is encrypted
            if doc.needs_pass:
                doc.close()
                return False, "PDF is password protected"
            
            # Check if PDF has text content
            text_content = ""
            for page in doc:
                text_content += page.get_text()
            
            doc.close()
            
            if len(text_content.strip()) < 100:
                return False, "PDF contains insufficient text content"
            
            return True, "PDF is valid"
            
        except Exception as e:
            return False, f"Error validating PDF: {str(e)}"

# Global instance
pdf_service = PDFService() 
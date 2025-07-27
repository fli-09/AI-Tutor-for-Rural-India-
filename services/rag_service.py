import os
import json
import hashlib
from typing import List, Dict, Optional, Tuple
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np
from datetime import datetime

class RAGService:
    def __init__(self, db_path: str = "vector_db"):
        """Initialize RAG service with vector database"""
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize sentence transformer for embeddings
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ RAG Service: Embedding model loaded successfully")
        except Exception as e:
            print(f"❌ RAG Service: Failed to load embedding model: {e}")
            print("⚠️  RAG Service: Running in fallback mode without embeddings")
            self.embedding_model = None
        
        # Get or create collections
        self.content_collection = self.client.get_or_create_collection(
            name="curriculum_content",
            metadata={"description": "Curriculum content chunks for RAG"}
        )
        
        self.questions_collection = self.client.get_or_create_collection(
            name="student_questions",
            metadata={"description": "Student questions and answers"}
        )
        
        # Multi-subject collections
        self.subject_collections = {}
        self.subjects = ['mathematics', 'science', 'history', 'geography', 'english', 'hindi']
        
        for subject in self.subjects:
            self.subject_collections[subject] = self.client.get_or_create_collection(
                name=f"subject_{subject}",
                metadata={"description": f"{subject.title()} content chunks"}
            )
        
        # Unified knowledge base collection
        self.unified_collection = self.client.get_or_create_collection(
            name="unified_knowledge",
            metadata={"description": "Unified knowledge base across all subjects"}
        )
        
        print("✅ RAG Service: Vector database initialized")
    
    def extract_and_chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Extract text chunks with overlap for better context"""
        if not text:
            return []
        
        # Clean and normalize text
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = ' '.join(text.split())  # Remove extra whitespace
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                for i in range(end, max(start + chunk_size - 100, start), -1):
                    if text[i] in '.!?':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for text chunks"""
        if not self.embedding_model:
            # Return dummy embeddings if model is not loaded
            print("⚠️  RAG Service: Using dummy embeddings (model not loaded)")
            return [[0.0] * 384 for _ in texts]  # 384 is the dimension of all-MiniLM-L6-v2
        
        try:
            embeddings = self.embedding_model.encode(texts, convert_to_tensor=False)
            return embeddings.tolist()
        except Exception as e:
            print(f"❌ Error creating embeddings: {e}")
            return []
    
    def add_pdf_content(self, pdf_filename: str, text: str, metadata: Dict = None, subject: str = None) -> bool:
        """Add PDF content to vector database with subject classification"""
        try:
            # Extract chunks
            chunks = self.extract_and_chunk_text(text)
            if not chunks:
                print(f"❌ No text chunks extracted from {pdf_filename}")
                return False
            
            # Create embeddings
            try:
                embeddings = self.create_embeddings(chunks)
                if not embeddings:
                    print(f"❌ Failed to create embeddings for {pdf_filename}")
                    return False
            except Exception as emb_error:
                print(f"⚠️  Embedding creation failed, using dummy embeddings: {emb_error}")
                embeddings = [[0.0] * 384 for _ in chunks]  # Fallback embeddings
            
            # Prepare documents for storage
            documents = []
            metadatas = []
            ids = []
            
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = f"{pdf_filename}_chunk_{i}"
                
                # Create metadata
                chunk_metadata = {
                    "pdf_filename": pdf_filename,
                    "chunk_index": i,
                    "chunk_size": len(chunk),
                    "timestamp": datetime.now().isoformat(),
                    "source": "pdf_upload"
                }
                
                if metadata:
                    chunk_metadata.update(metadata)
                
                documents.append(chunk)
                metadatas.append(chunk_metadata)
                ids.append(chunk_id)
            
            # Add to main collection
            try:
                self.content_collection.add(
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids
                )
            except Exception as e:
                print(f"⚠️  Failed to add to main collection: {e}")
            
            # Add to subject-specific collection if subject is specified
            if subject and subject.lower() in self.subjects:
                try:
                    subject_collection = self.subject_collections[subject.lower()]
                    subject_collection.add(
                        documents=documents,
                        embeddings=embeddings,
                        metadatas=metadatas,
                        ids=ids
                    )
                    print(f"✅ Added to {subject} collection")
                except Exception as e:
                    print(f"⚠️  Failed to add to {subject} collection: {e}")
            
            # Add to unified knowledge base
            try:
                self.unified_collection.add(
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids
                )
            except Exception as e:
                print(f"⚠️  Failed to add to unified collection: {e}")
            
            print(f"✅ Added {len(chunks)} chunks from {pdf_filename} to vector database")
            return True
            
        except Exception as e:
            print(f"❌ Error adding PDF content: {e}")
            return False
    
    def search_relevant_content(self, query: str, top_k: int = 5, filter_metadata: Dict = None, subject: str = None) -> List[Dict]:
        """Search for relevant content based on student query with optional subject filtering"""
        try:
            if not self.embedding_model:
                raise Exception("Embedding model not loaded")
            
            # Choose collection based on subject
            if subject and subject.lower() in self.subjects:
                collection = self.subject_collections[subject.lower()]
                print(f"🔍 Searching in {subject} collection")
            else:
                collection = self.unified_collection
                print(f"🔍 Searching in unified knowledge base")
            
            # Check if we have any content in the database
            total_chunks = collection.count()
            if total_chunks == 0:
                print("ℹ️ No content available in selected collection")
                return []
            
            # Create query embedding
            query_embedding = self.create_embeddings([query])
            if not query_embedding:
                return []
            
            # Search in collection
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=top_k,
                where=filter_metadata
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        'content': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {},
                        'distance': results['distances'][0][i] if results['distances'] and results['distances'][0] else 0,
                        'id': results['ids'][0][i] if results['ids'] and results['ids'][0] else None
                    })
            
            print(f"🔍 Found {len(formatted_results)} relevant chunks for query: '{query[:50]}...'")
            return formatted_results
            
        except Exception as e:
            print(f"❌ Error searching content: {e}")
            return []
    
    def process_question(self, query: str, llm_service, user_id: str = None) -> Dict:
        """Main method to process a question and generate an answer"""
        try:
            print(f"🤔 Processing question: {query}")
            
            # Search for relevant curriculum content
            context_chunks = self.search_relevant_content(query, top_k=5)
            
            # Generate answer
            answer_result = self.generate_answer_with_context(query, context_chunks, llm_service)
            
            # Save question-answer pair if user_id is provided
            if user_id:
                self.save_question_answer(query, answer_result, user_id)
            
            # Add metadata about the answer type
            if 'answer_type' not in answer_result:
                answer_result['answer_type'] = 'unknown'
            
            print(f"✅ Answer generated (type: {answer_result['answer_type']}, confidence: {answer_result['confidence']})")
            return answer_result
            
        except Exception as e:
            print(f"❌ Error processing question: {e}")
            return {
                'answer': "I'm sorry, I encountered an error while processing your question. Please try again.",
                'confidence': 0.0,
                'sources': [],
                'answer_type': 'error'
            }
    
    def generate_answer_with_context(self, query: str, context_chunks: List[Dict], llm_service) -> Dict:
        """Generate answer using retrieved context and LLM, or general knowledge if no context available"""
        try:
            if not context_chunks:
                # No curriculum content found, use general knowledge
                return self._generate_general_knowledge_answer(query, llm_service)
            
            # Prepare context
            context_text = "\n\n".join([chunk['content'] for chunk in context_chunks])
            sources = [chunk['metadata'].get('pdf_filename', 'Unknown') for chunk in context_chunks]
            
            # Calculate confidence based on relevance scores
            avg_distance = np.mean([chunk['distance'] for chunk in context_chunks])
            confidence = max(0.1, 1.0 - avg_distance)  # Higher distance = lower confidence
            
            # If confidence is too low, fall back to general knowledge
            if confidence < 0.3:
                print(f"⚠️ Low confidence ({confidence}) from curriculum content, using general knowledge")
                return self._generate_general_knowledge_answer(query, llm_service, context_chunks)
            
            # Create prompt for LLM with curriculum context
            prompt = f"""Based on the following curriculum content, please answer the student's question accurately and helpfully.

Context from curriculum:
{context_text}

Student's Question: {query}

Please provide:
1. A clear, accurate answer based on the curriculum content
2. Additional explanation if needed
3. Any important concepts the student should understand

Answer:"""
            
            # Generate answer using LLM
            answer = llm_service.generate_answer(prompt)
            
            return {
                'answer': answer,
                'confidence': round(confidence, 2),
                'sources': list(set(sources)),  # Remove duplicates
                'context_chunks': len(context_chunks),
                'answer_type': 'curriculum_based'
            }
            
        except Exception as e:
            print(f"❌ Error generating answer: {e}")
            return {
                'answer': "Sorry, I encountered an error while generating the answer. Please try again.",
                'confidence': 0.0,
                'sources': [],
                'answer_type': 'error'
            }
    
    def _generate_general_knowledge_answer(self, query: str, llm_service, context_chunks: List[Dict] = None) -> Dict:
        """Generate answer using general knowledge when no specific curriculum content is available"""
        try:
            # Create a general knowledge prompt
            if context_chunks:
                # Some context available but not very relevant
                context_text = "\n\n".join([chunk['content'] for chunk in context_chunks[:2]])  # Use only top 2 chunks
                prompt = f"""The student asked: {query}

I have some related curriculum content, but it may not be directly relevant:
{context_text}

Please provide a comprehensive answer using your general knowledge. If the curriculum content is relevant, incorporate it. If not, provide a thorough explanation based on general knowledge.

Please include:
1. A clear, accurate answer
2. Additional context and explanations
3. Related concepts that might be helpful
4. Suggestions for further learning if applicable

Answer:"""
            else:
                # No curriculum content at all
                prompt = f"""The student asked: {query}

Please provide a comprehensive answer using your general knowledge. This appears to be a general question not covered in the uploaded curriculum materials.

Please include:
1. A clear, accurate answer
2. Additional context and explanations
3. Related concepts that might be helpful
4. Suggestions for further learning if applicable

Answer:"""
            
            # Generate answer using LLM
            answer = llm_service.generate_answer(prompt)
            
            return {
                'answer': answer,
                'confidence': 0.7,  # Moderate confidence for general knowledge
                'sources': ['General Knowledge'],
                'context_chunks': len(context_chunks) if context_chunks else 0,
                'answer_type': 'general_knowledge'
            }
            
        except Exception as e:
            print(f"❌ Error generating general knowledge answer: {e}")
            return {
                'answer': "I'm sorry, I'm having trouble generating an answer right now. Please try again or rephrase your question.",
                'confidence': 0.0,
                'sources': [],
                'answer_type': 'error'
            }
    
    def save_question_answer(self, question: str, answer: Dict, user_id: str) -> bool:
        """Save question-answer pair for future reference"""
        try:
            qa_id = hashlib.md5(f"{user_id}_{question}_{datetime.now().isoformat()}".encode()).hexdigest()
            
            self.questions_collection.add(
                documents=[question],
                metadatas=[{
                    'user_id': user_id,
                    'answer': json.dumps(answer),
                    'timestamp': datetime.now().isoformat(),
                    'question_type': 'student_doubt'
                }],
                ids=[qa_id]
            )
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving Q&A: {e}")
            return False
    
    def get_user_question_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get user's question history"""
        try:
            results = self.questions_collection.query(
                query_texts=[""],  # Empty query to get all
                n_results=limit,
                where={"user_id": user_id}
            )
            
            history = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {}
                    history.append({
                        'question': doc,
                        'answer': json.loads(metadata.get('answer', '{}')),
                        'timestamp': metadata.get('timestamp', ''),
                        'id': results['ids'][0][i] if results['ids'] and results['ids'][0] else None
                    })
            
            return history
            
        except Exception as e:
            print(f"❌ Error getting question history: {e}")
            return []
    
    def delete_pdf_content(self, pdf_filename: str) -> bool:
        """Delete all content chunks for a specific PDF"""
        try:
            # Get all documents for this PDF
            results = self.content_collection.query(
                query_texts=[""],
                n_results=1000,
                where={"pdf_filename": pdf_filename}
            )
            
            if results['ids'] and results['ids'][0]:
                # Delete by IDs
                self.content_collection.delete(ids=results['ids'][0])
                print(f"✅ Deleted {len(results['ids'][0])} chunks for {pdf_filename}")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error deleting PDF content: {e}")
            return False
    
    def get_database_stats(self) -> Dict:
        """Get vector database statistics"""
        try:
            content_count = self.content_collection.count()
            questions_count = self.questions_collection.count()
            
            return {
                'total_content_chunks': content_count,
                'total_questions': questions_count,
                'embedding_model': 'all-MiniLM-L6-v2' if self.embedding_model else 'Not loaded',
                'database_path': self.db_path
            }
            
        except Exception as e:
            print(f"❌ Error getting database stats: {e}")
            return {}
    
    def get_subject_stats(self) -> Dict:
        """Get statistics for each subject collection"""
        stats = {}
        for subject in self.subjects:
            collection = self.subject_collections[subject]
            stats[subject] = {
                'chunks': collection.count(),
                'collection_name': f"subject_{subject}"
            }
        
        # Add unified collection stats
        stats['unified'] = {
            'chunks': self.unified_collection.count(),
            'collection_name': 'unified_knowledge'
        }
        
        return stats
    
    def search_across_subjects(self, query: str, subjects: List[str] = None, top_k: int = 5) -> Dict:
        """Search across multiple subjects and return combined results"""
        if not subjects:
            subjects = self.subjects
        
        all_results = {}
        
        for subject in subjects:
            if subject.lower() in self.subjects:
                results = self.search_relevant_content(query, top_k, subject=subject)
                all_results[subject] = results
        
        # Combine and rank results
        combined_results = []
        for subject, results in all_results.items():
            for result in results:
                result['subject'] = subject
                combined_results.append(result)
        
        # Sort by distance (lower is better)
        combined_results.sort(key=lambda x: x.get('distance', 1.0))
        
        return {
            'query': query,
            'subjects_searched': subjects,
            'results': combined_results[:top_k],
            'subject_breakdown': {subject: len(results) for subject, results in all_results.items()}
        }
    
    def classify_subject(self, text: str) -> str:
        """Classify the subject of a text based on keywords"""
        subject_keywords = {
            'mathematics': ['equation', 'formula', 'calculate', 'solve', 'number', 'math', 'algebra', 'geometry', 'trigonometry'],
            'science': ['experiment', 'hypothesis', 'theory', 'molecule', 'atom', 'chemical', 'physics', 'biology', 'chemistry'],
            'history': ['ancient', 'century', 'war', 'king', 'queen', 'empire', 'civilization', 'historical', 'past'],
            'geography': ['country', 'continent', 'ocean', 'mountain', 'river', 'climate', 'population', 'map', 'location'],
            'english': ['grammar', 'literature', 'poem', 'novel', 'sentence', 'vocabulary', 'writing', 'reading'],
            'hindi': ['हिंदी', 'कविता', 'कहानी', 'व्याकरण', 'साहित्य', 'भाषा']
        }
        
        text_lower = text.lower()
        subject_scores = {}
        
        for subject, keywords in subject_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            subject_scores[subject] = score
        
        # Return subject with highest score
        if subject_scores:
            return max(subject_scores, key=subject_scores.get)
        
        return 'general'  # Default if no clear subject

# Global instance
rag_service = RAGService("../vector_db") 
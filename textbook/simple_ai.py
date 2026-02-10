# textbook/simple_ai.py
import re
import random

class SimpleAI:
    def process_document(self, text, filename):
        """Basic document processing without AI"""
        print(f"DEBUG: SimpleAI processing document, text length: {len(text)}")
        
        # Create a simple summary
        if len(text) > 200:
            summary = f"Document summary: This {filename} contains educational content. " + text[:100] + "..."
        else:
            summary = f"Document: {filename}. Content ready for study."
        
        # Create simplified text (just truncate for now)
        if len(text) > 1500:
            simplified = text[:1000] + "\n\n[Content shortened for better studying. Full text available in original document.]"
        else:
            simplified = text
        
        print(f"DEBUG: SimpleAI processing complete")
        
        return {
            'success': True,
            'summary': summary,
            'simplified_text': simplified,
            'processed': True
        }
    
    def chat_with_document(self, text, question, chat_history=None):
        """Simple rule-based responses"""
        print(f"DEBUG: SimpleAI chat - Question: {question}")
        
        question_lower = question.lower()
        
        # Simple responses based on question type
        if any(word in question_lower for word in ['what', 'explain', 'tell me']):
            return "Based on the document content, this appears to explain important concepts that you should study carefully. I recommend taking notes on the key points."
        
        elif any(word in question_lower for word in ['how', 'method', 'process']):
            return "The document describes a process or method. Break it down into steps for better understanding and practice each part separately."
        
        elif any(word in question_lower for word in ['why', 'reason', 'purpose']):
            return "Understanding the purpose and reasoning in this document will help you grasp the underlying concepts more deeply."
        
        elif any(word in question_lower for word in ['hi', 'hello', 'hey']):
            return "Hello! I can help you study this document. Ask me questions about the content, or request explanations of specific parts."
        
        else:
            responses = [
                "This document contains valuable information for your studies. What specific aspect would you like to discuss?",
                "I can help you understand this material better. Try asking about specific concepts or sections.",
                "The content seems relevant to your learning goals. Let me know what part you'd like to focus on.",
                "This appears to be educational content. I recommend creating summaries and practice questions as you study."
            ]
            return random.choice(responses)
    
    def generate_quiz_questions(self, text, num_questions=3):
        """Generate simple quiz questions"""
        questions = []
        for i in range(num_questions):
            questions.append({
                'question': f'What is the main purpose of this document?',
                'options': {
                    'A': 'To provide educational content',
                    'B': 'To explain key concepts', 
                    'C': 'To help with learning',
                    'D': 'All of the above'
                },
                'answer': 'D'
            })
        return questions

simple_ai = SimpleAI()
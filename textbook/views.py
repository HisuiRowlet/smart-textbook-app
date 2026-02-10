import os
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .forms import UploadForm, CustomUserCreationForm, NoteForm, NotebookForm
from .models import UploadedDocument, Lesson, Quiz, UserProgress, DocumentChat, Note, Notebook
from PyPDF2 import PdfReader
import docx
import logging
from django.utils import timezone
from datetime import timedelta
from .models import PomodoroSession
import threading
from django.db import transaction
from django.db.models import Q 

logger = logging.getLogger(__name__)

# ===== TEXT EXTRACTION FUNCTION =====
def extract_text_from_file(path):
    ext = os.path.splitext(path)[1].lower()
    text = ""
    
    try:
        if ext == '.pdf':
            text = []
            reader = PdfReader(path)
            for p in reader.pages:
                text.append(p.extract_text() or '')
            text = "\n".join(text)
            
        elif ext in ('.docx', '.doc'):
            doc = docx.Document(path)
            text = "\n".join([p.text for p in doc.paragraphs])
            
        elif ext in ('.txt',):
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
                
        else:
            text = f"Unsupported file format: {ext}"
            
    except Exception as e:
        logger.exception(f"Error extracting text from {path}")
        text = f"Error extracting text: {str(e)}"
        
    return text

# ===== AUTHENTICATION VIEWS =====
def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Login successful!')
            return redirect('textbook:home')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'textbook/login.html')

def custom_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('textbook:login')

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('textbook:home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'textbook/signup.html', {'form': form})

from django.db.models import Q  # Add this import at the top

def home(request):
    # Get user's uploads
    uploads = None
    lessons = Lesson.objects.none()  # Start with empty queryset
    
    if request.user.is_authenticated:
        uploads = UploadedDocument.objects.filter(user=request.user).order_by('-uploaded_at')[:5]
        
        # Only show lessons that belong to this user OR are pre-made (no user)
        lessons = Lesson.objects.filter(
            Q(user=request.user) | Q(user__isnull=True)  # Use Q instead of models.Q
        ).order_by('order')
    
    return render(request, 'textbook/home.html', {
        'lessons': lessons, 
        'uploads': uploads
    })
# REPLACE the existing upload_document function with this:
@login_required
def upload_document(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.user = request.user
            doc.save()

            try:
                # Extract text
                text = extract_text_from_file(doc.file.path)
                print(f"DEBUG: Raw extracted text length: {len(text)}")
                print(f"DEBUG: First 200 chars: {text[:200]}")
                
                doc.extracted_text = text[:100000]
                doc.save()
                
                # Check if text was actually extracted
                if not text or len(text.strip()) < 10:
                    print("DEBUG: No substantial text extracted!")
                    messages.warning(request, 'File uploaded, but no readable text was found for processing.')
                    return redirect('textbook:home')
                
                print(f"DEBUG: Text extraction successful, {len(text)} characters")
                
                # Use SIMPLE AI instead of background thread for now
                from .simple_ai import simple_ai
                ai_results = simple_ai.process_document(text, doc.file.name)
                
                if ai_results['success']:
                    doc.summary = ai_results['summary']
                    doc.simplified_text = ai_results['simplified_text']
                    doc.save()
                    messages.success(request, 'File uploaded and processed successfully!')
                    print(f"DEBUG: Document processed successfully - ID: {doc.id}")
                else:
                    messages.warning(request, 'File uploaded but AI processing failed.')
                
            except Exception as e:
                logger.exception("Document processing failed")
                print(f"DEBUG: Exception in upload: {str(e)}")
                messages.error(request, f'Upload failed: {str(e)}')
                
            return redirect('textbook:home')
    else:
        form = UploadForm()
    return render(request, 'textbook/upload.html', {'form': form})

def create_lesson_from_upload(uploaded_doc):
    """Create a Lesson from an uploaded document"""
    try:
        # Create lesson title from filename
        title = uploaded_doc.file.name.split('/')[-1]  # Get filename
        title = title.replace('.pdf', '').replace('.docx', '').replace('.doc', '').replace('_', ' ')
        title = title.title()  # Capitalize words
        
        # Use simplified text if available, otherwise use extracted text
        content = uploaded_doc.simplified_text if uploaded_doc.simplified_text else uploaded_doc.extracted_text
        
        if not content or len(content.strip()) < 10:
            print(f"DEBUG: Not enough content for lesson from upload {uploaded_doc.id}")
            return None
        
        # Create the lesson with user and uploaded_document reference
        lesson = Lesson.objects.create(
            title=title,
            content=content[:5000],  # Limit content length
            order=Lesson.objects.count() + 1,  # Add to end
            user=uploaded_doc.user,  # Set the user
            uploaded_document=uploaded_doc  # Link to the upload
        )
        
        print(f"DEBUG: Successfully created lesson: {lesson.title} (ID: {lesson.id}) for user {uploaded_doc.user.username}")
        
        # Create quizzes for the lesson
        create_quiz_for_lesson(lesson, content)
        
        return lesson
        
    except Exception as e:
        print(f"DEBUG: Failed to create lesson from upload {uploaded_doc.id}: {str(e)}")
        return None

# REPLACE the existing create_quiz_for_lesson function with this:
def create_quiz_for_lesson(lesson, content):
    """Create AI-generated quizzes for a lesson"""
    try:
        # Lazy import
        from .ai_processor import ai_processor
        # Use AI to generate quiz questions
        quiz_questions = ai_processor.generate_quiz_questions(content, num_questions=3)
        
        for i, q_data in enumerate(quiz_questions):
            if q_data and 'question' in q_data and 'options' in q_data and 'answer' in q_data:
                Quiz.objects.create(
                    lesson=lesson,
                    question=q_data['question'],
                    options=q_data['options'],
                    answer=q_data['answer']
                )
        
        print(f"DEBUG: Created {Quiz.objects.filter(lesson=lesson).count()} AI-generated quizzes for lesson {lesson.id}")
        
    except Exception as e:
        print(f"DEBUG: Failed to create AI quizzes: {str(e)}")
        # Fallback to sample quizzes
        create_sample_quizzes(lesson)

# ADD this new function to textbook/views.py
def create_sample_quizzes(lesson):
    """Create sample quizzes as fallback"""
    sample_quizzes = [
        {
            'question': 'What is the main purpose of this document?',
            'options': {
                'A': 'To provide entertainment',
                'B': 'To educate and inform',
                'C': 'To sell a product', 
                'D': 'To tell a story'
            },
            'answer': 'B'
        },
        {
            'question': 'Which study method would be most effective for this material?',
            'options': {
                'A': 'Skimming quickly',
                'B': 'Active reading and note-taking',
                'C': 'Memorization only',
                'D': 'Reading once without review'
            },
            'answer': 'B'
        }
    ]
    
    for quiz_data in sample_quizzes:
        Quiz.objects.create(
            lesson=lesson,
            question=quiz_data['question'],
            options=quiz_data['options'],
            answer=quiz_data['answer']
        )

# DELETE the old process_with_ai_ollama function and REPLACE with this:
def process_with_ai_ollama(text, document):
    """Use the new AI processor for document processing"""
    try:
        # Lazy import to avoid circular imports
        from .ai_processor import ai_processor
        return ai_processor.process_document(text, document.file.name)
    except Exception as e:
        return {
            'success': False,
            'summary': f"AI processing error: {str(e)}",
            'simplified_text': f"AI processing error: {str(e)}",
            # REMOVED: 'key_concepts': f"AI processing error: {str(e)}",
            'processed': False
        }

@login_required
def delete_upload(request, upload_id):
    upload = get_object_or_404(UploadedDocument, id=upload_id, user=request.user)
    
    if request.method == 'POST':
        # Delete the actual file from storage
        if upload.file:
            if os.path.isfile(upload.file.path):
                os.remove(upload.file.path)
        
        upload.delete()
        messages.success(request, 'Upload deleted successfully!')
        return redirect('textbook:home')
    
    return render(request, 'textbook/confirm_delete.html', {'upload': upload})

def lesson_view(request, lesson_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    quizzes = lesson.quizzes.all()
    progress = None
    
    if request.user.is_authenticated:
        progress, created = UserProgress.objects.get_or_create(user=request.user, lesson=lesson)
    
    # Debug: Print quiz data to console
    print(f"DEBUG: Found {quizzes.count()} quizzes for lesson {lesson.title}")
    for quiz in quizzes:
        print(f"DEBUG: Quiz {quiz.id} - Options: {quiz.options}")
    
    return render(request, 'textbook/lesson.html', {
        'lesson': lesson,
        'quizzes': quizzes,  # Pass the Quiz objects directly
        'progress': progress
    })

def testollama(request):
    """Test if Ollama is working"""
    print("DEBUG: Testing Ollama connection...")
    
    try:
        # Test if Ollama is running
        test_response = requests.get('http://localhost:11434/api/tags', timeout=5)
        
        if test_response.status_code == 200:
            # Test the generate endpoint
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': 'llama2:latest',
                    'prompt': 'Just say "Hello from Ollama!" and nothing else.',
                    'stream': False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                test_result = result['response']
                status = "SUCCESS"
                print("DEBUG: Ollama test SUCCESS!")
            else:
                test_result = f"Generate failed: {response.status_code}"
                status = "GENERATE_ERROR"
                print(f"DEBUG: Generate error: {response.status_code}")
        else:
            test_result = f"Cannot connect: {test_response.status_code}"
            status = "CONNECTION_FAILED"
            print(f"DEBUG: Connection failed: {test_response.status_code}")
            
    except requests.exceptions.ConnectionError:
        test_result = "Cannot connect to Ollama. Make sure it's running on localhost:11434"
        status = "CONNECTION_ERROR"
        print("DEBUG: Connection error - Ollama not running")
    except Exception as e:
        test_result = f"Error: {str(e)}"
        status = "FAILED"
        print(f"DEBUG: Exception: {str(e)}")
    
    return render(request, 'textbook/test_ollama.html', {
        'test_result': test_result,
        'status': status
    })

# ===== NOTEBOOK VIEWS =====
@login_required
def notebook_list(request):
    notebooks = Notebook.objects.filter(user=request.user)
    notes = Note.objects.filter(user=request.user)
    
    context = {
        'notebooks': notebooks,
        'notes': notes,
    }
    return render(request, 'textbook/notebook_list.html', context)

@login_required
def create_notebook(request):
    if request.method == 'POST':
        form = NotebookForm(request.POST)
        if form.is_valid():
            notebook = form.save(commit=False)
            notebook.user = request.user
            notebook.save()
            messages.success(request, 'Notebook created successfully!')
            return redirect('textbook:notebook_list')
    else:
        form = NotebookForm()
    return render(request, 'textbook/create_notebook.html', {'form': form})

# ===== NOTE VIEWS =====
@login_required
def create_note(request):
    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.save()
            messages.success(request, 'Note created successfully!')
            return redirect('textbook:notebook_list')
    else:
        form = NoteForm()
    
    return render(request, 'textbook/create_notebook.html', {'form': form})

@login_required
def edit_note(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    
    if request.method == 'POST':
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, 'Note updated successfully!')
            return redirect('textbook:notebook_list')
    else:
        form = NoteForm(instance=note)
    
    return render(request, 'textbook/edit_note.html', {'form': form, 'note': note})

@login_required
def delete_note(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Note deleted successfully!')
        return redirect('textbook:notebook_list')
    
    return render(request, 'textbook/delete_note.html', {'note': note})

@login_required
def note_detail(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    return render(request, 'textbook/note_detail.html', {'note': note})

# ===== POMODORO VIEWS =====
@login_required
def pomodoro_timer(request):
    """Main Pomodoro timer page"""
    # Get user's recent Pomodoro sessions
    recent_sessions = PomodoroSession.objects.filter(user=request.user).order_by('-start_time')[:10]
    
    # Get today's completed sessions
    today = timezone.now().date()
    today_sessions = PomodoroSession.objects.filter(
        user=request.user,
        start_time__date=today,
        completed=True
    )
    
    # Calculate today's focus time
    today_focus_minutes = sum(
        session.duration_minutes 
        for session in today_sessions 
        if session.session_type == 'WORK'
    )
    
    # Get user's lessons for dropdown
    lessons = Lesson.objects.all()
    
    context = {
        'recent_sessions': recent_sessions,
        'today_focus_minutes': today_focus_minutes,
        'today_session_count': today_sessions.count(),
        'lessons': lessons,
    }
    return render(request, 'textbook/pomodoro_timer.html', context)

@login_required
def start_pomodoro_session(request):
    """Start a new Pomodoro session"""
    if request.method == 'POST':
        session_type = request.POST.get('session_type', 'WORK')
        duration = int(request.POST.get('duration', 25))
        lesson_id = request.POST.get('lesson_id')
        
        lesson = None
        if lesson_id:
            lesson = get_object_or_404(Lesson, id=lesson_id)
        
        # Create new Pomodoro session
        session = PomodoroSession.objects.create(
            user=request.user,
            duration_minutes=duration,
            session_type=session_type,
            lesson=lesson
        )
        
        messages.success(request, f'Started {duration} minute {session_type.replace("_", " ").title()} session!')
        return redirect('textbook:pomodoro_timer')
    
    return redirect('textbook:pomodoro_timer')

@login_required
def complete_pomodoro_session(request, session_id):
    """Mark a Pomodoro session as completed"""
    session = get_object_or_404(PomodoroSession, id=session_id, user=request.user)
    
    if not session.completed:
        session.completed = True
        session.end_time = timezone.now()
        session.save()
        
        messages.success(request, f'Great job! Completed {session.duration_minutes} minute {session.get_session_type_display()} session.')
    
    return redirect('textbook:pomodoro_timer')

@login_required
def pomodoro_stats(request):
    """Show Pomodoro statistics"""
    # Get time range (last 7 days)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=7)
    
    sessions = PomodoroSession.objects.filter(
        user=request.user,
        start_time__range=[start_date, end_date],
        completed=True
    )
    
    # Calculate statistics
    total_sessions = sessions.count()
    total_focus_time = sum(
        session.duration_minutes 
        for session in sessions 
        if session.session_type == 'WORK'
    )
    work_sessions = sessions.filter(session_type='WORK').count()
    break_sessions = sessions.filter(session_type__in=['SHORT_BREAK', 'LONG_BREAK']).count()
    
    # Daily breakdown
    daily_stats = []
    for i in range(7):
        day = start_date + timedelta(days=i)
        day_sessions = sessions.filter(start_time__date=day)
        day_focus = sum(
            session.duration_minutes 
            for session in day_sessions 
            if session.session_type == 'WORK'
        )
        daily_stats.append({
            'date': day,
            'sessions': day_sessions.count(),
            'focus_minutes': day_focus
        })
    
    context = {
        'total_sessions': total_sessions,
        'total_focus_time': total_focus_time,
        'work_sessions': work_sessions,
        'break_sessions': break_sessions,
        'daily_stats': daily_stats,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'textbook/pomodoro_stats.html', context)

# ===== DOCUMENT VIEWS =====
@login_required
def document_detail(request, document_id):
    """View for individual document with simplified text and chat"""
    document = get_object_or_404(UploadedDocument, id=document_id, user=request.user)
    chat_messages = DocumentChat.objects.filter(document=document, user=request.user).order_by('created_at')
    
    # Debug info
    print(f"DEBUG: Document ID: {document.id}")
    print(f"DEBUG: Has extracted_text: {bool(document.extracted_text)}")
    print(f"DEBUG: Has simplified_text: {bool(document.simplified_text)}")
    print(f"DEBUG: Extracted text length: {len(document.extracted_text or '')}")
    print(f"DEBUG: Simplified text length: {len(document.simplified_text or '')}")
    
    # If no simplified text, use extracted text as fallback
    if not document.simplified_text and document.extracted_text:
        document.simplified_text = document.extracted_text[:1000] + "... [Content not fully processed]"
        document.save()
    
    # Handle chat messages
    if request.method == 'POST' and 'message' in request.POST:
        user_message = request.POST.get('message', '').strip()
        
        if user_message:
            print(f"DEBUG: Chat message received: {user_message}")
            
            # Save user message
            user_chat = DocumentChat.objects.create(
                document=document,
                user=request.user,
                message=user_message,
                is_user_message=True
            )
            
            # Get AI response using SimpleAI
            try:
                from .simple_ai import simple_ai
                
                # Use available text
                text_content = document.extracted_text or document.simplified_text or "Educational document content"
                ai_response = simple_ai.chat_with_document(text_content, user_message)
                
                # Save AI response
                DocumentChat.objects.create(
                    document=document,
                    user=request.user,
                    message=ai_response,
                    is_user_message=False
                )
                
            except Exception as e:
                print(f"DEBUG: Chat error: {str(e)}")
                DocumentChat.objects.create(
                    document=document,
                    user=request.user,
                    message="I'm here to help you study this document. What would you like to know?",
                    is_user_message=False
                )
            
            return redirect('textbook:document_detail', document_id=document_id)
    
    return render(request, 'textbook/document_detail.html', {
        'document': document,
        'chat_messages': chat_messages
    })

def ai_status(request):
    """Check AI system status"""
    try:
        # Lazy import to avoid circular imports
        from .ai_processor import ai_processor
        status = {
            'ollama_available': ai_processor.client.is_available(),
            'available_models': ai_processor.client.available_models,
            'default_model': ai_processor.client.get_default_model(),
        }
    except Exception as e:
        status = {
            'ollama_available': False,
            'available_models': [],
            'default_model': 'Unknown',
            'error': str(e)
        }
    
    return render(request, 'textbook/ai_status.html', {'status': status})

def setup_guide(request):
    """Show Ollama setup instructions"""
    return render(request, 'textbook/setup_guide.html')

def test_ai_processing(request, document_id):
    """Test if AI processing works for a document"""
    document = get_object_or_404(UploadedDocument, id=document_id, user=request.user)
    
    print(f"DEBUG: Document ID: {document.id}")
    print(f"DEBUG: Has extracted text: {bool(document.extracted_text)}")
    print(f"DEBUG: Has simplified text: {bool(document.simplified_text)}")
    print(f"DEBUG: Extracted text length: {len(document.extracted_text or '')}")
    
    # Test AI processor
    from .ai_processor import ai_processor
    status = ai_processor.get_status()
    print(f"DEBUG: AI Status: {status}")
    
    # Test a simple chat
    if document.extracted_text:
        test_response = ai_processor.chat_with_document(
            text=document.extracted_text,
            question="What is this document about?",
            chat_history=[]
        )
        print(f"DEBUG: Test AI response: {test_response}")
    
    return redirect('textbook:document_detail', document_id=document_id)

def test_ai_directly(request):
    """Test the AI processor directly"""
    from .ai_processor import ai_processor
    
    print("=== TESTING AI PROCESSOR ===")
    
    # Test 1: Check status
    status = ai_processor.get_status()
    print(f"Status: {status}")
    
    # Test 2: Simple completion
    print("Testing simple completion...")
    test_prompt = "Just say 'Hello, AI is working!' and nothing else."
    response = ai_processor.client.generate_completion(test_prompt)
    print(f"Simple completion response: {response}")
    
    # Test 3: Chat with document
    print("Testing chat with document...")
    test_text = "This is a test document about machine learning. Machine learning is a subset of artificial intelligence that allows computers to learn without being explicitly programmed."
    test_question = "What is machine learning?"
    
    chat_response = ai_processor.chat_with_document(
        text=test_text,
        question=test_question,
        chat_history=[]
    )
    print(f"Chat response: {chat_response}")
    
    print("=== AI TEST COMPLETE ===")
    
    return render(request, 'textbook/test_ai.html', {
        'status': status,
        'simple_response': response,
        'chat_response': chat_response
    })
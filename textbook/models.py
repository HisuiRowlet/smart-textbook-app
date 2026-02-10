from django.db import models
from django.contrib.auth.models import User

class Notebook(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200, default="Untitled Notebook")
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#4361ee')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Note(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title

class Lesson(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Add this
    uploaded_document = models.ForeignKey('UploadedDocument', on_delete=models.CASCADE, null=True, blank=True)  # Add this

    def __str__(self):
        return self.title

class UploadedDocument(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    extracted_text = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    simplified_text = models.TextField(blank=True)  
    # REMOVED: key_concepts = models.TextField(blank=True)    

    def __str__(self):
        return f"{self.file.name} by {self.user.username}"

class DocumentChat(models.Model):  
    document = models.ForeignKey(UploadedDocument, on_delete=models.CASCADE, related_name='chats')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    is_user_message = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Chat for {self.document.file.name}"

class Quiz(models.Model):
    
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='quizzes')
    question = models.TextField()
    options = models.JSONField()
    answer = models.CharField(max_length=10)

    def __str__(self):
        return f"Q: {self.question[:40]}..."

class UserProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    score = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'lesson')

# ===== POMODORO MODEL =====
class PomodoroSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=25)
    session_type = models.CharField(
        max_length=20,
        choices=[
            ('WORK', 'Work Session'),
            ('SHORT_BREAK', 'Short Break'), 
            ('LONG_BREAK', 'Long Break')
        ],
        default='WORK'
    )
    completed = models.BooleanField(default=False)
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-start_time']
    
    def __str__(self):
        return f"{self.user.username} - {self.session_type} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
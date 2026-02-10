from django.contrib import admin
from .models import Lesson, UploadedDocument, Quiz, UserProgress

admin.site.register(Lesson)
admin.site.register(UploadedDocument)
admin.site.register(Quiz)
admin.site.register(UserProgress)

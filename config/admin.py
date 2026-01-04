from django.contrib import admin
from .models import BookDedication, BookCover, BookPageQuestion, BookPageAnswer, Book
from django.utils.html import format_html

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'status', 'created_at']
    list_filter = ['status']


@admin.register(BookDedication)
class BookDedicationAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


@admin.register(BookCover)
class BookCoverAdmin(admin.ModelAdmin):
    list_display = ('title', 'author_book', 'template', 'cover_preview')
    readonly_fields = ('cover_preview',)

    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" style="max-height: 200px; max-width: 200px;" />', obj.cover_image.url)
        return "(No preview)"

    cover_preview.short_description = "Preview"


@admin.register(BookPageQuestion)
class BookPageQuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'short_quiz', 'dedication')
    search_fields = ('quiz',)
    list_filter = ('dedication',)

    def short_quiz(self, obj):
        return obj.quiz[:50]

    short_quiz.short_description = "Вопрос"


@admin.register(BookPageAnswer)
class BookPageAnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'quiz', 'short_answer')
    search_fields = ('answer',)
    list_filter = ('user',)

    def short_answer(self, obj):
        return obj.answer[:50]

    short_answer.short_description = "Ответ"
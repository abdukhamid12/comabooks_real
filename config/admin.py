from django.contrib import admin
from .models import BookDedication, BookTemplate, BookCover
from django.utils.html import format_html


@admin.register(BookDedication)
class BookDedicationAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


@admin.register(BookTemplate)
class BookTemplateAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'image']
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

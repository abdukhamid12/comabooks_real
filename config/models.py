from django.db import models
from django.contrib.auth.models import AbstractUser
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from django.core.files.base import ContentFile
from django.utils.safestring import mark_safe


# 1. Custom foydalanuvchi modeli
class CustomUser(AbstractUser):
    phone = models.CharField(max_length=13)
    telegram_username_or_phone = models.CharField(max_length=150, blank=True, null=True)

    def __str__(self):
        return self.username


# 2. Kitob bag'ishlov (dedication)
class BookDedication(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


# 3. Shablon rasmlar
class BookTemplate(models.Model):
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to='templates/')

    def __str__(self):
        return self.name


# 4. Kitob jildi / tanlangan dizayn va muallif
class BookCover(models.Model):
    title = models.CharField(max_length=255)
    author_book = models.CharField(max_length=255)
    dedication = models.TextField(blank=True)
    template = models.CharField(max_length=50)
    cover_image = models.ImageField(upload_to="covers/", blank=True, null=True)

    def cover_preview(self):
        if self.cover_image:
            return mark_safe(f'<img src="{self.cover_image}" style="height: 300px; border: 1px solid #ccc;" />')
        return "Нет изображения"

    cover_preview.short_description = "Превью обложки"
    cover_preview.allow_tags = True


# 5. Kitobdagi har bir sahifaga savollar
class BookPageQuestion(models.Model):
    quiz = models.TextField()

    def __str__(self):
        return f"Quiz: {self.quiz[:30]}..."


# 6. Foydalanuvchining sahifaga yozgan javobi
class BookPageAnswer(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    quiz = models.ForeignKey(BookPageQuestion, on_delete=models.CASCADE)
    answer = models.TextField()
    image = models.ImageField(upload_to='bookpage/', blank=True, null=True)

    def __str__(self):
        return f"Answer by {self.user.username} to quiz {self.quiz.id}"

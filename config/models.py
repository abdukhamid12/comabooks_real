from django.db import models
from django.contrib.auth.models import AbstractUser

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
    title = models.CharField(max_length=200)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    author_book = models.CharField(max_length=255, blank=True, null=True)  # optional
    dedication = models.ForeignKey(BookDedication, on_delete=models.SET_NULL, null=True)
    template = models.ForeignKey(BookTemplate, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.title


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
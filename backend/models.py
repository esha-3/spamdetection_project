from django.db import models

class SpamRecord(models.Model):
    message_text = models.TextField()
    verdict = models.CharField(max_length=20) # 'spam', 'safe', 'unknown'
    confidence = models.FloatField()          # confidence percentage
    explanation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.verdict.upper()} ({self.confidence}%): {self.message_text[:30]}..."

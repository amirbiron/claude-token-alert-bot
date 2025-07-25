# Claude Session Alert Bot

בוט טלגרם שמזכיר למשתמש 10 ו-5 דקות לפני סיום שיחה עם Claude.

## שינויים חדשים - Web Service

הבוט שונה מ-background worker ל-web service שיישן עד שיקבל פקודה מהמשתמש.

### מה השתנה:

1. **Web Service במקום Worker**: הבוט כעת רץ כ-web service עם Flask
2. **Webhook במקום Polling**: הבוט מקבל עדכונים דרך webhook מטלגרם במקום polling מתמיד
3. **חיסכון במשאבים**: הבוט יישן כאשר אין פעילות ויתעורר רק כשמגיעה פקודה

### הגדרה:

1. הגדר את משתני הסביבה:
   - `TELEGRAM_BOT_TOKEN`: טוקן הבוט מ-BotFather
   - `WEBHOOK_URL`: כתובת השירות (לדוגמה: https://your-app.onrender.com)

2. הבוט יגדיר אוטומטית webhook ב-Telegram

### Endpoints:

- `/webhook` - מקבל עדכונים מטלגרם
- `/health` - בדיקת בריאות השירות
- `/` - עמוד בית פשוט

### פקודות:

- `/start` - הודעת ברוכים הבאים
- `/start_session <דקות>` - התחלת מעקב שיחה

### דוגמה:
```
/start_session 30
```
יתחיל מעקב של 30 דקות עם התראות ב-20 ו-25 דקות.
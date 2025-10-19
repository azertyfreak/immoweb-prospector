# 🏠 Immoweb Prospectie Tool

Automatische monitoring van nieuwe panden op Immoweb.be met intelligente notificaties.

## ✨ Features

- ✅ Automatische monitoring van Immoweb
- 📧 Email notificaties bij nieuwe panden
- 🔍 Configureerbare zoekopdrachten
- 🎯 Filter op particuliere verkopers
- 📊 Dashboard met statistieken
- 🌐 Web interface

## 🚀 Deployment op Replit

### Stap 1: Import vanuit GitHub
1. Ga naar [Replit.com](https://replit.com)
2. Klik "Create Repl" → "Import from GitHub"
3. Plak je repository URL
4. Klik "Import from GitHub"

### Stap 2: Environment Variables
Klik op 🔒 "Secrets" en voeg toe:

| Key | Value |
|-----|-------|
| SECRET_KEY | een-lange-random-string |
| EMAIL_FROM | jouw@gmail.com |
| EMAIL_PASSWORD | jouw-app-password |
| EMAIL_TO | ontvanger@email.com |
| EMAIL_ENABLED | 1 |
| CHECK_INTERVAL | 60 |

### Stap 3: Gmail Setup
1. Ga naar [Google Account Security](https://myaccount.google.com/security)
2. Schakel 2-Factor Authentication in
3. Ga naar "App Passwords"
4. Genereer nieuw app password voor "Mail"
5. Gebruik dit in EMAIL_PASSWORD

### Stap 4: Run!
Klik op de groene "Run" knop

## 💡 Gebruik

1. **Zoekopdracht toevoegen**: Ga naar "Zoekopdrachten" → configureer parameters
2. **Email instellen**: Ga naar "Instellingen" → vul Gmail credentials in
3. **Monitoren**: Dashboard toont automatisch nieuwe vondsten

## 🛠️ Tech Stack

- Flask 3.0
- SQLite
- APScheduler
- BeautifulSoup4
- SMTP (Gmail)

## ⚠️ Disclaimer

Voor educatieve doeleinden. Gebruik op eigen risico. Respecteer Immoweb's gebruiksvoorwaarden.

## 📄 Licentie

Proprietary - Contact voor commerciële licentie

---

**Made with ❤️ in Belgium**

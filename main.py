import os
import json
import sqlite3
import requests
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
import hashlib
import time
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
Config.init_app(app)

# Database initialization
def init_db():
    conn = sqlite3.connect(app.config['DATABASE_NAME'])
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS properties
                 (id TEXT PRIMARY KEY, 
                  url TEXT,
                  title TEXT,
                  price TEXT,
                  location TEXT,
                  seller_type TEXT,
                  first_seen TIMESTAMP,
                  notified INTEGER DEFAULT 0)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS search_configs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  province TEXT,
                  property_type TEXT,
                  min_price INTEGER,
                  max_price INTEGER,
                  seller_type TEXT,
                  active INTEGER DEFAULT 1)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (key TEXT PRIMARY KEY,
                  value TEXT)''')
    
    # Insert default settings if not exist
    c.execute("INSERT OR IGNORE INTO settings VALUES ('email_enabled', '0')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('email_from', '')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('email_password', '')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('email_to', '')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('check_interval', '60')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('last_check', '')")
    
    conn.commit()
    conn.close()

init_db()

# HTML Templates
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Immoweb Prospectie Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; background: #f5f7fa; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header h1 { font-size: 2rem; margin-bottom: 0.5rem; }
        .header p { opacity: 0.9; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .nav { display: flex; gap: 1rem; margin-bottom: 2rem; flex-wrap: wrap; }
        .nav a { padding: 0.75rem 1.5rem; background: white; color: #667eea; text-decoration: none; border-radius: 8px; font-weight: 600; transition: all 0.3s; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .nav a:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
        .stat-card { background: white; padding: 1.5rem; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .stat-card h3 { color: #64748b; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }
        .stat-card .value { font-size: 2rem; font-weight: 700; color: #1e293b; }
        .properties { background: white; border-radius: 12px; padding: 1.5rem; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .properties h2 { margin-bottom: 1.5rem; color: #1e293b; }
        .property-card { border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem; transition: all 0.3s; }
        .property-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); transform: translateY(-2px); }
        .property-card h3 { color: #1e293b; margin-bottom: 0.5rem; font-size: 1.125rem; }
        .property-meta { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 0.75rem; font-size: 0.875rem; color: #64748b; }
        .property-meta span { background: #f1f5f9; padding: 0.25rem 0.75rem; border-radius: 4px; }
        .property-link { display: inline-block; margin-top: 0.75rem; padding: 0.5rem 1rem; background: #667eea; color: white; text-decoration: none; border-radius: 6px; font-size: 0.875rem; transition: all 0.3s; }
        .property-link:hover { background: #5568d3; }
        .badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
        .badge-new { background: #dcfce7; color: #166534; }
        .badge-notified { background: #dbeafe; color: #1e40af; }
        .empty-state { text-align: center; padding: 3rem; color: #94a3b8; }
        .empty-state svg { width: 64px; height: 64px; margin-bottom: 1rem; opacity: 0.5; }
        @media (max-width: 768px) {
            .container { padding: 1rem; }
            .header { padding: 1.5rem; }
            .nav { gap: 0.5rem; }
            .nav a { padding: 0.5rem 1rem; font-size: 0.875rem; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>🏠 Immoweb Prospectie</h1>
            <p>Automatische monitoring van nieuwe panden</p>
        </div>
    </div>
    
    <div class="container">
        <div class="nav">
            <a href="/">Dashboard</a>
            <a href="/searches">Zoekopdrachten</a>
            <a href="/settings">Instellingen</a>
            <a href="/run-check">Check Nu</a>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>Totaal Gevonden</h3>
                <div class="value">{{ total_properties }}</div>
            </div>
            <div class="stat-card">
                <h3>Nieuwe (niet genotificeerd)</h3>
                <div class="value">{{ new_properties }}</div>
            </div>
            <div class="stat-card">
                <h3>Actieve Zoekopdrachten</h3>
                <div class="value">{{ active_searches }}</div>
            </div>
            <div class="stat-card">
                <h3>Laatste Check</h3>
                <div class="value" style="font-size: 1rem;">{{ last_check or 'Nog niet uitgevoerd' }}</div>
            </div>
        </div>
        
        <div class="properties">
            <h2>Recente Vondsten</h2>
            {% if properties %}
                {% for prop in properties %}
                <div class="property-card">
                    <div style="display: flex; justify-content: space-between; align-items: start; flex-wrap: wrap;">
                        <h3>{{ prop.title }}</h3>
                        {% if not prop.notified %}
                        <span class="badge badge-new">NIEUW</span>
                        {% else %}
                        <span class="badge badge-notified">Genotificeerd</span>
                        {% endif %}
                    </div>
                    <div class="property-meta">
                        <span>💰 {{ prop.price }}</span>
                        <span>📍 {{ prop.location }}</span>
                        <span>👤 {{ prop.seller_type }}</span>
                        <span>🕐 {{ prop.first_seen }}</span>
                    </div>
                    <a href="{{ prop.url }}" target="_blank" class="property-link">Bekijk op Immoweb →</a>
                </div>
                {% endfor %}
            {% else %}
                <div class="empty-state">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path>
                    </svg>
                    <p>Nog geen panden gevonden. Configureer je zoekopdrachten en voer een check uit.</p>
                </div>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

SEARCHES_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Zoekopdrachten - Immoweb Prospectie</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; background: #f5f7fa; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .nav { display: flex; gap: 1rem; margin-bottom: 2rem; flex-wrap: wrap; }
        .nav a { padding: 0.75rem 1.5rem; background: white; color: #667eea; text-decoration: none; border-radius: 8px; font-weight: 600; transition: all 0.3s; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .nav a:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .card { background: white; border-radius: 12px; padding: 2rem; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 2rem; }
        .card h2 { margin-bottom: 1.5rem; color: #1e293b; }
        .form-group { margin-bottom: 1.5rem; }
        .form-group label { display: block; margin-bottom: 0.5rem; color: #475569; font-weight: 600; font-size: 0.875rem; }
        .form-group input, .form-group select { width: 100%; padding: 0.75rem; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 1rem; transition: all 0.3s; }
        .form-group input:focus, .form-group select:focus { outline: none; border-color: #667eea; }
        .btn { padding: 0.75rem 1.5rem; background: #667eea; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.3s; }
        .btn:hover { background: #5568d3; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(102,126,234,0.4); }
        .btn-delete { background: #ef4444; }
        .btn-delete:hover { background: #dc2626; }
        .search-list { display: grid; gap: 1rem; }
        .search-item { border: 2px solid #e2e8f0; border-radius: 8px; padding: 1.25rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; }
        .search-info h3 { color: #1e293b; margin-bottom: 0.5rem; }
        .search-meta { display: flex; gap: 0.75rem; flex-wrap: wrap; font-size: 0.875rem; color: #64748b; }
        .search-meta span { background: #f1f5f9; padding: 0.25rem 0.75rem; border-radius: 4px; }
        .search-actions { display: flex; gap: 0.5rem; }
        .badge { padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
        .badge-active { background: #dcfce7; color: #166534; }
        .badge-inactive { background: #fee2e2; color: #991b1b; }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>🔍 Zoekopdrachten Beheren</h1>
        </div>
    </div>
    
    <div class="container">
        <div class="nav">
            <a href="/">Dashboard</a>
            <a href="/searches">Zoekopdrachten</a>
            <a href="/settings">Instellingen</a>
        </div>
        
        <div class="card">
            <h2>Nieuwe Zoekopdracht</h2>
            <form method="POST" action="/add-search">
                <div class="form-group">
                    <label>Naam zoekopdracht</label>
                    <input type="text" name="name" required placeholder="Bijv. Appartementen Antwerpen">
                </div>
                <div class="form-group">
                    <label>Provincie</label>
                    <select name="province" required>
                        <option value="">Selecteer provincie</option>
                        <option value="antwerp">Antwerpen</option>
                        <option value="flemish-brabant">Vlaams-Brabant</option>
                        <option value="walloon-brabant">Waals-Brabant</option>
                        <option value="west-flanders">West-Vlaanderen</option>
                        <option value="east-flanders">Oost-Vlaanderen</option>
                        <option value="hainaut">Henegouwen</option>
                        <option value="liege">Luik</option>
                        <option value="limburg">Limburg</option>
                        <option value="luxembourg">Luxemburg</option>
                        <option value="namur">Namen</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Type pand</label>
                    <select name="property_type" required>
                        <option value="house">Huis</option>
                        <option value="apartment">Appartement</option>
                        <option value="land">Grond</option>
                        <option value="office">Kantoor</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Min. prijs (EUR)</label>
                    <input type="number" name="min_price" placeholder="0">
                </div>
                <div class="form-group">
                    <label>Max. prijs (EUR)</label>
                    <input type="number" name="max_price" placeholder="999999999">
                </div>
                <div class="form-group">
                    <label>Verkoper type</label>
                    <select name="seller_type" required>
                        <option value="private">Alleen particulieren</option>
                        <option value="all">Allemaal</option>
                    </select>
                </div>
                <button type="submit" class="btn">Zoekopdracht Toevoegen</button>
            </form>
        </div>
        
        <div class="card">
            <h2>Actieve Zoekopdrachten</h2>
            <div class="search-list">
                {% if searches %}
                    {% for search in searches %}
                    <div class="search-item">
                        <div class="search-info">
                            <h3>{{ search.name }}</h3>
                            <div class="search-meta">
                                <span>📍 {{ search.province }}</span>
                                <span>🏠 {{ search.property_type }}</span>
                                <span>💰 €{{ search.min_price }} - €{{ search.max_price }}</span>
                                <span>👤 {{ search.seller_type }}</span>
                            </div>
                        </div>
                        <div class="search-actions">
                            {% if search.active %}
                            <span class="badge badge-active">Actief</span>
                            {% else %}
                            <span class="badge badge-inactive">Inactief</span>
                            {% endif %}
                            <form method="POST" action="/delete-search/{{ search.id }}" style="display: inline;">
                                <button type="submit" class="btn btn-delete" onclick="return confirm('Weet je zeker dat je deze zoekopdracht wilt verwijderen?')">Verwijderen</button>
                            </form>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                    <p style="color: #94a3b8; text-align: center; padding: 2rem;">Nog geen zoekopdrachten geconfigureerd.</p>
                {% endif %}
            </div>
        </div>
    </div>
</body>
</html>
'''

SETTINGS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Instellingen - Immoweb Prospectie</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; background: #f5f7fa; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .nav { display: flex; gap: 1rem; margin-bottom: 2rem; flex-wrap: wrap; }
        .nav a { padding: 0.75rem 1.5rem; background: white; color: #667eea; text-decoration: none; border-radius: 8px; font-weight: 600; transition: all 0.3s; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .card { background: white; border-radius: 12px; padding: 2rem; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 2rem; }
        .card h2 { margin-bottom: 1.5rem; color: #1e293b; }
        .form-group { margin-bottom: 1.5rem; }
        .form-group label { display: block; margin-bottom: 0.5rem; color: #475569; font-weight: 600; font-size: 0.875rem; }
        .form-group input, .form-group select { width: 100%; padding: 0.75rem; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 1rem; }
        .form-group input:focus { outline: none; border-color: #667eea; }
        .form-group small { color: #64748b; font-size: 0.875rem; }
        .btn { padding: 0.75rem 1.5rem; background: #667eea; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.3s; }
        .btn:hover { background: #5568d3; transform: translateY(-2px); }
        .alert { padding: 1rem; border-radius: 8px; margin-bottom: 1rem; }
        .alert-info { background: #dbeafe; color: #1e40af; border-left: 4px solid #3b82f6; }
        .alert-warning { background: #fef3c7; color: #92400e; border-left: 4px solid #f59e0b; }
        .checkbox-group { display: flex; align-items: center; gap: 0.5rem; }
        .checkbox-group input[type="checkbox"] { width: auto; }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>⚙️ Instellingen</h1>
        </div>
    </div>
    
    <div class="container">
        <div class="nav">
            <a href="/">Dashboard</a>
            <a href="/searches">Zoekopdrachten</a>
            <a href="/settings">Instellingen</a>
        </div>
        
        {% if message %}
        <div class="alert alert-info">{{ message }}</div>
        {% endif %}
        
        <div class="card">
            <h2>Email Notificaties</h2>
            <div class="alert alert-warning">
                <strong>Gmail Setup:</strong> Voor Gmail moet je een "App Password" aanmaken in je Google Account settings (2FA vereist). Gebruik dit app password in plaats van je normale wachtwoord.
            </div>
            <form method="POST" action="/save-settings">
                <div class="form-group checkbox-group">
                    <input type="checkbox" name="email_enabled" id="email_enabled" {% if settings.email_enabled == '1' %}checked{% endif %}>
                    <label for="email_enabled">Email notificaties inschakelen</label>
                </div>
                <div class="form-group">
                    <label>Van email (Gmail)</label>
                    <input type="email" name="email_from" value="{{ settings.email_from }}" placeholder="jouw@gmail.com">
                    <small>Je Gmail adres waarmee emails verstuurd worden</small>
                </div>
                <div class="form-group">
                    <label>Gmail App Password</label>
                    <input type="password" name="email_password" value="{{ settings.email_password }}" placeholder="••••••••••••••••">
                    <small>Niet je normale wachtwoord! Maak een App Password aan in Google Account settings</small>
                </div>
                <div class="form-group">
                    <label>Naar email</label>
                    <input type="email" name="email_to" value="{{ settings.email_to }}" placeholder="ontvanger@email.com">
                    <small>Email adres waar notificaties naartoe gestuurd worden</small>
                </div>
                <div class="form-group">
                    <label>Check interval (minuten)</label>
                    <input type="number" name="check_interval" value="{{ settings.check_interval }}" min="5" max="1440">
                    <small>Hoe vaak er gecontroleerd wordt op nieuwe panden (minimum 5 minuten)</small>
                </div>
                <button type="submit" class="btn">Instellingen Opslaan</button>
            </form>
        </div>
        
        <div class="card">
            <h2>Systeem Info</h2>
            <div class="alert alert-info">
                <p><strong>Replit Deployment:</strong></p>
                <ul style="margin-left: 1.5rem; margin-top: 0.5rem;">
                    <li>Schakel "Always On" in voor 24/7 monitoring</li>
                    <li>Of gebruik Replit Deployments voor productie</li>
                    <li>Check interval werkt automatisch op de achtergrond</li>
                </ul>
            </div>
        </div>
    </div>
</body>
</html>
'''

# Helper functions
def get_setting(key):
    conn = sqlite3.connect(app.config['DATABASE_NAME'])
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def set_setting(key, value):
    conn = sqlite3.connect(app.config['DATABASE_NAME'])
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def send_email_notification(properties):
    if get_setting('email_enabled') != '1':
        return
    
    email_from = get_setting('email_from')
    email_password = get_setting('email_password')
    email_to = get_setting('email_to')
    
    if not all([email_from, email_password, email_to]):
        print("Email settings incomplete")
        return
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'🏠 {len(properties)} nieuwe panden gevonden op Immoweb'
        msg['From'] = email_from
        msg['To'] = email_to
        
        html = '<html><body style="font-family: Arial, sans-serif;">'
        html += f'<h2>Er zijn {len(properties)} nieuwe panden gevonden!</h2>'
        
        for prop in properties:
            html += f'''
            <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 8px;">
                <h3>{prop['title']}</h3>
                <p><strong>Prijs:</strong> {prop['price']}</p>
                <p><strong>Locatie:</strong> {prop['location']}</p>
                <p><strong>Type verkoper:</strong> {prop['seller_type']}</p>
                <a href="{prop['url']}" style="display: inline-block; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px;">Bekijk pand</a>
            </div>
            '''
        
        html += '</body></html>'
        
        msg.attach(MIMEText(html, 'html'))
        
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(email_from, email_password)
        server.sendmail(email_from, email_to, msg.as_string())
        server.quit()
        
        print(f"Email sent successfully for {len(properties)} properties")
    except Exception as e:
        print(f"Error sending email: {e}")

def scrape_immoweb(search_config):
    """
    Scrapes Immoweb based on search configuration
    Returns list of new properties
    """
    new_properties = []
    
    try:
        # Build Immoweb search URL
        base_url = "https://www.immoweb.be/en/search"
        params = {
            'countries': 'BE',
            'propertyTypes': search_config['property_type'].upper(),
            'provinces': search_config['province'].upper().replace('-', '_'),
            'minPrice': search_config['min_price'],
            'maxPrice': search_config['max_price']
        }
        
        # Note: This is a simplified scraper. Immoweb may require more sophisticated handling
        # Including headers, session management, and potentially dealing with JavaScript rendering
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Construct URL (simplified - actual Immoweb URL structure may vary)
        search_url = f"{base_url}/{search_config['property_type']}/for-sale/{search_config['province']}/?minPrice={search_config['min_price']}&maxPrice={search_config['max_price']}"
        
        print(f"Searching: {search_url}")
        
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Failed to fetch: {response.status_code}")
            return new_properties
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find property listings - this selector may need adjustment based on actual Immoweb structure
        # This is a generic approach that should work for most real estate sites
        listings = soup.find_all('article') or soup.find_all('div', class_=lambda x: x and 'card' in x.lower())
        
        for listing in listings[:20]:  # Limit to first 20 results
            try:
                # Extract property info - selectors may need adjustment
                title_elem = listing.find('h2') or listing.find('h3') or listing.find('a')
                price_elem = listing.find(text=lambda t: t and '€' in str(t))
                link_elem = listing.find('a', href=True)
                
                if not link_elem:
                    continue
                
                url
              url = link_elem['href']
                if not url.startswith('http'):
                    url = 'https://www.immoweb.be' + url
                
                title = title_elem.get_text(strip=True) if title_elem else 'Geen titel'
                price = price_elem if price_elem else 'Prijs op aanvraag'
                
                # Create unique ID for this property
                property_id = hashlib.md5(url.encode()).hexdigest()
                
                # Check if we already have this property
                conn = sqlite3.connect(app.config['DATABASE_NAME'])
                c = conn.cursor()
                c.execute("SELECT id FROM properties WHERE id = ?", (property_id,))
                exists = c.fetchone()
                
                if not exists:
                    # Check seller type if filtering for private sellers
                    seller_type = 'Particulier' if 'particulier' in listing.get_text().lower() else 'Makelaar'
                    
                    if search_config['seller_type'] == 'private' and seller_type != 'Particulier':
                        conn.close()
                        continue
                    
                    # New property found!
                    location = search_config['province']
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    c.execute("""INSERT INTO properties 
                                 (id, url, title, price, location, seller_type, first_seen, notified)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
                              (property_id, url, title, price, location, seller_type, timestamp))
                    conn.commit()
                    
                    new_properties.append({
                        'id': property_id,
                        'url': url,
                        'title': title,
                        'price': price,
                        'location': location,
                        'seller_type': seller_type
                    })
                    
                    print(f"New property found: {title}")
                
                conn.close()
                
            except Exception as e:
                print(f"Error parsing listing: {e}")
                continue
        
        # Small delay to be respectful
        time.sleep(2)
        
    except Exception as e:
        print(f"Error scraping Immoweb: {e}")
    
    return new_properties

def check_for_new_properties():
    """Main function to check all active searches for new properties"""
    print(f"Starting property check at {datetime.now()}")
    
    conn = sqlite3.connect(app.config['DATABASE_NAME'])
    c = conn.cursor()
    c.execute("SELECT * FROM search_configs WHERE active = 1")
    searches = c.fetchall()
    conn.close()
    
    all_new_properties = []
    
    for search in searches:
        search_config = {
            'id': search[0],
            'name': search[1],
            'province': search[2],
            'property_type': search[3],
            'min_price': search[4],
            'max_price': search[5],
            'seller_type': search[6]
        }
        
        print(f"Checking search: {search_config['name']}")
        new_props = scrape_immoweb(search_config)
        all_new_properties.extend(new_props)
    
    # Send notification if new properties found
    if all_new_properties:
        print(f"Found {len(all_new_properties)} new properties total")
        send_email_notification(all_new_properties)
        
        # Mark as notified
        conn = sqlite3.connect(app.config['DATABASE_NAME'])
        c = conn.cursor()
        for prop in all_new_properties:
            c.execute("UPDATE properties SET notified = 1 WHERE id = ?", (prop['id'],))
        conn.commit()
        conn.close()
    else:
        print("No new properties found")
    
    # Update last check time
    set_setting('last_check', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    return len(all_new_properties)

# Routes
@app.route('/')
def dashboard():
    conn = sqlite3.connect(app.config['DATABASE_NAME'])
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM properties")
    total_properties = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM properties WHERE notified = 0")
    new_properties = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM search_configs WHERE active = 1")
    active_searches = c.fetchone()[0]
    
    c.execute("SELECT * FROM properties ORDER BY first_seen DESC LIMIT 20")
    properties = []
    for row in c.fetchall():
        properties.append({
            'id': row[0],
            'url': row[1],
            'title': row[2],
            'price': row[3],
            'location': row[4],
            'seller_type': row[5],
            'first_seen': row[6],
            'notified': row[7]
        })
    
    conn.close()
    
    last_check = get_setting('last_check')
    
    return render_template_string(DASHBOARD_TEMPLATE,
                                 total_properties=total_properties,
                                 new_properties=new_properties,
                                 active_searches=active_searches,
                                 properties=properties,
                                 last_check=last_check)

@app.route('/searches')
def searches():
    conn = sqlite3.connect(app.config['DATABASE_NAME'])
    c = conn.cursor()
    c.execute("SELECT * FROM search_configs")
    searches = []
    for row in c.fetchall():
        searches.append({
            'id': row[0],
            'name': row[1],
            'province': row[2],
            'property_type': row[3],
            'min_price': row[4],
            'max_price': row[5],
            'seller_type': row[6],
            'active': row[7]
        })
    conn.close()
    
    return render_template_string(SEARCHES_TEMPLATE, searches=searches)

@app.route('/add-search', methods=['POST'])
def add_search():
    name = request.form.get('name')
    province = request.form.get('province')
    property_type = request.form.get('property_type')
    min_price = request.form.get('min_price', 0)
    max_price = request.form.get('max_price', 999999999)
    seller_type = request.form.get('seller_type')
    
    conn = sqlite3.connect(app.config['DATABASE_NAME'])
    c = conn.cursor()
    c.execute("""INSERT INTO search_configs 
                 (name, province, property_type, min_price, max_price, seller_type, active)
                 VALUES (?, ?, ?, ?, ?, ?, 1)""",
              (name, province, property_type, min_price, max_price, seller_type))
    conn.commit()
    conn.close()
    
    return redirect(url_for('searches'))

@app.route('/delete-search/<int:search_id>', methods=['POST'])
def delete_search(search_id):
    conn = sqlite3.connect(app.config['DATABASE_NAME'])
    c = conn.cursor()
    c.execute("DELETE FROM search_configs WHERE id = ?", (search_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('searches'))

@app.route('/settings')
def settings():
    settings_data = {
        'email_enabled': get_setting('email_enabled'),
        'email_from': get_setting('email_from') or '',
        'email_password': get_setting('email_password') or '',
        'email_to': get_setting('email_to') or '',
        'check_interval': get_setting('check_interval') or '60'
    }
    
    return render_template_string(SETTINGS_TEMPLATE, settings=settings_data, message=None)

@app.route('/save-settings', methods=['POST'])
def save_settings():
    set_setting('email_enabled', '1' if request.form.get('email_enabled') else '0')
    set_setting('email_from', request.form.get('email_from', ''))
    set_setting('email_password', request.form.get('email_password', ''))
    set_setting('email_to', request.form.get('email_to', ''))
    set_setting('check_interval', request.form.get('check_interval', '60'))
    
    # Restart scheduler with new interval
    interval = int(get_setting('check_interval'))
    scheduler.remove_all_jobs()
    scheduler.add_job(check_for_new_properties, 'interval', minutes=interval, id='property_check')
    
    settings_data = {
        'email_enabled': get_setting('email_enabled'),
        'email_from': get_setting('email_from'),
        'email_password': get_setting('email_password'),
        'email_to': get_setting('email_to'),
        'check_interval': get_setting('check_interval')
    }
    
    return render_template_string(SETTINGS_TEMPLATE, settings=settings_data, 
                                 message='Instellingen succesvol opgeslagen!')

@app.route('/run-check')
def run_check():
    count = check_for_new_properties()
    return redirect(url_for('dashboard'))

# Initialize scheduler
scheduler = BackgroundScheduler()
interval = int(get_setting('check_interval') or 60)
scheduler.add_job(check_for_new_properties, 'interval', minutes=interval, id='property_check')
scheduler.start()

if __name__ == '__main__':
    print("🏠 Immoweb Prospectie Tool gestart!")
    print(f"Check interval: {interval} minuten")
    app.run(host='0.0.0.0', port=5000, debug=False)
              

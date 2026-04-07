from flask import Flask, render_template_string, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "kisaan_secret_key_2025" 

DB_PATH = "kisaan_app.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # users table (plain-text password per user's choice)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    # labors table: each labor belongs to a username
    c.execute("""
        CREATE TABLE IF NOT EXISTS labors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT,
            wage REAL DEFAULT 0,   -- wage per day
            days REAL DEFAULT 0    -- number of days worked
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -------------------------
# DB helpers
# -------------------------
def register_user_db(username, password):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def validate_user_db(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
    row = c.fetchone()
    conn.close()
    return row is not None

def add_labor_db(username, name, role, wage, days):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO labors (username, name, role, wage, days) VALUES (?, ?, ?, ?, ?)",
              (username, name, role, wage, days))
    conn.commit()
    conn.close()

def update_labor_db(labor_id, username, name, role, wage, days):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE labors SET name=?, role=?, wage=?, days=? WHERE id=? AND username=?",
              (name, role, wage, days, labor_id, username))
    conn.commit()
    conn.close()

def delete_labor_db(labor_id, username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM labors WHERE id=? AND username=?", (labor_id, username))
    conn.commit()
    conn.close()

def get_labors_db(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, role, wage, days FROM labors WHERE username=? ORDER BY id ASC", (username,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "role": r[2], "wage": float(r[3]), "days": float(r[4])} for r in rows]

# -------------------------
# Base template (single)
# -------------------------
base_template = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>KISAAN — {{ title }}</title>
  <style>
    :root{
      --green-1:#004d00;
      --green-2:#1b5e20;
      --accent:#ffd54f;
      --card: rgba(0,0,0,0.45);
    }
    html,body{height:100%; margin:0; font-family: 'Poppins', 'Segoe UI', sans-serif; color:#fff;}
    body{
      {% if use_gradient %}
      background: linear-gradient(135deg, var(--green-1), var(--green-2));
      {% else %}
      background: url('{{ bg_image }}') no-repeat center/cover fixed;
      {% endif %}
      -webkit-font-smoothing:antialiased;
    }
    .overlay { position: fixed; inset:0; background: rgba(0,0,0,0.34); backdrop-filter: blur(6px); z-index:0; }

    header{ position:relative; z-index:2; background: rgba(0,80,0,0.9); padding:12px 0; text-align:center; }
    header h1{ margin:0; font-size:18px; letter-spacing:1.5px; }
    nav{ position:relative; z-index:2; background: rgba(0,100,0,0.95); display:flex; justify-content:center; gap:18px; padding:10px 8px; flex-wrap:wrap;}
    nav a{ color:#fff; text-decoration:none; font-weight:600; }
    nav a:hover{ color: var(--accent); }

    main.container{ position:relative; z-index:2; max-width:1100px; margin:50px auto; background:var(--card); padding:30px; border-radius:12px; box-shadow:0 12px 30px rgba(0,0,0,0.5); }

    h2{ color:#d4ffcc; margin-top:0; }
    p, li { color:#eaf6ea; line-height:1.7; }
    a.link{ color: var(--accent); text-decoration:none; }
    a.link:hover{ text-decoration:underline; }

    .form-row{ margin:10px 0; }
    input[type="text"], input[type="password"], input[type="number"]{
      padding:10px; border-radius:6px; border:none; width:260px;
    }
    select{ padding:10px; border-radius:6px; border:none; }

    button{ padding:10px 14px; border-radius:6px; border:none; background:var(--green-2); color:#fff; font-weight:700; cursor:pointer; }
    button:hover{ background:#0f4a11; }

    table{ width:100%; border-collapse:collapse; margin-top:12px; color:#fff;}
    th,td{ padding:10px; border:1px solid rgba(255,255,255,0.08); text-align:center; }
    th{ background: rgba(255,255,255,0.03); color:#f0f9f0; }

    .muted{ color:#dfeede; font-size:0.95rem; }
    .msg{ color:var(--accent); font-weight:700; margin-top:12px; }

    footer{ margin-top:18px; text-align:center; color:#dbeedd; font-size:14px; }

    /* small screens */
    @media (max-width:900px){
      main.container{ margin:20px; padding:18px; }
      input[type="text"], input[type="password"], input[type="number"]{ width:100%; }
    }
  </style>
</head>
<body>
  <div class="overlay"></div>
  <header><h1>🌾 KISAAN PORTAL</h1></header>

  <nav>
    <a href="{{ url_for('home') }}">Home</a>
    <a href="{{ url_for('agriculture') }}">Agricultural Info</a>
    <a href="{{ url_for('schemes') }}">Government Schemes</a>
    <a href="{{ url_for('market') }}">Market</a>
    <a href="{{ url_for('news') }}">News</a>
    <a href="{{ url_for('contact') }}">Contact</a>
    {% if 'username' in session %}
      <a href="{{ url_for('logout') }}" style="margin-left:12px;">Logout ({{ session['username'] }})</a>
    {% else %}
      <a href="{{ url_for('login') }}" style="margin-left:12px;">Login</a>
      <a href="{{ url_for('register') }}">Register</a>
    {% endif %}
  </nav>

  <main class="container" role="main">
    {{ content|safe }}
  </main>

  <footer>© 2025 KISAAN — Empowering Farmers • Data & resources for cultivation and markets</footer>
</body>
</html>
"""

# -------------------------
# Helper to render page with background or gradient
# -------------------------
def render_page(title, content_html, bg_image=None, use_gradient=False):
    return render_template_string(
        base_template,
        title=title,
        content=content_html,
        bg_image=bg_image or "",
        use_gradient=use_gradient
    )

# -------------------------
# Routes & Pages (detailed content)
# -------------------------

# HOME (public)
@app.route("/")
def home():
    content = """
    <h2>Welcome to KISAAN</h2>
    <p class="muted">Your digital companion for modern, sustainable and profitable farming. KISAAN brings curated information, official resources, market tools, and labour tracking to help Indian farmers make better decisions.</p>

    <h3>What you can do here</h3>
    <ul>
      <li>Explore in-depth agricultural information and seasonal advisories.</li>
      <li>Read summaries of key government schemes and official links.</li>
      <li>Manage labour records and automatically calculate total payments.</li>
      <li>Stay updated with curated agriculture news and best practices.</li>
    </ul>

    <h3>Quick Start</h3>
    <p>If you're a farmer or manager: <a class="link" href="/register">Register</a> and then <a class="link" href="/login">Login</a>. The Market page contains labour tools reserved for logged-in users.</p>
    """
    # use a pleasant farmland background for home
    return render_page("Home", content, bg_image="https://images.unsplash.com/photo-1501004318641-b39e6451bec6?auto=format&fit=crop&w=1600&q=80", use_gradient=False)

# AGRICULTURE (expanded)
@app.route("/agriculture")
def agriculture():
    content = """
    <h2>Agricultural Information — Practical Guide</h2>

    <h3>Soil & Nutrient Management</h3>
    <p>Healthy soil is the foundation of farming. Conduct soil testing at least once a year. Use the Soil Health Card recommendations to balance nitrogen (N), phosphorus (P), potassium (K) and required micronutrients (Zn, Fe, B) rather than overdosing chemical fertilizers. Combine organic matter (compost/farm-yard manure) and biofertilizers with chemical fertilizers for sustained yields.</p>

    <h3>Irrigation Best Practices</h3>
    <p>Switch to micro-irrigation (drip/sprinkler) for water efficiency. Mulching, contour bunding, and rainwater harvesting help reduce evaporation and increase ground water recharge.</p>

    <h3>Crop Choice & Crop Rotation</h3>
    <p>Choose crops based on climate, soil, and market demand. Rotate cereals with legumes to improve soil nitrogen naturally. Diversification (horticulture + cereals) improves income resilience.</p>

    <h3>Pest & Disease Management</h3>
    <p>Use Integrated Pest Management (IPM): start with cultural practices, biological controls (predatory insects), and use chemical pesticides only when thresholds are exceeded. Read pesticide labels carefully and follow safety guidelines.</p>

    <h3>Modern Technology</h3>
    <ul>
      <li><strong>Precision Farming:</strong> soil sensors, satellite imagery & GPS-guided machinery reduce input waste.</li>
      <li><strong>Protected cultivation:</strong> greenhouses/poly-tunnels to extend growing seasons.</li>
      <li><strong>Mobile Advisory:</strong> use government and private advisory apps for pest alerts and market rates.</li>
    </ul>

    <h3>Trusted Resources</h3>
    <ul>
      <li><a class="link" href="https://icar.org.in/" target="_blank">Indian Council of Agricultural Research (ICAR)</a></li>
      <li><a class="link" href="https://agricoop.gov.in/" target="_blank">Ministry of Agriculture & Farmers Welfare</a></li>
      <li><a class="link" href="https://soilhealth.dac.gov.in/" target="_blank">Soil Health Card Portal</a></li>
      <li><a class="link" href="https://vikaspedia.in/agriculture" target="_blank">Vikaspedia – Agriculture</a></li>
    </ul>
    """
    return render_page("Agriculture Info", content, bg_image="https://images.unsplash.com/photo-1568605114967-8130f3a36994?auto=format&fit=crop&w=1600&q=80", use_gradient=False)

# SCHEMES (expanded)
@app.route("/schemes")
def schemes():
    content = """
    <h2>Government Schemes — What Farmers Should Know</h2>

    <h3>PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)</h3>
    <p>Small & marginal farmers receive direct income support under PM-KISAN. Check eligibility & status at <a class="link" href="https://pmkisan.gov.in/" target="_blank">pmkisan.gov.in</a>.</p>

    <h3>PM Fasal Bima Yojana (Crop Insurance)</h3>
    <p>Insurance cover for crop losses due to natural calamities. Enrolment often occurs via local banks/insurance providers—visit <a class="link" href="https://pmfby.gov.in/" target="_blank">pmfby.gov.in</a>.</p>

    <h3>Kisan Credit Card (KCC)</h3>
    <p>Short-term credit for agricultural needs—working capital for crop production, inputs, and allied activities. Apply via banks; terms depend on the lending institution.</p>

    <h3>Soil Health Card & Extension Services</h3>
    <p>Free soil testing and advisory services help optimize fertilizer use. The Soil Health Card portal: <a class="link" href="https://soilhealth.dac.gov.in/" target="_blank">soilhealth.dac.gov.in</a>.</p>

    <h3>Other Important Supports</h3>
    <ul>
      <li><a class="link" href="https://enam.gov.in/" target="_blank">eNAM</a> — National Agriculture Market for online trading of produce.</li>
      <li><a class="link" href="https://www.nabard.org/" target="_blank">NABARD</a> — credit & infrastructure schemes for rural development.</li>
    </ul>

    <p>For implementation details and state-level schemes, always check the state agriculture department websites or the local agriculture office.</p>
    """
    return render_page("Government Schemes", content, bg_image="https://images.unsplash.com/photo-1503220317375-aaad61436b1b?auto=format&fit=crop&w=1600&q=80", use_gradient=False)

# NEWS (expanded)
@app.route("/news")
def news():
    content = """
    <h2>Agriculture News & Advisory</h2>

    <article>
      <h3>1. New Irrigation Subsidies Announced</h3>
      <p>The central and several state governments announced additional subsidies to accelerate micro-irrigation adoption, focusing on drip systems for horticulture and high-value crops.</p>
    </article>

    <article>
      <h3>2. Technology for Small Farms</h3>
      <p>Affordable sensor kits and mobile advisory platforms are now available to smallholder farmers to help monitor soil moisture, pest outbreaks and optimize input timings.</p>
    </article>

    <article>
      <h3>3. Market Prices & MSP Alerts</h3>
      <p>Stay updated with MSP notifications and local mandi rates. For official commodity price data, visit <a class="link" href="https://agmarknet.gov.in/" target="_blank">Agmarknet</a>.</p>
    </article>

    <p>For authoritative government releases, check the Press Information Bureau: <a class="link" href="https://pib.gov.in/" target="_blank">pib.gov.in</a>.</p>
    """
    return render_page("News", content, bg_image="https://images.unsplash.com/photo-1609793713619-fb0e28a4d8f5?auto=format&fit=crop&w=1600&q=80", use_gradient=False)

# CONTACT (expanded)
@app.route("/contact")
def contact():
    content = """
    <h2>Contact & Help</h2>
    <p><strong>Kisan Call Centre:</strong> 1800-180-1551</p>
    <p><strong>Email:</strong> support@kisaan.gov.in (demo)</p>
    <p><strong>Address:</strong> Krishi Bhavan, New Delhi, India</p>

    <h3>Useful Links</h3>
    <ul>
      <li><a class="link" href="https://farmer.gov.in/" target="_blank">National Farmer Portal</a></li>
      <li><a class="link" href="https://agricoop.gov.in/" target="_blank">Ministry of Agriculture</a></li>
      <li><a class="link" href="https://icar.org.in/" target="_blank">ICAR</a></li>
    </ul>

    <h3>Feedback</h3>
    <p>If you'd like to suggest improvements for this portal, email <em>support@kisaan.gov.in</em>.</p>
    """
    return render_page("Contact", content, bg_image="https://images.unsplash.com/photo-1494949649100-ecbb6f0b3be6?auto=format&fit=crop&w=1600&q=80", use_gradient=False)

# -------------------------
# Market / Labour (logged in)
# - add / edit / delete labour
# - calculates Amount(₹) = wage * days
# - shows total amount per user 
# -------------------------
@app.route("/market", methods=["GET", "POST"])
def market():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    message = ""

    # Handle form actions
    if request.method == "POST":
        action = request.form.get("action")

        # Add new labour
        if action == "add":
            name = request.form.get("name", "").strip()
            role = request.form.get("role", "").strip()
            wage_raw = request.form.get("wage", "0").strip()
            days_raw = request.form.get("days", "0").strip()

            try:
                wage = float(wage_raw) if wage_raw else 0.0
                days = float(days_raw) if days_raw else 0.0
                if name:
                    add_labor_db(username, name, role, wage, days)
                    message = f"✅ Added labour: {name}."
                else:
                    message = "Please specify a labour name."
            except ValueError:
                message = "Enter valid numbers for wage and days."

        # Update labour record
        elif action == "update":
            lab_id = request.form.get("labor_id")
            name = request.form.get("name", "").strip()
            role = request.form.get("role", "").strip()
            wage_raw = request.form.get("wage", "0").strip()
            days_raw = request.form.get("days", "0").strip()

            try:
                wage = float(wage_raw) if wage_raw else 0.0
                days = float(days_raw) if days_raw else 0.0
                if lab_id and name:
                    updated = update_labor_db(int(lab_id), username, name, role, wage, days)
                    message = "✅ Record updated successfully." if updated else "❌ No record found for that ID."
                else:
                    message = "Please provide valid data to update."
            except ValueError:
                message = "Enter valid numbers for wage and days."

        # Delete labour record
        elif action == "delete":
            lab_id = request.form.get("labor_id")
            if lab_id:
                delete_labor_db(int(lab_id), username)
                message = "🗑️ Labour record deleted."
            else:
                message = "Provide valid ID to delete."

    # Fetch all labours for this user
    labors = get_labors_db(username)
    total = 0.0
    rows = ""

    for l in labors:
        amount = l["wage"] * l["days"]
        total += amount
        rows += f"""
        <tr>
            <form method="POST">
                <td>{l['id']}<input type="hidden" name="labor_id" value="{l['id']}"></td>
                <td><input type="text" name="name" value="{l['name']}" style="width:120px;"></td>
                <td><input type="text" name="role" value="{l['role'] or ''}" style="width:120px;"></td>
                <td><input type="number" step="0.01" name="wage" value="{l['wage']}" style="width:100px;"></td>
                <td><input type="number" step="0.01" name="days" value="{l['days']}" style="width:80px;"></td>
                <td>₹ {amount:.2f}</td>
                <td>
                    <button type="submit" name="action" value="update">Update</button>
                    <button type="submit" name="action" value="delete" style="background:#b71c1c;">Delete</button>
                </td>
            </form>
        </tr>
        """

    content = f"""
      <h2>Market & Labour Management</h2>
      <p class="muted">Manage labour records for <strong>{username}</strong>. Add or update wage and days worked — the portal calculates the total payment automatically.</p>

      <h3>Add Labour</h3>
      <form method="POST">
        <div class="form-row">
          <input type="text" name="name" placeholder="Labour Name" required>
          <input type="text" name="role" placeholder="Work Type (e.g., Harvester)">
          <input type="number" step="0.01" name="wage" placeholder="Wage per day (₹)" required>
          <input type="number" step="0.01" name="days" placeholder="Days worked" required>
          <button type="submit" name="action" value="add">Add Labour</button>
        </div>
      </form>

      <p class="msg">{message}</p>

      <h3 style="margin-top:18px;">Current Labour Records</h3>
      <table>
        <tr><th>ID</th><th>Name</th><th>Role</th><th>Wage (₹/day)</th><th>Days</th><th>Amount (₹)</th><th>Actions</th></tr>
        {rows if rows else '<tr><td colspan="7">No records yet.</td></tr>'}
      </table>

      <h3 style="margin-top:20px;">💵 Total Paid: ₹ {total:.2f}</h3>
    """
    return render_page("Market", content, bg_image="https://images.unsplash.com/photo-1602526216435-5e99e94bcf68?auto=format&fit=crop&w=1600&q=80", use_gradient=False)

# -------------------------
# Authentication (Login/Register)
# - Login/Register pages use gradient background for clarity
# -------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    msg = ""
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","").strip()
        if not username or not password:
            msg = "Username and password required."
        else:
            ok = register_user_db(username, password)
            if ok:
                return redirect(url_for('login'))
            else:
                msg = "Username already exists."
    content = f"""
      <h2>Register</h2>
      <form method="POST">
        <div class="form-row"><input type="text" name="username" placeholder="Enter username" required></div>
        <div class="form-row"><input type="password" name="password" placeholder="Enter password" required></div>
        <div class="form-row"><button type="submit">Register</button></div>
      </form>
      <p class="msg">{msg}</p>
      <p class="muted">Passwords stored as plain-text in this demo (for easy testing).</p>
    """
    return render_page("Register", content, use_gradient=True)

@app.route("/login", methods=["GET", "POST"])
def login():
    msg = ""
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","").strip()
        if validate_user_db(username, password):
            session['username'] = username
            return redirect(url_for('home'))
        else:
            msg = "Invalid username or password."
    content = f"""
      <h2>Login</h2>
      <form method="POST">
        <div class="form-row"><input type="text" name="username" placeholder="Username" required></div>
        <div class="form-row"><input type="password" name="password" placeholder="Password" required></div>
        <div class="form-row"><button type="submit">Login</button></div>
      </form>
      <p class="msg">{msg}</p>
      <p class="muted">Don't have an account? <a class="link" href="/register">Register here</a>.</p>
    """
    return render_page("Login", content, use_gradient=True)

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    # ensure DB exists
    if not os.path.exists(DB_PATH):
        init_db()
    app.run(debug=True)

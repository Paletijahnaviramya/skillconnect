from flask import Flask, render_template, request, jsonify, session
import sqlite3, os, hashlib
from functools import wraps
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "skillconnect-local-demo-key-change-before-production")
app.config["MAX_CONTENT_LENGTH"] = 21 * 1024 * 1024
DB = os.path.join(os.path.dirname(__file__), "skillconnect.db")

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT UNIQUE,
      password TEXT, role TEXT, area TEXT, skills TEXT DEFAULT '',
      availability TEXT DEFAULT 'Flexible', bio TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS opportunities(
      id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, category TEXT, description TEXT,
      area TEXT, pay REAL, work_type TEXT, posted_by INTEGER, status TEXT DEFAULT 'Open'
    );
    CREATE TABLE IF NOT EXISTS applications(
      id INTEGER PRIMARY KEY AUTOINCREMENT, opportunity_id INTEGER, user_id INTEGER,
      status TEXT DEFAULT 'Applied', UNIQUE(opportunity_id,user_id)
    );
    CREATE TABLE IF NOT EXISTS reviews(
      id INTEGER PRIMARY KEY AUTOINCREMENT, provider_id INTEGER, customer_name TEXT,
      rating INTEGER, comment TEXT
    );
    CREATE TABLE IF NOT EXISTS favorites(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,opportunity_id INTEGER,UNIQUE(user_id,opportunity_id));
    CREATE TABLE IF NOT EXISTS circles(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,category TEXT,description TEXT,members INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS circle_members(id INTEGER PRIMARY KEY AUTOINCREMENT,circle_id INTEGER,user_id INTEGER,UNIQUE(circle_id,user_id));
    CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,message TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,seen INTEGER DEFAULT 0);
    """)
    columns=[r["name"] for r in con.execute("PRAGMA table_info(users)").fetchall()]
    if "portfolio" not in columns:
        con.execute("ALTER TABLE users ADD COLUMN portfolio TEXT DEFAULT ''")
    if con.execute("SELECT COUNT(*) FROM circles").fetchone()[0] == 0:
        con.executemany("INSERT INTO circles(name,category,description) VALUES(?,?,?)",[
          ("Stitch & Share","Tailoring","Exchange patterns, pricing tips and customer-ready stitching ideas."),
          ("Creative Hands","Handicrafts","Share handmade products, craft ideas and feedback."),
          ("Digital Starters","Digital Services","Learn digital payments, online catalogues and basic design."),
          ("Home Chefs Network","Cooking","Share recipes, hygiene tips and local food orders.")
        ])
    if con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        users = [
          ("Anitha","9000000001","demo","woman","Miyapur","Tailoring,Embroidery","Morning","Experienced tailor"),
          ("Sravani","9000000002","demo","woman","Kukatpally","Cooking,Snacks","Flexible","Homemade food specialist"),
          ("Meena","9000000003","demo","woman","Ameerpet","Beauty Services,Mehendi","Evening","Beauty and mehendi services"),
          ("Customer Demo","9000000005","demo","customer","Miyapur","","Flexible",""),
          ("Admin","9000000004","admin","admin","Hyderabad","","Flexible","")
        ]
        for u in users:
            con.execute("INSERT INTO users(name,phone,password,role,area,skills,availability,bio) VALUES(?,?,?,?,?,?,?,?)",u)
        admin = con.execute("SELECT id FROM users WHERE role='admin'").fetchone()["id"]
        seeds = [
          ("Blouse stitching orders","Tailoring","Stitch 5 blouses for a local boutique. Materials will be provided.","Miyapur",450,"Home-based"),
          ("Homemade snack preparation","Cooking","Prepare evening snack boxes for 20 customers.","Kukatpally",600,"Flexible"),
          ("Mehendi artist for event","Beauty Services","Provide simple mehendi designs for a family function.","Ameerpet",800,"Part-time"),
          ("Embroidery work","Embroidery","Complete hand embroidery on 3 dress pieces.","Miyapur",700,"Home-based"),
          ("Weekend cooking assistant","Cooking","Prepare traditional meals on Saturday and Sunday.","Kukatpally",500,"Part-time")
        ]
        for x in seeds:
            con.execute("INSERT INTO opportunities(title,category,description,area,pay,work_type,posted_by) VALUES(?,?,?,?,?,?,?)",(*x,admin))
        con.execute("INSERT INTO reviews(provider_id,customer_name,rating,comment) VALUES(1,'Local Boutique',5,'Excellent stitching and timely delivery')")
        con.execute("INSERT INTO reviews(provider_id,customer_name,rating,comment) VALUES(2,'Happy Customer',4,'Tasty homemade snacks')")
    con.commit()
    con.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error":"Please login first"}), 401
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/stats")
def stats():
    con=db()
    data={
      "women":con.execute("SELECT COUNT(*) FROM users WHERE role='woman'").fetchone()[0],
      "opportunities":con.execute("SELECT COUNT(*) FROM opportunities WHERE status='Open'").fetchone()[0],
      "applications":con.execute("SELECT COUNT(*) FROM applications").fetchone()[0],
      "matches":con.execute("SELECT COUNT(*) FROM applications WHERE status='Selected'").fetchone()[0],
      "skills":[dict(r) for r in con.execute("SELECT category,COUNT(*) count FROM opportunities GROUP BY category ORDER BY count DESC")]
    }
    con.close()
    return jsonify(data)

@app.route("/api/login", methods=["POST"])
def login():
    d=request.json or {}
    con=db()
    u=con.execute("SELECT * FROM users WHERE phone=? AND password=?",(d.get("phone",""),d.get("password",""))).fetchone()
    con.close()
    if not u: return jsonify({"error":"Invalid phone number or password"}),401
    session["user_id"]=u["id"]; session["name"]=u["name"]; session["role"]=u["role"]
    return jsonify({"id":u["id"],"name":u["name"],"role":u["role"],"area":u["area"],"skills":u["skills"]})

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok":True})

@app.route("/api/me")
def me():
    if not session.get("user_id"): return jsonify({"user":None})
    con=db(); u=con.execute("SELECT id,name,phone,role,area,skills,availability,bio,portfolio FROM users WHERE id=?",(session["user_id"],)).fetchone(); con.close()
    return jsonify({"user":dict(u) if u else None})

@app.route("/api/register", methods=["POST"])
def register():
    d=request.json or {}
    required=["name","phone","password","role","area"]
    if any(not d.get(k) for k in required): return jsonify({"error":"Please fill all required fields"}),400
    if d["role"] not in ("woman","customer"): return jsonify({"error":"Invalid account type"}),400
    con=db()
    try:
        cur=con.execute("INSERT INTO users(name,phone,password,role,area,skills,availability,bio) VALUES(?,?,?,?,?,?,?,?)",
          (d["name"],d["phone"],d["password"],d["role"],d["area"],d.get("skills",""),d.get("availability","Flexible"),d.get("bio","")))
        con.commit()
        session["user_id"]=cur.lastrowid; session["name"]=d["name"]; session["role"]=d["role"]
        return jsonify({"ok":True})
    except sqlite3.IntegrityError:
        return jsonify({"error":"Phone number already registered"}),409
    finally: con.close()

@app.route("/api/opportunities")
def opportunities():
    con=db()
    rows=con.execute("""SELECT o.*,u.name poster FROM opportunities o LEFT JOIN users u ON o.posted_by=u.id
      WHERE o.status='Open' ORDER BY o.id DESC""").fetchall()
    con.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/recommendations")
@login_required
def recommendations():
    con=db()
    u=con.execute("SELECT * FROM users WHERE id=?",(session["user_id"],)).fetchone()
    rows=con.execute("SELECT * FROM opportunities WHERE status='Open'").fetchall()
    user_skills=[s.strip().lower() for s in (u["skills"] or "").split(",") if s.strip()]
    scored=[]
    for o in rows:
        skill=o["category"].lower()
        skill_score=1 if any(s in skill or skill in s for s in user_skills) else 0
        area_score=1 if u["area"].lower()==o["area"].lower() else 0
        # Transparent weighted ranking: skill 60%, locality 30%, flexibility 10%.
        score=skill_score*60+area_score*30+(10 if o["work_type"] in ("Flexible","Home-based") else 0)
        scored.append({**dict(o),"score":score,"reason":"Skill match" if skill_score else "Explore a new skill","locality_match":bool(area_score)})
    con.close()
    return jsonify(sorted(scored,key=lambda x:x["score"],reverse=True))

@app.route("/api/apply",methods=["POST"])
@login_required
def apply():
    if session.get("role")!="woman": return jsonify({"error":"Only women service-provider accounts can apply"}),403
    oid=(request.json or {}).get("opportunity_id")
    con=db()
    try:
        con.execute("INSERT INTO applications(opportunity_id,user_id) VALUES(?,?)",(oid,session["user_id"]))
        con.commit(); return jsonify({"ok":True,"message":"Application submitted"})
    except sqlite3.IntegrityError:
        return jsonify({"error":"You have already applied"}),409
    finally: con.close()

@app.route("/api/post",methods=["POST"])
@login_required
def post():
    if session.get("role") not in ("customer","admin"): return jsonify({"error":"Customer account required"}),403
    d=request.json or {}
    con=db()
    con.execute("INSERT INTO opportunities(title,category,description,area,pay,work_type,posted_by) VALUES(?,?,?,?,?,?,?)",
      (d.get("title"),d.get("category"),d.get("description"),d.get("area"),float(d.get("pay") or 0),d.get("work_type","Flexible"),session["user_id"]))
    con.commit(); con.close()
    return jsonify({"ok":True})

@app.route("/api/my-applications")
@login_required
def my_applications():
    con=db()
    rows=con.execute("""SELECT a.status,o.title,o.area,o.pay,o.category FROM applications a
      JOIN opportunities o ON a.opportunity_id=o.id WHERE a.user_id=? ORDER BY a.id DESC""",(session["user_id"],)).fetchall()
    con.close(); return jsonify([dict(r) for r in rows])

@app.route("/api/profile",methods=["POST"])
@login_required
def profile():
    d=request.json or {}
    con=db()
    con.execute("UPDATE users SET area=?,skills=?,availability=?,bio=?,portfolio=? WHERE id=?",
      (d.get("area",""),d.get("skills",""),d.get("availability","Flexible"),d.get("bio",""),d.get("portfolio",""),session["user_id"]))
    con.commit(); con.close(); return jsonify({"ok":True})

@app.route("/api/earnings")
@login_required
def earnings():
    con=db()
    count=con.execute("SELECT COUNT(*) FROM applications WHERE user_id=? AND status='Selected'",(session["user_id"],)).fetchone()[0]
    con.close()
    return jsonify({"selected":count,"estimated":count*550})

@app.route("/api/admin")
@login_required
def admin():
    if session.get("role")!="admin": return jsonify({"error":"Admin access only"}),403
    con=db()
    users=[dict(r) for r in con.execute("SELECT id,name,phone,role,area,skills FROM users ORDER BY id DESC")]
    apps=[dict(r) for r in con.execute("""SELECT a.id,a.status,u.name woman,o.title opportunity FROM applications a
      JOIN users u ON a.user_id=u.id JOIN opportunities o ON a.opportunity_id=o.id ORDER BY a.id DESC""")]
    con.close(); return jsonify({"users":users,"applications":apps})

@app.route("/api/application-status",methods=["POST"])
@login_required
def application_status():
    if session.get("role")!="admin": return jsonify({"error":"Admin access only"}),403
    d=request.json or {}
    con=db(); con.execute("UPDATE applications SET status=? WHERE id=?",(d.get("status"),d.get("id"))); con.commit(); con.close()
    return jsonify({"ok":True})

@app.route("/api/reviews")
def reviews():
    con=db()
    rows=con.execute("""SELECT r.*,u.name provider FROM reviews r JOIN users u ON u.id=r.provider_id ORDER BY r.id DESC""").fetchall()
    con.close(); return jsonify([dict(r) for r in rows])

@app.route("/api/review",methods=["POST"])
@login_required
def review():
    d=request.json or {}
    con=db()
    con.execute("INSERT INTO reviews(provider_id,customer_name,rating,comment) VALUES(?,?,?,?)",
      (d.get("provider_id"),session.get("name"),int(d.get("rating",5)),d.get("comment","")))
    con.commit(); con.close(); return jsonify({"ok":True})



@app.route("/api/portfolio-upload",methods=["POST"])
@login_required
def portfolio_upload():
    if session.get("role")!="woman": return jsonify({"error":"Only provider accounts can upload portfolio work"}),403
    files=request.files.getlist("photos")
    if not files: return jsonify({"error":"Choose at least one image"}),400
    allowed={"png","jpg","jpeg","webp"}
    folder=os.path.join(os.path.dirname(__file__),"static","uploads")
    os.makedirs(folder,exist_ok=True)
    con=db()
    row=con.execute("SELECT portfolio FROM users WHERE id=?",(session["user_id"],)).fetchone()
    links=[x.strip() for x in (row["portfolio"] or "").splitlines() if x.strip()]
    for f in files[:5]:
        name=secure_filename(f.filename or "")
        ext=name.rsplit(".",1)[-1].lower() if "." in name else ""
        if ext not in allowed: continue
        f.stream.seek(0,os.SEEK_END); size=f.stream.tell(); f.stream.seek(0)
        if size>4*1024*1024: continue
        filename=f"{uuid.uuid4().hex}.{ext}"
        f.save(os.path.join(folder,filename))
        links.append("/static/uploads/"+filename)
    con.execute("UPDATE users SET portfolio=? WHERE id=?",( "\\n".join(links),session["user_id"]))
    con.commit(); con.close()
    return jsonify({"ok":True,"portfolio":"\\n".join(links)})

@app.route("/api/favorites")
@login_required
def favorites():
    con=db()
    rows=con.execute("""SELECT o.* FROM favorites f JOIN opportunities o ON o.id=f.opportunity_id
      WHERE f.user_id=? ORDER BY f.id DESC""",(session["user_id"],)).fetchall()
    con.close(); return jsonify([dict(r) for r in rows])

@app.route("/api/favorite",methods=["POST"])
@login_required
def favorite():
    d=request.json or {}; oid=d.get("opportunity_id")
    con=db()
    exists=con.execute("SELECT id FROM favorites WHERE user_id=? AND opportunity_id=?",(session["user_id"],oid)).fetchone()
    if exists:
        con.execute("DELETE FROM favorites WHERE id=?",(exists["id"],)); saved=False
    else:
        con.execute("INSERT OR IGNORE INTO favorites(user_id,opportunity_id) VALUES(?,?)",(session["user_id"],oid)); saved=True
    con.commit(); con.close(); return jsonify({"saved":saved})

@app.route("/api/community")
def community():
    con=db()
    rows=con.execute("""SELECT c.*,COUNT(cm.id) AS member_count FROM circles c
      LEFT JOIN circle_members cm ON cm.circle_id=c.id GROUP BY c.id ORDER BY c.name""").fetchall()
    con.close(); return jsonify([dict(r) for r in rows])

@app.route("/api/community/join",methods=["POST"])
@login_required
def community_join():
    d=request.json or {}; con=db()
    con.execute("INSERT OR IGNORE INTO circle_members(circle_id,user_id) VALUES(?,?)",(d.get("circle_id"),session["user_id"]))
    con.commit(); con.close(); return jsonify({"ok":True})

@app.route("/api/notifications")
@login_required
def notifications():
    con=db()
    rows=con.execute("SELECT id,message,created_at,seen FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 20",(session["user_id"],)).fetchall()
    con.close(); return jsonify([dict(r) for r in rows])

init_db()

if __name__ == "__main__":
    app.run(debug=True)

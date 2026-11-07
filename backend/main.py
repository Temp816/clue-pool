# -*- coding: utf-8 -*-
"""线索池 Beta 后端 — FastAPI + SQLite
信息安全设计：AI 推荐默认使用本地规则引擎，数据不出本机/内网；
外部 AI 接口（DeepSeek 等）仅管理员在管理端显式开启后才会被调用。"""
import os, io, json, time, base64, hashlib, sqlite3, secrets
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, Request, UploadFile, Form, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from itsdangerous import URLSafeSerializer
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 从 ai_config.json 加载配置（本地敏感配置，不进入版本库）
_cfg_path = os.path.join(BASE_DIR, "ai_config.json")
if os.path.exists(_cfg_path):
    with open(_cfg_path, encoding="utf-8") as _f:
        for _k, _v in json.load(_f).items():
            os.environ.setdefault(_k, str(_v))

DB_PATH = os.path.join(BASE_DIR, "cluepool.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

SECRET = os.environ.get("SECRET_KEY", "cluepool-beta-secret-2026")
signer = URLSafeSerializer(SECRET)

# ---- 外部 AI 配置（OpenAI 兼容接口；仅管理员开启后使用）----
AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://api.deepseek.com/v1")
AI_MODEL = os.environ.get("AI_MODEL", "deepseek-chat")
AI_VISION_MODEL = os.environ.get("AI_VISION_MODEL", "deepseek-chat")

CREDIBILITY = ["高", "中", "低"]
CLUE_STATUS = ["待补充", "待核实", "已核实", "已归档"]
ROLES = {"submitter": "提交人", "viewer": "查看人", "approver": "审批员", "admin": "管理员"}

DEFAULT_TAXONOMY = {
    "depts": ["原价", "CI"],
    "materials": ["结构件", "电子料", "化工料", "其他"],
    "topics": {
        "原价": ["供应商信息", "产品信息", "市场行情", "研发方向", "竞争对手动态", "政策动向", "其他"],
        "CI": ["行业动态", "竞争对手", "政策法规", "技术趋势", "客户信息", "厂商信息", "其他"],
    },
    "channels": {
        "原价": ["供应商出差", "展会出差", "日常交流", "其他"],
        "CI": ["网络调研", "实地调研", "展会会议", "专家交流", "其他"],
    },
}

# ---------------- DB ----------------
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def get_setting(conn, key, default=""):
    r = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default

def set_setting(conn, key, value):
    conn.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

def get_taxonomy(conn=None):
    close = False
    if conn is None: conn, close = db(), True
    raw = get_setting(conn, "taxonomy", "")
    if close: conn.close()
    try:
        return json.loads(raw) if raw else DEFAULT_TAXONOMY
    except Exception:
        return DEFAULT_TAXONOMY

def init_db():
    conn = db()
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS settings(
        key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        roles TEXT NOT NULL DEFAULT 'submitter,viewer',
        perms TEXT NOT NULL DEFAULT '结构件,电子料,化工料,CI',
        approve_scope TEXT DEFAULT '',   -- 审批员负责的范围：结构件/电子料/化工料/CI
        avatar TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS tag_presets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        depts TEXT DEFAULT '',
        material TEXT DEFAULT '',
        category TEXT DEFAULT '',
        channel TEXT DEFAULT '',
        keywords TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS clues(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT DEFAULT '',
        source TEXT DEFAULT '',          -- 来源身份（自由文本）
        scene TEXT DEFAULT '',           -- 获取场景/地点
        acquired_at TEXT DEFAULT '',     -- 获取时间
        dept TEXT DEFAULT '',            -- 条线，逗号分隔：原价,CI
        material TEXT DEFAULT '',        -- 物料类别（原价条线）
        category TEXT DEFAULT '',        -- 信息主题（单选）
        channel TEXT DEFAULT '',         -- 获取方式
        keywords TEXT DEFAULT '',        -- 关键词标签，逗号分隔
        credibility TEXT DEFAULT '中',
        status TEXT DEFAULT '待核实',
        approval TEXT DEFAULT '待审批',   -- 待审批/已通过/已驳回
        approved_by TEXT DEFAULT '',      -- 审批人姓名
        approved_at TEXT DEFAULT '',
        approval_comment TEXT DEFAULT '',
        submitter_id INTEGER NOT NULL,
        images TEXT DEFAULT '[]',
        views INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS likes(
        user_id INTEGER NOT NULL, clue_id INTEGER NOT NULL,
        created_at TEXT NOT NULL, PRIMARY KEY(user_id, clue_id));
    CREATE TABLE IF NOT EXISTS favorites(
        user_id INTEGER NOT NULL, clue_id INTEGER NOT NULL,
        created_at TEXT NOT NULL, PRIMARY KEY(user_id, clue_id));
    CREATE TABLE IF NOT EXISTS follows(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        target_type TEXT NOT NULL,       -- submitter | category
        target_value TEXT NOT NULL,
        is_public INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        UNIQUE(user_id, target_type, target_value));
    CREATE TABLE IF NOT EXISTS personal_tags(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL, clue_id INTEGER NOT NULL,
        tag TEXT NOT NULL, created_at TEXT NOT NULL,
        UNIQUE(user_id, clue_id, tag));
    """)
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        now = datetime.now().isoformat(timespec="seconds")
        def h(p): return hashlib.sha256(("cluepool::" + p).encode()).hexdigest()
        c.execute("INSERT INTO users(username,password_hash,name,roles,created_at) VALUES(?,?,?,?,?)",
                  ("admin", h("admin123"), "管理员", "submitter,viewer,admin", now))
        c.execute("INSERT INTO users(username,password_hash,name,roles,perms,created_at) VALUES(?,?,?,?,?,?)",
                  ("demo", h("demo123"), "演示用户", "submitter,viewer", "结构件,电子料,CI", now))
        c.execute("INSERT INTO users(username,password_hash,name,roles,perms,approve_scope,created_at) VALUES(?,?,?,?,?,?,?)",
                  ("reviewer", h("review123"), "审批员", "viewer,approver", "结构件,电子料,化工料,CI", "结构件", now))
        set_setting(conn, "taxonomy", json.dumps(DEFAULT_TAXONOMY, ensure_ascii=False))
        set_setting(conn, "ai_external_enabled", "0")
        samples = [
            ("竞品A计划下季度对电子料产品线降价10%-15%", "在行业交流会上从客户采购经理处获悉，竞品A正在制定明年Q1的价格调整方案，电容电阻等主力电子料预计降价10%-15%，意在抢占中端市场份额。", "某客户采购经理", "行业交流会现场", "2026-11-06 15:30", "原价", "电子料", "市场行情", "展会出差", "竞品A,降价,价格战", "中", "待核实", 1, 12, 3),
            ("供应商B注塑模具产能紧张", "赴供应商B工厂考察时发现其注塑产线排产已满至明年2月，交期可能延长。供应商确认正在扩产但进度不明。", "供应商B生产主管", "供应商工厂", "2026-11-05 14:00", "原价", "结构件", "供应商信息", "供应商出差", "供应商B,注塑,交期", "高", "已核实", 1, 21, 9),
            ("某省拟出台化工原料安全管理新规", "与同行交流时听说，某省监管部门正在起草化工原料存储新规，可能影响涂料胶水类物料的仓储成本。未经官方证实，建议持续跟踪。", "同行企业信息主管", "午餐交流", "2026-11-05 12:20", "原价,CI", "化工料", "政策动向", "日常交流", "化工,新规,仓储", "中", "待核实", 2, 8, 5),
            ("头部客户透露明年预算向数字化倾斜", "客户拜访时获悉，该客户明年IT预算同比增长约20%，重点投向数字化改造。决策人为信息部总监，预计12月启动招标。", "客户信息部员工", "客户拜访", "2026-11-04 10:00", "CI", "", "客户信息", "实地调研", "预算,数字化,招标", "高", "已核实", 1, 15, 6),
            ("AI视觉检测在电子料质检环节成本下降明显", "行业公众号文章提到，AI视觉检测方案整体成本较去年下降约40%，多家厂商在PCB检测环节规模化落地。", "公开公众号文章", "日常信息监测", "2026-11-03 09:15", "CI", "电子料", "技术趋势", "网络调研", "AI,视觉检测,PCB", "高", "已归档", 2, 15, 2),
            ("听说某厂商在接触我们的核心供应商", "", "", "", "", "原价", "结构件", "竞争对手动态", "供应商出差", "", "中", "待补充", 2, 3, 0),
        ]
        for s in samples:
            c.execute("""INSERT INTO clues(title,content,source,scene,acquired_at,dept,material,category,channel,keywords,
                credibility,status,submitter_id,images,views,likes,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (*s[:13], '[]', s[13], s[14], now, now))
    # 历史数据迁移：条线 IC 更名为 CI（幂等，重复执行无副作用）
    def _ci(v):
        return ",".join("CI" if t == "IC" else t for t in (v or "").split(","))
    for row in c.execute("SELECT id, dept FROM clues").fetchall():
        nv = _ci(row[1])
        if nv != row[1]: c.execute("UPDATE clues SET dept=? WHERE id=?", (nv, row[0]))
    for row in c.execute("SELECT id, perms, approve_scope FROM users").fetchall():
        np_, ns = _ci(row[1]), _ci(row[2])
        if np_ != row[1] or ns != row[2]:
            c.execute("UPDATE users SET perms=?, approve_scope=? WHERE id=?", (np_, ns, row[0]))
    for row in c.execute("SELECT id, depts FROM tag_presets").fetchall():
        nv = _ci(row[1])
        if nv != row[1]: c.execute("UPDATE tag_presets SET depts=? WHERE id=?", (nv, row[0]))
    conn.commit(); conn.close()

def hash_pw(p): return hashlib.sha256(("cluepool::" + p).encode()).hexdigest()
def now(): return datetime.now().isoformat(timespec="seconds")

# ---------------- 查看权限 ----------------
# 四个受控范围：结构件/电子料/化工料(原价物料) + CI(条线)。其他标签全员可见。
PERM_SCOPES = ["结构件", "电子料", "化工料", "CI"]

def visible_filter(u):
    """返回 (sql片段, 参数)。规则：线索的受控范围（物料为三类之一 或 条线含IC）中，
    用户拥有任意一个对应授权即可查看；不受控线索（其他）全员可见；本人提交的永远可见；管理员全部可见。"""
    if "admin" in u["roles"].split(","):
        return "1=1", []
    perms = set(filter(None, (u.get("perms") or "").split(",")))
    allowed, args = [], []
    mats_have = [m for m in PERM_SCOPES[:3] if m in perms]
    if mats_have:
        allowed.append("material IN (%s)" % ",".join("?" * len(mats_have)))
        args += mats_have
    if "CI" in perms:
        allowed.append("(','||dept||',') LIKE '%,CI,%'")
    allowed.append("submitter_id=?")
    args.append(u["id"])
    restricted = "(material IN ('结构件','电子料','化工料') OR (','||dept||',') LIKE '%,CI,%')"
    return f"(NOT {restricted} OR {' OR '.join(allowed)})", args

def clue_scopes(clue_row):
    """线索所属的受控范围集合：物料三类 + CI"""
    scopes = set()
    if clue_row["material"] in PERM_SCOPES[:3]:
        scopes.add(clue_row["material"])
    if "CI" in (clue_row["dept"] or "").split(","):
        scopes.add("CI")
    return scopes

def can_approve(u, clue_row):
    """管理员可审批全部；审批员可审批其负责范围内的线索（线索含该范围即可）；无受控范围的线索任何审批员均可审批"""
    roles = u["roles"].split(",")
    if "admin" in roles: return True
    if "approver" not in roles: return False
    scopes = clue_scopes(clue_row)
    if not scopes: return True
    return u.get("approve_scope") in scopes

# ---------------- App ----------------
app = FastAPI(title="线索池 Beta")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

def current_user(req: Request):
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "未登录")
    try:
        data = signer.loads(auth[7:])
    except Exception:
        raise HTTPException(401, "登录已过期")
    conn = db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (data["uid"],)).fetchone()
    conn.close()
    if not u: raise HTTPException(401, "用户不存在")
    return dict(u)

def require_admin(u=Depends(current_user)):
    if "admin" not in u["roles"].split(","): raise HTTPException(403, "需要管理员权限")
    return u

def make_token(uid): return signer.dumps({"uid": uid})

def clue_out(r, uid=None, conn=None):
    d = dict(r)
    d["images"] = json.loads(d.get("images") or "[]")
    d["keywords"] = [k for k in (d.get("keywords") or "").split(",") if k]
    d["depts"] = [x for x in (d.get("dept") or "").split(",") if x]
    close = False
    if conn is None: conn, close = db(), True
    s = conn.execute("SELECT id,username,name,avatar FROM users WHERE id=?", (d["submitter_id"],)).fetchone()
    d["submitter_name"] = s["name"] if s else "未知"
    d["submitter_avatar"] = (s["avatar"] if s else "") or ""
    if uid:
        d["liked"] = bool(conn.execute("SELECT 1 FROM likes WHERE user_id=? AND clue_id=?", (uid, d["id"])).fetchone())
        d["favorited"] = bool(conn.execute("SELECT 1 FROM favorites WHERE user_id=? AND clue_id=?", (uid, d["id"])).fetchone())
        d["my_tags"] = [r["tag"] for r in conn.execute("SELECT tag FROM personal_tags WHERE user_id=? AND clue_id=?", (uid, d["id"]))]
    if close: conn.close()
    return d

# ---------------- Auth API ----------------
@app.post("/api/login")
def login(body: dict):
    conn = db()
    u = conn.execute("SELECT * FROM users WHERE username=?", (body.get("username", ""),)).fetchone()
    conn.close()
    if not u or u["password_hash"] != hash_pw(body.get("password", "")):
        raise HTTPException(400, "用户名或密码错误")
    d = dict(u); d.pop("password_hash")
    d["role_names"] = [ROLES[r] for r in u["roles"].split(",") if r in ROLES]
    return {"token": make_token(u["id"]), "user": d}

@app.get("/api/me")
def me(u=Depends(current_user)):
    u.pop("password_hash", None)
    u["role_names"] = [ROLES[r] for r in u["roles"].split(",") if r in ROLES]
    return u

@app.post("/api/change-password")
def change_pw(body: dict, u=Depends(current_user)):
    conn = db()
    if u["password_hash"] != hash_pw(body.get("old", "")):
        conn.close(); raise HTTPException(400, "原密码错误")
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_pw(body.get("new", "")), u["id"]))
    conn.commit(); conn.close()
    return {"ok": True}

# ---------------- Meta ----------------
@app.get("/api/meta")
def meta(u=Depends(current_user)):
    conn = db()
    submitters = [dict(r) for r in conn.execute(
        "SELECT DISTINCT u.id,u.name FROM users u JOIN clues c ON c.submitter_id=u.id ORDER BY u.name")]
    ai_on = get_setting(conn, "ai_external_enabled", "0") == "1" and bool(AI_API_KEY)
    conn.close()
    return {"taxonomy": get_taxonomy(), "credibility": CREDIBILITY, "status": CLUE_STATUS,
            "roles": ROLES, "submitters": submitters,
            "ai_enabled": ai_on,          # 外部AI是否可用（管理员开启+已配Key）
            "ai_suggest": True}           # 智能推荐（本地引擎）始终可用

# ---------------- Clues ----------------
CLUE_FIELDS = ("title", "content", "source", "scene", "acquired_at",
               "material", "category", "channel", "credibility", "status")

@app.post("/api/clues")
def create_clue(body: dict, u=Depends(current_user)):
    if "submitter" not in u["roles"].split(","): raise HTTPException(403, "您没有提交人角色")
    title = (body.get("title") or "").strip()
    if not title: raise HTTPException(400, "请填写线索标题")
    t = now()
    dept = ",".join([d for d in (body.get("depts") or []) if d])
    conn = db()
    cur = conn.execute("""INSERT INTO clues(title,content,source,scene,acquired_at,dept,material,category,channel,
        keywords,credibility,status,submitter_id,images,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (title, body.get("content", ""), body.get("source", ""), body.get("scene", ""),
         body.get("acquired_at", ""), dept, body.get("material", ""), body.get("category", ""),
         body.get("channel", ""), ",".join(body.get("keywords") or []), body.get("credibility", "中"),
         body.get("status", "待核实"), u["id"], json.dumps(body.get("images") or []), t, t))
    conn.commit()
    row = conn.execute("SELECT * FROM clues WHERE id=?", (cur.lastrowid,)).fetchone()
    out = clue_out(row, u["id"], conn); conn.close()
    return out

@app.get("/api/clues")
def list_clues(req: Request, u=Depends(current_user)):
    q = req.query_params
    where, args = ["1=1"], []
    vis_sql, vis_args = visible_filter(u)
    where.append(vis_sql); args += vis_args
    if q.get("keyword"):
        where.append("(title LIKE ? OR content LIKE ? OR keywords LIKE ?)")
        k = f"%{q['keyword']}%"; args += [k, k, k]
    if q.get("dept"): where.append("(','||dept||',') LIKE ?"); args.append(f"%,{q['dept']},%")
    if q.get("material"): where.append("material=?"); args.append(q["material"])
    if q.get("category"): where.append("category=?"); args.append(q["category"])
    if q.get("channel"): where.append("channel=?"); args.append(q["channel"])
    if q.get("submitter_id"): where.append("submitter_id=?"); args.append(q["submitter_id"])
    if q.get("status"): where.append("status=?"); args.append(q["status"])
    if q.get("approval"): where.append("approval=?"); args.append(q["approval"])
    if q.get("credibility"): where.append("credibility=?"); args.append(q["credibility"])
    if q.get("date_from"): where.append("created_at>=?"); args.append(q["date_from"])
    if q.get("date_to"): where.append("created_at<=?"); args.append(q["date_to"] + "T23:59:59")
    if q.get("my_tags"):
        where.append("id IN (SELECT clue_id FROM personal_tags WHERE user_id=? AND tag=?)")
        args += [u["id"], q["my_tags"]]
    if q.get("mine") == "1": where.append("submitter_id=?"); args.append(u["id"])
    if q.get("fav") == "1":
        where.append("id IN (SELECT clue_id FROM favorites WHERE user_id=?)"); args.append(u["id"])
    if q.get("following") == "1":
        where.append("""(submitter_id IN (SELECT CAST(target_value AS INTEGER) FROM follows WHERE user_id=? AND target_type='submitter')
                        OR category IN (SELECT target_value FROM follows WHERE user_id=? AND target_type='category'))""")
        args += [u["id"], u["id"]]
    order = {
        "fresh": "created_at DESC",
        "hot": "(likes*3 + views*0.5) / (1 + (julianday('now','localtime') - julianday(created_at))) DESC, created_at DESC",
        "views": "views DESC, created_at DESC",
        "likes": "likes DESC, created_at DESC",
    }.get(q.get("sort", "fresh"), "created_at DESC")
    conn = db()
    rows = conn.execute(f"SELECT * FROM clues WHERE {' AND '.join(where)} ORDER BY {order} LIMIT 200", args).fetchall()
    out = [clue_out(r, u["id"], conn) for r in rows]
    conn.close()
    return {"items": out, "total": len(out)}

@app.get("/api/clues/{cid}")
def clue_detail(cid: int, u=Depends(current_user)):
    conn = db()
    r = conn.execute("SELECT * FROM clues WHERE id=?", (cid,)).fetchone()
    if not r: conn.close(); raise HTTPException(404, "线索不存在")
    vis_sql, vis_args = visible_filter(u)
    ok = conn.execute(f"SELECT 1 FROM clues WHERE id=? AND {vis_sql}", (cid, *vis_args)).fetchone()
    if not ok: conn.close(); raise HTTPException(403, "您没有查看该线索的权限")
    conn.execute("UPDATE clues SET views=views+1 WHERE id=?", (cid,))
    conn.commit()
    r = conn.execute("SELECT * FROM clues WHERE id=?", (cid,)).fetchone()
    out = clue_out(r, u["id"], conn)
    out["can_approve"] = can_approve(u, r)
    conn.close()
    return out

@app.patch("/api/clues/{cid}")
def update_clue(cid: int, body: dict, u=Depends(current_user)):
    conn = db()
    r = conn.execute("SELECT * FROM clues WHERE id=?", (cid,)).fetchone()
    if not r: conn.close(); raise HTTPException(404, "线索不存在")
    is_admin = "admin" in u["roles"].split(",")
    if r["submitter_id"] != u["id"] and not is_admin:
        conn.close(); raise HTTPException(403, "只能修改自己提交的线索")
    fields = {k: v for k, v in body.items() if k in CLUE_FIELDS}
    if "depts" in body: fields["dept"] = ",".join([d for d in body["depts"] if d])
    if "keywords" in body: fields["keywords"] = ",".join(body["keywords"])
    if "images" in body: fields["images"] = json.dumps(body["images"])
    if "status" in fields and not is_admin: del fields["status"]
    if fields:
        fields["updated_at"] = now()
        if "status" not in fields and r["status"] == "待补充" and body.get("content"):
            fields["status"] = "待核实"
        sql = ",".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE clues SET {sql} WHERE id=?", (*fields.values(), cid))
        conn.commit()
    out = clue_out(conn.execute("SELECT * FROM clues WHERE id=?", (cid,)).fetchone(), u["id"], conn)
    conn.close(); return out

@app.delete("/api/clues/{cid}")
def delete_clue(cid: int, u=Depends(current_user)):
    conn = db()
    r = conn.execute("SELECT * FROM clues WHERE id=?", (cid,)).fetchone()
    if not r: conn.close(); raise HTTPException(404, "线索不存在")
    if r["submitter_id"] != u["id"] and "admin" not in u["roles"].split(","):
        conn.close(); raise HTTPException(403, "无权删除")
    for t in ("clues", "likes", "favorites", "personal_tags"):
        col = "clue_id" if t != "clues" else "id"
        conn.execute(f"DELETE FROM {t} WHERE {col}=?", (cid,))
    conn.commit(); conn.close()
    return {"ok": True}

# ---------------- 审批 ----------------
@app.post("/api/clues/{cid}/approve")
def approve_clue(cid: int, body: dict, u=Depends(current_user)):
    action = body.get("action")  # pass | reject | reset
    if action not in ("pass", "reject", "reset"): raise HTTPException(400, "非法操作")
    conn = db()
    r = conn.execute("SELECT * FROM clues WHERE id=?", (cid,)).fetchone()
    if not r: conn.close(); raise HTTPException(404, "线索不存在")
    if not can_approve(u, r):
        conn.close()
        scope = u.get("approve_scope") or "未分配"
        raise HTTPException(403, f"您的审批范围为「{scope}」，无权审批该线索")
    if action == "pass":
        conn.execute("UPDATE clues SET approval='已通过', approved_by=?, approved_at=?, approval_comment=? WHERE id=?",
                     (u["name"], now(), body.get("comment", ""), cid))
    elif action == "reject":
        conn.execute("UPDATE clues SET approval='已驳回', approved_by=?, approved_at=?, approval_comment=? WHERE id=?",
                     (u["name"], now(), body.get("comment", ""), cid))
    else:
        conn.execute("UPDATE clues SET approval='待审批', approved_by='', approved_at='', approval_comment='' WHERE id=?", (cid,))
    conn.commit()
    out = clue_out(conn.execute("SELECT * FROM clues WHERE id=?", (cid,)).fetchone(), u["id"], conn)
    out["can_approve"] = can_approve(u, conn.execute("SELECT * FROM clues WHERE id=?", (cid,)).fetchone())
    conn.close(); return out

# ---------------- 头像 ----------------
@app.post("/api/me/avatar")
async def upload_avatar(file: UploadFile, u=Depends(current_user)):
    ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp"): raise HTTPException(400, "仅支持图片格式")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024: raise HTTPException(400, "头像不能超过5MB")
    name = f"avatar_{u['id']}_{secrets.token_hex(3)}{ext}"
    with open(os.path.join(UPLOAD_DIR, name), "wb") as f: f.write(data)
    url = f"/uploads/{name}"
    conn = db()
    conn.execute("UPDATE users SET avatar=? WHERE id=?", (url, u["id"]))
    conn.commit(); conn.close()
    return {"avatar": url}

# ---------------- 互动 ----------------
@app.post("/api/clues/{cid}/like")
def toggle_like(cid: int, u=Depends(current_user)):
    conn = db()
    ex = conn.execute("SELECT 1 FROM likes WHERE user_id=? AND clue_id=?", (u["id"], cid)).fetchone()
    if ex:
        conn.execute("DELETE FROM likes WHERE user_id=? AND clue_id=?", (u["id"], cid))
        conn.execute("UPDATE clues SET likes=MAX(0,likes-1) WHERE id=?", (cid,)); liked = False
    else:
        conn.execute("INSERT INTO likes VALUES(?,?,?)", (u["id"], cid, now()))
        conn.execute("UPDATE clues SET likes=likes+1 WHERE id=?", (cid,)); liked = True
    likes = conn.execute("SELECT likes FROM clues WHERE id=?", (cid,)).fetchone()[0]
    conn.commit(); conn.close()
    return {"liked": liked, "likes": likes}

@app.post("/api/clues/{cid}/favorite")
def toggle_fav(cid: int, u=Depends(current_user)):
    conn = db()
    ex = conn.execute("SELECT 1 FROM favorites WHERE user_id=? AND clue_id=?", (u["id"], cid)).fetchone()
    if ex:
        conn.execute("DELETE FROM favorites WHERE user_id=? AND clue_id=?", (u["id"], cid)); fav = False
    else:
        conn.execute("INSERT INTO favorites VALUES(?,?,?)", (u["id"], cid, now())); fav = True
    conn.commit(); conn.close()
    return {"favorited": fav}

# ---------------- 关注 ----------------
@app.get("/api/follows")
def my_follows(u=Depends(current_user)):
    conn = db()
    rows = conn.execute("SELECT * FROM follows WHERE user_id=? ORDER BY created_at DESC", (u["id"],)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        if d["target_type"] == "submitter":
            s = conn.execute("SELECT name FROM users WHERE id=?", (int(d["target_value"]),)).fetchone()
            d["target_name"] = s["name"] if s else "已删除用户"
        else:
            d["target_name"] = d["target_value"]
        out.append(d)
    conn.close()
    return {"follows": out}

@app.post("/api/follows")
def add_follow(body: dict, u=Depends(current_user)):
    tt, tv = body.get("target_type"), str(body.get("target_value"))
    if tt not in ("submitter", "category"): raise HTTPException(400, "非法关注类型")
    conn = db()
    conn.execute("INSERT OR IGNORE INTO follows(user_id,target_type,target_value,is_public,created_at) VALUES(?,?,?,?,?)",
                 (u["id"], tt, tv, 1 if body.get("is_public", True) else 0, now()))
    conn.commit(); conn.close()
    return {"ok": True}

@app.patch("/api/follows/{fid}")
def update_follow(fid: int, body: dict, u=Depends(current_user)):
    conn = db()
    conn.execute("UPDATE follows SET is_public=? WHERE id=? AND user_id=?",
                 (1 if body.get("is_public") else 0, fid, u["id"]))
    conn.commit(); conn.close()
    return {"ok": True}

@app.delete("/api/follows/{fid}")
def del_follow(fid: int, u=Depends(current_user)):
    conn = db()
    conn.execute("DELETE FROM follows WHERE id=? AND user_id=?", (fid, u["id"]))
    conn.commit(); conn.close()
    return {"ok": True}

# ---------------- 个人标签 ----------------
@app.post("/api/clues/{cid}/my-tags")
def add_my_tag(cid: int, body: dict, u=Depends(current_user)):
    tag = (body.get("tag") or "").strip()
    if not tag: raise HTTPException(400, "标签不能为空")
    conn = db()
    conn.execute("INSERT OR IGNORE INTO personal_tags(user_id,clue_id,tag,created_at) VALUES(?,?,?,?)",
                 (u["id"], cid, tag, now()))
    conn.commit()
    tags = [r["tag"] for r in conn.execute("SELECT tag FROM personal_tags WHERE user_id=? AND clue_id=?", (u["id"], cid))]
    conn.close(); return {"my_tags": tags}

@app.delete("/api/clues/{cid}/my-tags")
def del_my_tag(cid: int, tag: str, u=Depends(current_user)):
    conn = db()
    conn.execute("DELETE FROM personal_tags WHERE user_id=? AND clue_id=? AND tag=?", (u["id"], cid, tag))
    conn.commit(); conn.close()
    return {"ok": True}

@app.get("/api/my-tags")
def my_tag_list(u=Depends(current_user)):
    conn = db()
    rows = conn.execute("SELECT tag, COUNT(*) c FROM personal_tags WHERE user_id=? GROUP BY tag ORDER BY c DESC", (u["id"],)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ---------------- 标签组合预设 ----------------
@app.get("/api/presets")
def list_presets(u=Depends(current_user)):
    conn = db()
    rows = [dict(r) for r in conn.execute("SELECT * FROM tag_presets WHERE user_id=? ORDER BY created_at DESC", (u["id"],))]
    conn.close()
    for r in rows:
        r["depts"] = [x for x in (r["depts"] or "").split(",") if x]
        r["keywords"] = [x for x in (r["keywords"] or "").split(",") if x]
    return rows

@app.post("/api/presets")
def create_preset(body: dict, u=Depends(current_user)):
    name = (body.get("name") or "").strip()
    if not name: raise HTTPException(400, "请为标签组合命名")
    conn = db()
    conn.execute("""INSERT INTO tag_presets(user_id,name,depts,material,category,channel,keywords,created_at)
                    VALUES(?,?,?,?,?,?,?,?)""",
                 (u["id"], name, ",".join(body.get("depts") or []), body.get("material", ""),
                  body.get("category", ""), body.get("channel", ""),
                  ",".join(body.get("keywords") or []), now()))
    conn.commit(); conn.close()
    return {"ok": True}

@app.delete("/api/presets/{pid}")
def delete_preset(pid: int, u=Depends(current_user)):
    conn = db()
    conn.execute("DELETE FROM tag_presets WHERE id=? AND user_id=?", (pid, u["id"]))
    conn.commit(); conn.close()
    return {"ok": True}

# ---------------- 上传 ----------------
@app.post("/api/upload")
async def upload(file: UploadFile, u=Depends(current_user)):
    ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"): raise HTTPException(400, "仅支持图片")
    name = f"{int(time.time()*1000)}_{secrets.token_hex(4)}{ext}"
    data = await file.read()
    if len(data) > 10 * 1024 * 1024: raise HTTPException(400, "图片不能超过10MB")
    with open(os.path.join(UPLOAD_DIR, name), "wb") as f: f.write(data)
    return {"url": f"/uploads/{name}"}

# ---------------- 智能推荐 ----------------
# 本地规则引擎：关键词 → 条线/主题/物料/标签。数据不出本机。
LOCAL_RULES = [
    # (关键词列表, dept, topic, material, tags)
    (["降价", "涨价", "价格", "报价", "行情", "市场份额"], "原价", "市场行情", "", []),
    (["供应商", "产能", "交期", "工厂", "审核"], "原价", "供应商信息", "", ["供应商"]),
    (["竞品", "对手", "友商", "竞争"], "", "竞争对手动态", "", []),
    (["新规", "政策", "法规", "监管", "合规", "办法"], "", "政策动向", "", ["政策"]),
    (["研发", "新技术", "专利", "路线图"], "", "研发方向", "", []),
    (["客户", "招标", "预算", "订单", "需求"], "CI", "客户信息", "", ["客户"]),
    (["AI", "算法", "视觉检测", "自动化", "数字化"], "CI", "技术趋势", "", []),
    (["展会", "论坛", "峰会"], "", "", "", ["展会"]),
    (["专家", "访谈"], "CI", "", "", []),
    (["钣金", "注塑", "模具", "压铸", "五金", "结构件", "外壳"], "", "", "结构件", ["结构件"]),
    (["芯片", "PCB", "电容", "电阻", "元器件", "电子料", "IC"], "", "", "电子料", ["电子料"]),
    (["涂料", "胶水", "塑料", "化工", "油墨"], "", "", "化工料", ["化工料"]),
]
# CI 条线下的主题映射修正
IC_TOPIC_MAP = {"竞争对手动态": "竞争对手", "政策动向": "政策法规", "研发方向": "技术趋势", "市场行情": "行业动态"}

def local_suggest(title, content, taxonomy):
    text = (title or "") + " " + (content or "")
    dept, topic, material, tags = "", "", "", []
    for kws, d, tp, mt, tg in LOCAL_RULES:
        hit = [k for k in kws if k.lower() in text.lower()]
        if hit:
            if d and not dept: dept = d
            if tp and not topic: topic = tp
            if mt and not material: material = mt
            tags += hit + tg
    if dept == "CI" and topic in IC_TOPIC_MAP: topic = IC_TOPIC_MAP[topic]
    if not dept: dept = "CI" if topic in taxonomy["topics"].get("CI", []) else "原价"
    if not topic: topic = "其他"
    # 主题必须在所选条线的可选范围内，否则落到该条线的"其他"
    valid = taxonomy["topics"].get(dept, [])
    if topic not in valid:
        alt = [x for x in taxonomy["depts"] if topic in taxonomy["topics"].get(x, [])]
        if alt and not dept: dept = alt[0]
        elif topic not in valid: topic = "其他"
    if material and material not in taxonomy["materials"]: material = ""
    # 去重保序
    seen, out = set(), []
    for t in tags:
        if t not in seen: seen.add(t); out.append(t)
    return {"depts": [dept] if dept else [], "category": topic, "material": material,
            "tags": out[:5], "ai": False, "engine": "local"}

def ai_chat(messages, model=None, timeout=40):
    req = urllib.request.Request(
        AI_BASE_URL.rstrip("/") + "/chat/completions",
        data=json.dumps({"model": model or AI_MODEL, "messages": messages, "temperature": 0.3}).encode(),
        headers={"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]

@app.post("/api/ai/suggest")
def ai_suggest(body: dict, u=Depends(current_user)):
    conn = db()
    tax = get_taxonomy(conn)
    ai_on = get_setting(conn, "ai_external_enabled", "0") == "1" and bool(AI_API_KEY)
    conn.close()
    text = f"标题：{body.get('title','')}\n内容：{body.get('content','')}"
    if ai_on:
        try:
            all_topics = {d: tax["topics"].get(d, []) for d in tax["depts"]}
            out = ai_chat([{"role": "system", "content":
                f"""你是企业情报线索分类助手。根据线索标题和内容进行分类。
条线（可多选）：{'、'.join(tax['depts'])}。原价=成本/物料相关；CI=课题调研相关。
各条线的信息主题（单选，选最相关一个）：{json.dumps(all_topics, ensure_ascii=False)}
物料类别（仅原价条线，可选）：{'、'.join(tax['materials'])}
另提取3-5个关键词标签。
只返回JSON：{{"depts":["条线"],"category":"主题","material":"物料或空","tags":["标签"]}}，不要输出其他内容。"""},
                {"role": "user", "content": text}])
            s = out[out.find("{"): out.rfind("}") + 1]
            d = json.loads(s)
            d["ai"] = True; d["engine"] = "external"
            return d
        except Exception:
            pass
    return local_suggest(body.get("title", ""), body.get("content", ""), tax)

@app.post("/api/ai/ocr")
async def ai_ocr(file: UploadFile, u=Depends(current_user)):
    """OCR 依赖多模态大模型，必须开启外部AI且模型支持视觉；默认关闭以保障信息安全。"""
    conn = db()
    ai_on = get_setting(conn, "ai_external_enabled", "0") == "1" and bool(AI_API_KEY)
    conn.close()
    if not ai_on:
        return {"text": "", "ai": False, "msg": "外部AI未开启，图片文字识别不可用（可在管理端开启）"}
    data = await file.read()
    b64 = base64.b64encode(data).decode()
    mime = file.content_type or "image/jpeg"
    try:
        out = ai_chat([{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            {"type": "text", "text": "请识别图片中的全部文字，原样输出，不要添加任何解释。"}]}],
            model=AI_VISION_MODEL, timeout=60)
        return {"text": out.strip(), "ai": True}
    except Exception:
        return {"text": "", "ai": False, "msg": "识别失败，请手动输入"}

# ---------------- 管理员 ----------------
@app.get("/api/admin/users")
def admin_users(u=Depends(require_admin)):
    conn = db()
    rows = [dict(r) for r in conn.execute("SELECT id,username,name,roles,perms,approve_scope,avatar,created_at FROM users ORDER BY id")]
    for r in rows:
        r["role_names"] = [ROLES[x] for x in r["roles"].split(",") if x in ROLES]
        r["perm_list"] = [x for x in r["perms"].split(",") if x]
    conn.close(); return rows

def _valid_perms(lst):
    if lst is None: return None
    return ",".join([p for p in lst if p in PERM_SCOPES])

@app.post("/api/admin/users")
def admin_create_user(body: dict, u=Depends(require_admin)):
    username = (body.get("username") or "").strip()
    name = (body.get("name") or "").strip()
    password = body.get("password") or ""
    roles = [r for r in (body.get("roles") or []) if r in ROLES]
    if not username or not name or not password or not roles:
        raise HTTPException(400, "请完整填写用户名、姓名、密码和角色")
    perms = _valid_perms(body.get("perms"))
    if perms is None: perms = ",".join(PERM_SCOPES)
    scope = body.get("approve_scope") or ""
    if scope and scope not in PERM_SCOPES: scope = ""
    conn = db()
    try:
        conn.execute("INSERT INTO users(username,password_hash,name,roles,perms,approve_scope,created_at) VALUES(?,?,?,?,?,?,?)",
                     (username, hash_pw(password), name, ",".join(roles), perms, scope, now()))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close(); raise HTTPException(400, "用户名已存在")
    conn.close(); return {"ok": True}

@app.patch("/api/admin/users/{uid}")
def admin_update_user(uid: int, body: dict, u=Depends(require_admin)):
    conn = db()
    if body.get("password"):
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_pw(body["password"]), uid))
    if body.get("roles"):
        roles = [r for r in body["roles"] if r in ROLES]
        if roles: conn.execute("UPDATE users SET roles=? WHERE id=?", (",".join(roles), uid))
    if body.get("name"):
        conn.execute("UPDATE users SET name=? WHERE id=?", (body["name"], uid))
    perms = _valid_perms(body.get("perms"))
    if perms is not None:
        conn.execute("UPDATE users SET perms=? WHERE id=?", (perms, uid))
    if "approve_scope" in body:
        scope = body.get("approve_scope") or ""
        if scope and scope not in PERM_SCOPES: scope = ""
        conn.execute("UPDATE users SET approve_scope=? WHERE id=?", (scope, uid))
    conn.commit(); conn.close()
    return {"ok": True}

# ---- 账号批量导入 ----
ROLE_ALIAS = {"提交人": "submitter", "查看人": "viewer", "管理员": "admin", "全部": "all"}

@app.get("/api/admin/users/template")
def admin_user_template(u=Depends(require_admin)):
    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "账号导入模板"
    ws.append(["用户名", "姓名", "密码", "角色", "查看权限", "审批范围"])
    ws.append(["zhangsan", "张三", "123456", "提交人,查看人", "结构件,电子料,化工料,CI", ""])
    ws.append(["lisi", "李四", "123456", "查看人", "CI", ""])
    ws.append(["shenpi1", "王审批", "123456", "查看人,审批员", "结构件,电子料,化工料,CI", "结构件"])
    ws.append([])
    ws.append(["说明：角色可选 提交人/查看人/审批员/管理员，多个用英文逗号分隔；"])
    ws.append(["查看权限可选 结构件/电子料/化工料/CI，多个用英文逗号分隔，填“全部”表示四类全部授权；"])
    ws.append(["审批范围仅审批员需要填写：结构件/电子料/化工料/CI 中的一项；"])
    ws.append(["标为“其他”的线索所有人可见，无需授权。"])
    from openpyxl.utils import get_column_letter
    for i in range(1, 7): ws.column_dimensions[get_column_letter(i)].width = 22
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": "attachment; filename=user-import-template.xlsx"})

@app.post("/api/admin/users/import")
async def admin_import_users(file: UploadFile, u=Depends(require_admin)):
    import openpyxl
    data = await file.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data))
    except Exception:
        raise HTTPException(400, "文件无法解析，请使用模板提供的 xlsx 格式")
    ws = wb.active
    created, skipped = [], []
    conn = db()
    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or not row[0]: continue
        username = str(row[0]).strip()
        name = str(row[1] or "").strip()
        password = str(row[2] or "").strip()
        roles_raw = str(row[3] or "").strip()
        perms_raw = str(row[4] or "").strip()
        if not username or not password:
            skipped.append(f"第{i}行：用户名或密码为空"); continue
        if "说明" in username: continue
        roles = [ROLE_ALIAS[x] for x in roles_raw.replace("，", ",").split(",") if x.strip() in ROLE_ALIAS]
        if not roles: roles = ["viewer"]
        scope = str(row[5] or "").strip() if len(row) > 5 else ""
        if scope not in PERM_SCOPES: scope = ""
        if perms_raw in ("全部", "all", "ALL", ""):
            perms = ",".join(PERM_SCOPES)
        else:
            perms = ",".join([x for x in perms_raw.replace("，", ",").split(",") if x.strip() in PERM_SCOPES])
        try:
            conn.execute("INSERT INTO users(username,password_hash,name,roles,perms,approve_scope,created_at) VALUES(?,?,?,?,?,?,?)",
                         (username, hash_pw(password), name or username, ",".join(roles), perms, scope, now()))
            created.append(username)
        except sqlite3.IntegrityError:
            skipped.append(f"第{i}行：用户名 {username} 已存在")
    conn.commit(); conn.close()
    return {"created": created, "skipped": skipped}

@app.delete("/api/admin/users/{uid}")
def admin_delete_user(uid: int, u=Depends(require_admin)):
    if uid == u["id"]: raise HTTPException(400, "不能删除自己")
    conn = db()
    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit(); conn.close()
    return {"ok": True}

# ---- 标签体系管理 ----
@app.get("/api/admin/taxonomy")
def admin_get_taxonomy(u=Depends(require_admin)):
    return get_taxonomy()

@app.put("/api/admin/taxonomy")
def admin_put_taxonomy(body: dict, u=Depends(require_admin)):
    for k in ("depts", "materials"):
        if not isinstance(body.get(k), list) or not body[k]:
            raise HTTPException(400, f"{k} 必须是非空列表")
    for k in ("topics", "channels"):
        if not isinstance(body.get(k), dict):
            raise HTTPException(400, f"{k} 格式错误")
    conn = db()
    set_setting(conn, "taxonomy", json.dumps(body, ensure_ascii=False))
    conn.commit(); conn.close()
    return {"ok": True}

@app.get("/api/admin/settings")
def admin_get_settings(u=Depends(require_admin)):
    conn = db()
    out = {"ai_external_enabled": get_setting(conn, "ai_external_enabled", "0") == "1",
           "ai_key_configured": bool(AI_API_KEY)}
    conn.close(); return out

@app.put("/api/admin/settings")
def admin_put_settings(body: dict, u=Depends(require_admin)):
    conn = db()
    if "ai_external_enabled" in body:
        set_setting(conn, "ai_external_enabled", "1" if body["ai_external_enabled"] else "0")
    conn.commit(); conn.close()
    return {"ok": True}

# ---- 数据看板 ----
@app.get("/api/admin/stats")
def admin_stats(u=Depends(require_admin)):
    conn = db()
    total = conn.execute("SELECT COUNT(*) c FROM clues").fetchone()["c"]
    users_n = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    today = datetime.now().strftime("%Y-%m-%d")
    today_n = conn.execute("SELECT COUNT(*) c FROM clues WHERE created_at>=?", (today,)).fetchone()["c"]
    week_n = conn.execute("SELECT COUNT(*) c FROM clues WHERE created_at>=date('now','localtime','-7 day')").fetchone()["c"]
    by_dept = {}
    for r in conn.execute("SELECT dept FROM clues"):
        for d in (r["dept"] or "未分类").split(","):
            by_dept[d] = by_dept.get(d, 0) + 1
    by_topic = {r["category"] or "未分类": r["c"] for r in
                conn.execute("SELECT category, COUNT(*) c FROM clues GROUP BY category")}
    by_status = {r["status"]: r["c"] for r in
                 conn.execute("SELECT status, COUNT(*) c FROM clues GROUP BY status")}
    by_material = {r["material"]: r["c"] for r in
                   conn.execute("SELECT material, COUNT(*) c FROM clues WHERE material!='' GROUP BY material")}
    top_submitters = [dict(r) for r in conn.execute("""
        SELECT u.name, COUNT(*) c FROM clues c JOIN users u ON u.id=c.submitter_id
        GROUP BY c.submitter_id ORDER BY c DESC LIMIT 5""")]
    trend = [dict(r) for r in conn.execute("""
        SELECT substr(created_at,1,10) d, COUNT(*) c FROM clues
        WHERE created_at>=date('now','localtime','-13 day')
        GROUP BY substr(created_at,1,10) ORDER BY d""")]
    hot = [dict(r) for r in conn.execute(
        "SELECT id,title,likes,views FROM clues ORDER BY likes*3+views DESC LIMIT 5")]
    conn.close()
    return {"total": total, "users": users_n, "today": today_n, "week": week_n,
            "by_dept": by_dept, "by_topic": by_topic, "by_status": by_status,
            "by_material": by_material, "top_submitters": top_submitters,
            "trend": trend, "hot": hot}

@app.get("/api/admin/export")
def admin_export(u=Depends(require_admin)):
    import openpyxl
    conn = db()
    rows = conn.execute("""SELECT c.*, u.name AS submitter_name FROM clues c
                           JOIN users u ON u.id=c.submitter_id ORDER BY c.created_at DESC""").fetchall()
    conn.close()
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "线索池"
    headers = ["ID", "标题", "内容", "来源身份", "场景/地点", "获取时间", "条线", "物料类别",
               "信息主题", "获取方式", "关键词", "可信度", "状态", "审批状态", "审批人", "审批时间", "审批意见",
               "提交人", "浏览数", "点赞数", "提交时间", "更新时间"]
    ws.append(headers)
    for r in rows:
        ws.append([r["id"], r["title"], r["content"], r["source"], r["scene"], r["acquired_at"],
                   r["dept"], r["material"], r["category"], r["channel"], r["keywords"], r["credibility"],
                   r["status"], r["approval"], r["approved_by"], r["approved_at"], r["approval_comment"],
                   r["submitter_name"], r["views"], r["likes"], r["created_at"], r["updated_at"]])
    from openpyxl.utils import get_column_letter
    for i, h in enumerate(headers, 1): ws.column_dimensions[get_column_letter(i)].width = 14
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": "attachment; filename=clue-pool-export.xlsx"})

# ---------------- 健康检查 & 云端保活 ----------------
@app.get("/api/health")
def health():
    return {"ok": True, "time": now()}

def start_keepalive():
    """云端部署时防休眠：每10分钟自访问一次（Render 自动注入 RENDER_EXTERNAL_URL）。本地运行不启用。"""
    url = os.environ.get("SELF_PING_URL") or os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        return
    import threading
    def loop():
        while True:
            time.sleep(600)
            try:
                urllib.request.urlopen(url.rstrip("/") + "/api/health", timeout=15)
            except Exception:
                pass
    threading.Thread(target=loop, daemon=True).start()

# 生产模式：托管前端构建产物（必须放在所有 API 路由之后，避免拦截 /api/*）
dist = os.path.join(BASE_DIR, "dist")
if os.path.isdir(dist):
    app.mount("/", StaticFiles(directory=dist, html=True), name="static")

init_db()
start_keepalive()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

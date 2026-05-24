from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import os
import json

DB_DIR = os.environ.get("DB_DIR", "/data")
if not os.path.isdir(DB_DIR):
    DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "edu.db")

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# --- Models ---

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # teacher / student
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, nullable=True)


class Classroom(Base):
    __tablename__ = "classrooms"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, nullable=False)
    teacher_id = Column(String, ForeignKey("users.id"), nullable=False)
    voice_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ClassroomMember(Base):
    __tablename__ = "classroom_members"
    id = Column(String, primary_key=True)
    classroom_id = Column(String, ForeignKey("classrooms.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role = Column(String, default="student")  # teacher / student
    joined_at = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True)
    classroom_id = Column(String, ForeignKey("classrooms.id"), nullable=False)
    sender_id = Column(String, ForeignKey("users.id"), nullable=False)
    sender_name = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PrivateMessage(Base):
    __tablename__ = "private_messages"
    id = Column(String, primary_key=True)
    sender_id = Column(String, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(String, ForeignKey("users.id"), nullable=False)
    sender_name = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class FileRecord(Base):
    __tablename__ = "files"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    size = Column(String, nullable=True)
    uploaded_by = Column(String, ForeignKey("users.id"), nullable=False)
    uploaded_by_name = Column(String, nullable=True)
    classroom_id = Column(String, nullable=True)
    data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FlaggedMessage(Base):
    __tablename__ = "flagged_messages"
    id = Column(String, primary_key=True)
    message_id = Column(String, nullable=False)
    message_type = Column(String, nullable=False)  # "group" or "private"
    sender_id = Column(String, nullable=False)
    sender_name = Column(String, nullable=False)
    receiver_id = Column(String, nullable=True)
    receiver_name = Column(String, nullable=True)
    classroom_id = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    matched_words = Column(String, nullable=False)
    reviewed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Homework(Base):
    __tablename__ = "homework"
    id = Column(String, primary_key=True)
    classroom_id = Column(String, ForeignKey("classrooms.id"), nullable=False)
    teacher_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class HomeworkSubmission(Base):
    __tablename__ = "homework_submissions"
    id = Column(String, primary_key=True)
    homework_id = Column(String, ForeignKey("homework.id"), nullable=False)
    student_id = Column(String, ForeignKey("users.id"), nullable=False)
    student_name = Column(String, nullable=False)
    answer = Column(Text, nullable=False)
    grade = Column(String, nullable=True)
    feedback = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)


class Quiz(Base):
    __tablename__ = "quizzes"
    id = Column(String, primary_key=True)
    classroom_id = Column(String, ForeignKey("classrooms.id"), nullable=False)
    teacher_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    questions = Column(Text, nullable=False)  # JSON array
    created_at = Column(DateTime, default=datetime.utcnow)


class QuizSubmission(Base):
    __tablename__ = "quiz_submissions"
    id = Column(String, primary_key=True)
    quiz_id = Column(String, ForeignKey("quizzes.id"), nullable=False)
    student_id = Column(String, ForeignKey("users.id"), nullable=False)
    student_name = Column(String, nullable=False)
    answers = Column(Text, nullable=False)  # JSON array
    score = Column(String, nullable=True)
    total = Column(String, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)


class Grade(Base):
    __tablename__ = "grades"
    id = Column(String, primary_key=True)
    classroom_id = Column(String, ForeignKey("classrooms.id"), nullable=False)
    student_id = Column(String, ForeignKey("users.id"), nullable=False)
    student_name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    grade = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    teacher_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Timetable(Base):
    __tablename__ = "timetables"
    id = Column(String, primary_key=True)
    classroom_id = Column(String, ForeignKey("classrooms.id"), nullable=False, unique=True)
    schedule = Column(Text, nullable=False)  # JSON: { "الأحد": [...], "الاثنين": [...], ... }
    updated_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(engine)


# --- Threat Detection ---

THREAT_KEYWORDS = [
    # Direct threats
    "اقتلك", "أقتلك", "بقتلك", "هقتلك", "راح اقتلك", "بدي اقتلك",
    "اذبحك", "أذبحك", "بذبحك", "هذبحك",
    "اضربك", "أضربك", "بضربك", "هضربك", "راح اضربك",
    "اكسرك", "أكسرك", "بكسرك",
    "ادمرك", "أدمرك", "بدمرك",
    "اطعنك", "أطعنك",
    # Threats with objects
    "سكين", "مسدس", "سلاح", "بندقية", "رصاصة",
    # Death threats
    "موتك", "تموت", "انتحر", "انتحار", "اموت",
    "مقبرة", "قبرك", "جنازتك",
    # Severe insults / bullying
    "حقير", "حقيرة", "نجس", "نجسة", "قذر", "قذرة",
    "كلب", "حمار", "حيوان", "خنزير",
    "غبي", "غبية", "احمق", "حمقاء", "معاق", "متخلف",
    "ابن الكلب", "ابن الحرام", "ابن ال",
    "عاهرة", "شرموطة", "قحبة",
    "لعنة", "الله يلعنك", "يلعن",
    # Harassment
    "تحرش", "اتحرش", "اغتصب", "اغتصاب",
    # Intimidation
    "خايف", "خوفك", "ارعبك", "ارهبك",
    "ستندم", "بتندم", "راح تندم", "هتندم",
    "بعرف وين بيتك", "اعرف بيتك", "بيتك",
    "انتظرني", "انتظرك", "استناني", "استناك",
    "بعد المدرسة", "بره المدرسة", "عند البوابة",
    # English threats that students might use
    "kill", "die", "dead", "threat", "hurt",
    "stupid", "idiot", "hate you",
]

def detect_threats(text: str) -> list:
    text_lower = text.strip()
    matched = []
    for keyword in THREAT_KEYWORDS:
        if keyword in text_lower:
            matched.append(keyword)
    return matched


# --- Seed admin account ---
def seed_admin():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == "admin").first()
        if not existing:
            admin = User(
                id=str(int(datetime.utcnow().timestamp() * 1000)),
                name="المعلم المسؤول",
                username="admin",
                password="admin123",
                role="teacher",
                is_admin=True,
                created_at=datetime.utcnow(),
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()

seed_admin()


# --- Schemas ---

class RegisterRequest(BaseModel):
    name: str
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateStudentRequest(BaseModel):
    name: str
    username: str
    password: str
    teacher_id: str


class CreateTeacherRequest(BaseModel):
    name: str
    username: str
    password: str
    created_by: str


class UpdatePasswordRequest(BaseModel):
    new_password: str


class CreateClassroomRequest(BaseModel):
    name: str
    teacher_id: str


class JoinClassroomRequest(BaseModel):
    code: str
    user_id: str


class RenameClassroomRequest(BaseModel):
    name: str


class SendMessageRequest(BaseModel):
    sender_id: str
    sender_name: str
    text: str


class SendPrivateMessageRequest(BaseModel):
    sender_id: str
    receiver_id: str
    sender_name: str
    text: str


class AddStudentToClassroomRequest(BaseModel):
    user_id: str


class AddFileRequest(BaseModel):
    name: str
    type: str
    size: Optional[str] = None
    uploaded_by: str
    uploaded_by_name: Optional[str] = None
    classroom_id: Optional[str] = None
    data: Optional[str] = None


class CreateHomeworkRequest(BaseModel):
    classroom_id: str
    teacher_id: str
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None


class SubmitHomeworkRequest(BaseModel):
    student_id: str
    student_name: str
    answer: str


class GradeHomeworkRequest(BaseModel):
    grade: str
    feedback: Optional[str] = None


class CreateQuizRequest(BaseModel):
    classroom_id: str
    teacher_id: str
    title: str
    questions: str  # JSON string


class SubmitQuizRequest(BaseModel):
    student_id: str
    student_name: str
    answers: str  # JSON string


class CreateGradeRequest(BaseModel):
    classroom_id: str
    student_id: str
    student_name: str
    subject: str
    grade: str
    notes: Optional[str] = None
    teacher_id: str


# --- Deps ---

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- App ---

app = FastAPI(title="Edu Messenger API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Auth ---

@app.post("/api/auth/register")
def register_teacher(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(400, "اسم المستخدم مسجل بالفعل")
    user = User(
        id=str(int(datetime.utcnow().timestamp() * 1000)),
        name=req.name,
        username=req.username,
        password=req.password,
        role="teacher",
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_dict(user)


@app.post("/api/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        raise HTTPException(401, "اسم المستخدم غير موجود")
    if user.password != req.password:
        raise HTTPException(401, "كلمة المرور غير صحيحة")
    return _user_dict(user)


# --- Students ---

@app.post("/api/students")
def create_student(req: CreateStudentRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(400, "اسم المستخدم مسجل بالفعل")
    student = User(
        id=str(int(datetime.utcnow().timestamp() * 1000)),
        name=req.name,
        username=req.username,
        password=req.password,
        role="student",
        is_admin=False,
        created_by=req.teacher_id,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return _user_dict(student)


@app.get("/api/students")
def get_students(teacher_id: str = None, db: Session = Depends(get_db)):
    query = db.query(User).filter(User.role == "student")
    if teacher_id:
        query = query.filter(User.created_by == teacher_id)
    students = query.all()
    return [_user_dict(s) for s in students]


@app.put("/api/students/{student_id}/password")
def update_student_password(student_id: str, req: UpdatePasswordRequest, db: Session = Depends(get_db)):
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(404, "الطالب غير موجود")
    student.password = req.new_password
    db.commit()
    return {"success": True}


@app.delete("/api/students/{student_id}")
def delete_student(student_id: str, db: Session = Depends(get_db)):
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(404, "الطالب غير موجود")
    db.delete(student)
    db.commit()
    return {"success": True}


# --- Teachers ---

@app.post("/api/teachers")
def create_teacher(req: CreateTeacherRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(400, "اسم المستخدم مستخدم بالفعل")
    teacher = User(
        id=str(int(datetime.utcnow().timestamp() * 1000)),
        name=req.name,
        username=req.username,
        password=req.password,
        role="teacher",
        is_admin=False,
        created_by=req.created_by,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return _user_dict(teacher)


@app.get("/api/teachers")
def get_teachers(db: Session = Depends(get_db)):
    teachers = db.query(User).filter(User.role == "teacher").all()
    return [_user_dict(t) for t in teachers]


@app.put("/api/teachers/{teacher_id}/password")
def update_teacher_password(teacher_id: str, req: UpdatePasswordRequest, db: Session = Depends(get_db)):
    teacher = db.query(User).filter(User.id == teacher_id, User.role == "teacher").first()
    if not teacher:
        raise HTTPException(404, "المعلم غير موجود")
    teacher.password = req.new_password
    db.commit()
    return {"success": True}


@app.delete("/api/teachers/{teacher_id}")
def delete_teacher(teacher_id: str, db: Session = Depends(get_db)):
    teacher = db.query(User).filter(User.id == teacher_id, User.role == "teacher").first()
    if not teacher:
        raise HTTPException(404, "المعلم غير موجود")
    if teacher.is_admin:
        raise HTTPException(400, "لا يمكن حذف حساب المسؤول")
    db.delete(teacher)
    db.commit()
    return {"success": True}


# --- Classrooms ---

@app.post("/api/classrooms")
def create_classroom(req: CreateClassroomRequest, db: Session = Depends(get_db)):
    import random
    code = str(random.randint(100000, 999999))
    while db.query(Classroom).filter(Classroom.code == code).first():
        code = str(random.randint(100000, 999999))
    classroom = Classroom(
        id=str(int(datetime.utcnow().timestamp() * 1000)),
        name=req.name,
        code=code,
        teacher_id=req.teacher_id,
    )
    db.add(classroom)
    member = ClassroomMember(
        id=f"{classroom.id}_{req.teacher_id}",
        classroom_id=classroom.id,
        user_id=req.teacher_id,
        role="teacher",
    )
    db.add(member)
    db.commit()
    db.refresh(classroom)
    return _classroom_dict(classroom, db)


@app.get("/api/classrooms")
def get_classrooms(user_id: str, db: Session = Depends(get_db)):
    requesting_user = db.query(User).filter(User.id == user_id).first()
    if requesting_user and requesting_user.is_admin:
        classrooms = db.query(Classroom).all()
        for c in classrooms:
            existing = db.query(ClassroomMember).filter(
                ClassroomMember.classroom_id == c.id,
                ClassroomMember.user_id == user_id,
            ).first()
            if not existing:
                member = ClassroomMember(
                    id=f"{c.id}_{user_id}",
                    classroom_id=c.id,
                    user_id=user_id,
                    role="teacher",
                )
                db.add(member)
        db.commit()
    else:
        member_ids = [m.classroom_id for m in db.query(ClassroomMember).filter(ClassroomMember.user_id == user_id).all()]
        classrooms = db.query(Classroom).filter(Classroom.id.in_(member_ids)).all() if member_ids else []
    return [_classroom_dict(c, db) for c in classrooms]


@app.post("/api/classrooms/join")
def join_classroom(req: JoinClassroomRequest, db: Session = Depends(get_db)):
    classroom = db.query(Classroom).filter(Classroom.code == req.code).first()
    if not classroom:
        raise HTTPException(404, "كود الفصل غير صحيح")
    existing = db.query(ClassroomMember).filter(
        ClassroomMember.classroom_id == classroom.id,
        ClassroomMember.user_id == req.user_id,
    ).first()
    if not existing:
        user = db.query(User).filter(User.id == req.user_id).first()
        member = ClassroomMember(
            id=f"{classroom.id}_{req.user_id}",
            classroom_id=classroom.id,
            user_id=req.user_id,
            role=user.role if user else "student",
        )
        db.add(member)
        db.commit()
    return _classroom_dict(classroom, db)


@app.post("/api/classrooms/{classroom_id}/students")
def add_student_to_classroom(classroom_id: str, req: AddStudentToClassroomRequest, db: Session = Depends(get_db)):
    existing = db.query(ClassroomMember).filter(
        ClassroomMember.classroom_id == classroom_id,
        ClassroomMember.user_id == req.user_id,
    ).first()
    if not existing:
        member = ClassroomMember(
            id=f"{classroom_id}_{req.user_id}",
            classroom_id=classroom_id,
            user_id=req.user_id,
            role="student",
        )
        db.add(member)
        db.commit()
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    return _classroom_dict(classroom, db)


@app.delete("/api/classrooms/{classroom_id}/students/{student_id}")
def remove_student_from_classroom(classroom_id: str, student_id: str, db: Session = Depends(get_db)):
    member = db.query(ClassroomMember).filter(
        ClassroomMember.classroom_id == classroom_id,
        ClassroomMember.user_id == student_id,
    ).first()
    if member:
        db.delete(member)
        db.commit()
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    return _classroom_dict(classroom, db)


@app.put("/api/classrooms/{classroom_id}/rename")
def rename_classroom(classroom_id: str, req: RenameClassroomRequest, db: Session = Depends(get_db)):
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not classroom:
        raise HTTPException(404, "الفصل غير موجود")
    classroom.name = req.name
    db.commit()
    db.refresh(classroom)
    return _classroom_dict(classroom, db)


@app.put("/api/classrooms/{classroom_id}/voice")
def toggle_voice(classroom_id: str, db: Session = Depends(get_db)):
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not classroom:
        raise HTTPException(404, "الفصل غير موجود")
    classroom.voice_enabled = not (classroom.voice_enabled if classroom.voice_enabled is not None else True)
    db.commit()
    db.refresh(classroom)
    return _classroom_dict(classroom, db)


@app.delete("/api/classrooms/{classroom_id}")
def delete_classroom(classroom_id: str, db: Session = Depends(get_db)):
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not classroom:
        raise HTTPException(404, "الفصل غير موجود")
    db.query(Message).filter(Message.classroom_id == classroom_id).delete()
    db.query(ClassroomMember).filter(ClassroomMember.classroom_id == classroom_id).delete()
    db.delete(classroom)
    db.commit()
    return {"success": True}


# --- Contacts (classmates) ---

@app.get("/api/contacts")
def get_contacts(user_id: str, db: Session = Depends(get_db)):
    my_classrooms = [m.classroom_id for m in db.query(ClassroomMember).filter(ClassroomMember.user_id == user_id).all()]
    if not my_classrooms:
        return []
    classmate_ids = set()
    for cid in my_classrooms:
        members = db.query(ClassroomMember).filter(ClassroomMember.classroom_id == cid).all()
        for m in members:
            if m.user_id != user_id:
                classmate_ids.add(m.user_id)
    contacts = db.query(User).filter(User.id.in_(list(classmate_ids))).all() if classmate_ids else []
    return [{"id": u.id, "name": u.name, "username": u.username, "role": u.role} for u in contacts]


# --- Messages ---

@app.get("/api/classrooms/{classroom_id}/messages")
def get_messages(classroom_id: str, db: Session = Depends(get_db)):
    msgs = db.query(Message).filter(Message.classroom_id == classroom_id).order_by(Message.created_at).all()
    return [_msg_dict(m) for m in msgs]


@app.post("/api/classrooms/{classroom_id}/messages")
def send_message(classroom_id: str, req: SendMessageRequest, db: Session = Depends(get_db)):
    msg = Message(
        id=str(int(datetime.utcnow().timestamp() * 1000)),
        classroom_id=classroom_id,
        sender_id=req.sender_id,
        sender_name=req.sender_name,
        text=req.text,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    threats = detect_threats(req.text)
    if threats:
        flag = FlaggedMessage(
            id=f"flag_{msg.id}",
            message_id=msg.id,
            message_type="group",
            sender_id=req.sender_id,
            sender_name=req.sender_name,
            classroom_id=classroom_id,
            text=req.text,
            matched_words=",".join(threats),
        )
        db.add(flag)
        db.commit()
    result = _msg_dict(msg)
    result["flagged"] = len(threats) > 0
    return result


# --- Private Messages ---

@app.get("/api/private-messages")
def get_private_messages(user1: str, user2: str, db: Session = Depends(get_db)):
    msgs = db.query(PrivateMessage).filter(
        ((PrivateMessage.sender_id == user1) & (PrivateMessage.receiver_id == user2)) |
        ((PrivateMessage.sender_id == user2) & (PrivateMessage.receiver_id == user1))
    ).order_by(PrivateMessage.created_at).all()
    return [_pm_dict(m) for m in msgs]


@app.post("/api/private-messages")
def send_private_message(req: SendPrivateMessageRequest, db: Session = Depends(get_db)):
    msg = PrivateMessage(
        id=str(int(datetime.utcnow().timestamp() * 1000)),
        sender_id=req.sender_id,
        receiver_id=req.receiver_id,
        sender_name=req.sender_name,
        text=req.text,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    threats = detect_threats(req.text)
    if threats:
        receiver = db.query(User).filter(User.id == req.receiver_id).first()
        flag = FlaggedMessage(
            id=f"flag_{msg.id}",
            message_id=msg.id,
            message_type="private",
            sender_id=req.sender_id,
            sender_name=req.sender_name,
            receiver_id=req.receiver_id,
            receiver_name=receiver.name if receiver else None,
            text=req.text,
            matched_words=",".join(threats),
        )
        db.add(flag)
        db.commit()
    result = _pm_dict(msg)
    result["flagged"] = len(threats) > 0
    return result


# --- Flagged Messages ---

@app.get("/api/flagged-messages")
def get_flagged_messages(db: Session = Depends(get_db)):
    flags = db.query(FlaggedMessage).order_by(FlaggedMessage.created_at.desc()).all()
    return [{
        "id": f.id,
        "messageId": f.message_id,
        "messageType": f.message_type,
        "senderId": f.sender_id,
        "senderName": f.sender_name,
        "receiverId": f.receiver_id,
        "receiverName": f.receiver_name,
        "classroomId": f.classroom_id,
        "text": f.text,
        "matchedWords": f.matched_words.split(",") if f.matched_words else [],
        "reviewed": f.reviewed,
        "createdAt": f.created_at.isoformat() if f.created_at else None,
    } for f in flags]


@app.put("/api/flagged-messages/{flag_id}/review")
def review_flagged_message(flag_id: str, db: Session = Depends(get_db)):
    flag = db.query(FlaggedMessage).filter(FlaggedMessage.id == flag_id).first()
    if not flag:
        raise HTTPException(404, "not found")
    flag.reviewed = True
    db.commit()
    return {"success": True}


@app.delete("/api/flagged-messages/{flag_id}")
def delete_flagged_message(flag_id: str, db: Session = Depends(get_db)):
    flag = db.query(FlaggedMessage).filter(FlaggedMessage.id == flag_id).first()
    if flag:
        db.delete(flag)
        db.commit()
    return {"success": True}


# --- Files ---

@app.get("/api/files")
def get_files(db: Session = Depends(get_db)):
    files = db.query(FileRecord).order_by(FileRecord.created_at.desc()).all()
    return [_file_dict(f) for f in files]


@app.post("/api/files")
def add_file(req: AddFileRequest, db: Session = Depends(get_db)):
    f = FileRecord(
        id=str(int(datetime.utcnow().timestamp() * 1000)),
        name=req.name,
        type=req.type,
        size=req.size,
        uploaded_by=req.uploaded_by,
        uploaded_by_name=req.uploaded_by_name,
        classroom_id=req.classroom_id,
        data=req.data,
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return _file_dict(f)


@app.delete("/api/files/{file_id}")
def delete_file(file_id: str, db: Session = Depends(get_db)):
    f = db.query(FileRecord).filter(FileRecord.id == file_id).first()
    if f:
        db.delete(f)
        db.commit()
    return {"success": True}


# --- Users lookup ---

@app.get("/api/users")
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [_user_dict(u) for u in users]


@app.get("/api/users/{user_id}")
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "المستخدم غير موجود")
    return _user_dict(user)


# --- Homework ---

@app.post("/api/homework")
def create_homework(req: CreateHomeworkRequest, db: Session = Depends(get_db)):
    hw = Homework(
        id=str(int(datetime.utcnow().timestamp() * 1000)),
        classroom_id=req.classroom_id,
        teacher_id=req.teacher_id,
        title=req.title,
        description=req.description,
        due_date=req.due_date,
    )
    db.add(hw)
    db.commit()
    db.refresh(hw)
    subs = db.query(HomeworkSubmission).filter(HomeworkSubmission.homework_id == hw.id).all()
    return _homework_dict(hw, subs)


@app.get("/api/homework")
def get_homework(classroom_id: str, db: Session = Depends(get_db)):
    hws = db.query(Homework).filter(Homework.classroom_id == classroom_id).order_by(Homework.created_at.desc()).all()
    result = []
    for hw in hws:
        subs = db.query(HomeworkSubmission).filter(HomeworkSubmission.homework_id == hw.id).all()
        result.append(_homework_dict(hw, subs))
    return result


@app.post("/api/homework/{homework_id}/submit")
def submit_homework(homework_id: str, req: SubmitHomeworkRequest, db: Session = Depends(get_db)):
    existing = db.query(HomeworkSubmission).filter(
        HomeworkSubmission.homework_id == homework_id,
        HomeworkSubmission.student_id == req.student_id,
    ).first()
    if existing:
        existing.answer = req.answer
        existing.submitted_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
    else:
        sub = HomeworkSubmission(
            id=str(int(datetime.utcnow().timestamp() * 1000)),
            homework_id=homework_id,
            student_id=req.student_id,
            student_name=req.student_name,
            answer=req.answer,
        )
        db.add(sub)
        db.commit()
    hw = db.query(Homework).filter(Homework.id == homework_id).first()
    subs = db.query(HomeworkSubmission).filter(HomeworkSubmission.homework_id == homework_id).all()
    return _homework_dict(hw, subs)


@app.put("/api/homework/submissions/{submission_id}/grade")
def grade_homework(submission_id: str, req: GradeHomeworkRequest, db: Session = Depends(get_db)):
    sub = db.query(HomeworkSubmission).filter(HomeworkSubmission.id == submission_id).first()
    if not sub:
        raise HTTPException(404, "لم يتم العثور على الإجابة")
    sub.grade = req.grade
    sub.feedback = req.feedback
    db.commit()
    return {"success": True}


@app.delete("/api/homework/{homework_id}")
def delete_homework(homework_id: str, db: Session = Depends(get_db)):
    db.query(HomeworkSubmission).filter(HomeworkSubmission.homework_id == homework_id).delete()
    db.query(Homework).filter(Homework.id == homework_id).delete()
    db.commit()
    return {"success": True}


# --- Quizzes ---

@app.post("/api/quizzes")
def create_quiz(req: CreateQuizRequest, db: Session = Depends(get_db)):
    quiz = Quiz(
        id=str(int(datetime.utcnow().timestamp() * 1000)),
        classroom_id=req.classroom_id,
        teacher_id=req.teacher_id,
        title=req.title,
        questions=req.questions,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return _quiz_dict(quiz, [])


@app.get("/api/quizzes")
def get_quizzes(classroom_id: str, db: Session = Depends(get_db)):
    quizzes = db.query(Quiz).filter(Quiz.classroom_id == classroom_id).order_by(Quiz.created_at.desc()).all()
    result = []
    for q in quizzes:
        subs = db.query(QuizSubmission).filter(QuizSubmission.quiz_id == q.id).all()
        result.append(_quiz_dict(q, subs))
    return result


@app.post("/api/quizzes/{quiz_id}/submit")
def submit_quiz(quiz_id: str, req: SubmitQuizRequest, db: Session = Depends(get_db)):
    existing = db.query(QuizSubmission).filter(
        QuizSubmission.quiz_id == quiz_id,
        QuizSubmission.student_id == req.student_id,
    ).first()
    if existing:
        raise HTTPException(400, "لقد أجبت على هذا الاختبار بالفعل")
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(404, "الاختبار غير موجود")
    questions = json.loads(quiz.questions)
    answers = json.loads(req.answers)
    score = 0
    total = len(questions)
    for i, q in enumerate(questions):
        if i < len(answers) and answers[i] == q.get("correct"):
            score += 1
    sub = QuizSubmission(
        id=str(int(datetime.utcnow().timestamp() * 1000)),
        quiz_id=quiz_id,
        student_id=req.student_id,
        student_name=req.student_name,
        answers=req.answers,
        score=str(score),
        total=str(total),
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return {"score": score, "total": total, "submission": _quiz_submission_dict(sub)}


@app.delete("/api/quizzes/{quiz_id}")
def delete_quiz(quiz_id: str, db: Session = Depends(get_db)):
    db.query(QuizSubmission).filter(QuizSubmission.quiz_id == quiz_id).delete()
    db.query(Quiz).filter(Quiz.id == quiz_id).delete()
    db.commit()
    return {"success": True}


# --- Grades ---

@app.post("/api/grades")
def create_grade(req: CreateGradeRequest, db: Session = Depends(get_db)):
    g = Grade(
        id=str(int(datetime.utcnow().timestamp() * 1000)),
        classroom_id=req.classroom_id,
        student_id=req.student_id,
        student_name=req.student_name,
        subject=req.subject,
        grade=req.grade,
        notes=req.notes,
        teacher_id=req.teacher_id,
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    return _grade_dict(g)


@app.get("/api/grades")
def get_grades(classroom_id: str = None, student_id: str = None, db: Session = Depends(get_db)):
    q = db.query(Grade)
    if classroom_id:
        q = q.filter(Grade.classroom_id == classroom_id)
    if student_id:
        q = q.filter(Grade.student_id == student_id)
    return [_grade_dict(g) for g in q.order_by(Grade.created_at.desc()).all()]


@app.delete("/api/grades/{grade_id}")
def delete_grade(grade_id: str, db: Session = Depends(get_db)):
    db.query(Grade).filter(Grade.id == grade_id).delete()
    db.commit()
    return {"success": True}


# --- Timetable ---

class TimetableRequest(BaseModel):
    classroom_id: str
    schedule: str  # JSON string

@app.get("/api/timetable")
def get_timetable(classroom_id: str, db: Session = Depends(get_db)):
    tt = db.query(Timetable).filter(Timetable.classroom_id == classroom_id).first()
    if not tt:
        return {"id": None, "classroomId": classroom_id, "schedule": None}
    return {"id": tt.id, "classroomId": tt.classroom_id, "schedule": json.loads(tt.schedule)}

@app.post("/api/timetable")
def save_timetable(req: TimetableRequest, db: Session = Depends(get_db)):
    tt = db.query(Timetable).filter(Timetable.classroom_id == req.classroom_id).first()
    if tt:
        tt.schedule = req.schedule
        tt.updated_at = datetime.utcnow()
    else:
        tt = Timetable(
            id=str(int(datetime.utcnow().timestamp() * 1000)),
            classroom_id=req.classroom_id,
            schedule=req.schedule,
            updated_at=datetime.utcnow(),
        )
        db.add(tt)
    db.commit()
    return {"success": True}


# --- Voice Call Signaling ---

call_signals = {}  # in-memory store for call signaling

class CallSignalRequest(BaseModel):
    from_id: str
    from_name: str
    to_id: str
    signal_type: str  # "offer", "answer", "ice", "end"
    data: Optional[str] = None

@app.post("/api/calls/signal")
def send_signal(req: CallSignalRequest):
    key = req.to_id
    if key not in call_signals:
        call_signals[key] = []
    call_signals[key].append({
        "fromId": req.from_id,
        "fromName": req.from_name,
        "toId": req.to_id,
        "signalType": req.signal_type,
        "data": req.data,
        "timestamp": datetime.utcnow().isoformat(),
    })
    return {"success": True}

@app.get("/api/calls/signal")
def get_signals(user_id: str):
    key = user_id
    signals = call_signals.pop(key, [])
    return signals

@app.post("/api/calls/end")
def end_call(req: CallSignalRequest):
    call_signals.pop(req.from_id, None)
    call_signals.pop(req.to_id, None)
    return {"success": True}


# --- Health ---

@app.get("/api/health")
def health():
    return {"status": "ok"}


# --- Helpers ---

def _homework_dict(hw: Homework, subs):
    return {
        "id": hw.id,
        "classroomId": hw.classroom_id,
        "teacherId": hw.teacher_id,
        "title": hw.title,
        "description": hw.description,
        "dueDate": hw.due_date,
        "createdAt": hw.created_at.isoformat() if hw.created_at else None,
        "submissions": [_hw_submission_dict(s) for s in subs],
    }

def _hw_submission_dict(s: HomeworkSubmission):
    return {
        "id": s.id,
        "homeworkId": s.homework_id,
        "studentId": s.student_id,
        "studentName": s.student_name,
        "answer": s.answer,
        "grade": s.grade,
        "feedback": s.feedback,
        "submittedAt": s.submitted_at.isoformat() if s.submitted_at else None,
    }

def _quiz_dict(q: Quiz, subs):
    return {
        "id": q.id,
        "classroomId": q.classroom_id,
        "teacherId": q.teacher_id,
        "title": q.title,
        "questions": json.loads(q.questions),
        "createdAt": q.created_at.isoformat() if q.created_at else None,
        "submissions": [_quiz_submission_dict(s) for s in subs],
    }

def _quiz_submission_dict(s: QuizSubmission):
    return {
        "id": s.id,
        "quizId": s.quiz_id,
        "studentId": s.student_id,
        "studentName": s.student_name,
        "answers": json.loads(s.answers),
        "score": s.score,
        "total": s.total,
        "submittedAt": s.submitted_at.isoformat() if s.submitted_at else None,
    }

def _grade_dict(g: Grade):
    return {
        "id": g.id,
        "classroomId": g.classroom_id,
        "studentId": g.student_id,
        "studentName": g.student_name,
        "subject": g.subject,
        "grade": g.grade,
        "notes": g.notes,
        "teacherId": g.teacher_id,
        "createdAt": g.created_at.isoformat() if g.created_at else None,
    }


def _user_dict(u: User):
    return {
        "id": u.id,
        "name": u.name,
        "username": u.username,
        "password": u.password,
        "role": u.role,
        "isAdmin": u.is_admin,
        "createdAt": u.created_at.isoformat() if u.created_at else None,
        "createdBy": u.created_by,
    }


def _classroom_dict(c: Classroom, db: Session):
    members = db.query(ClassroomMember).filter(ClassroomMember.classroom_id == c.id).all()
    students = []
    teacher = None
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        if user:
            ud = _user_dict(user)
            if m.role == "teacher":
                teacher = ud
            else:
                students.append(ud)
    return {
        "id": c.id,
        "name": c.name,
        "code": c.code,
        "teacherId": c.teacher_id,
        "teacher": teacher,
        "students": students,
        "voiceEnabled": c.voice_enabled if c.voice_enabled is not None else True,
        "createdAt": c.created_at.isoformat() if c.created_at else None,
    }


def _msg_dict(m: Message):
    return {
        "id": m.id,
        "classroomId": m.classroom_id,
        "senderId": m.sender_id,
        "senderName": m.sender_name,
        "text": m.text,
        "timestamp": m.created_at.isoformat() if m.created_at else None,
    }


def _pm_dict(m: PrivateMessage):
    return {
        "id": m.id,
        "senderId": m.sender_id,
        "receiverId": m.receiver_id,
        "senderName": m.sender_name,
        "text": m.text,
        "timestamp": m.created_at.isoformat() if m.created_at else None,
    }


def _file_dict(f: FileRecord):
    return {
        "id": f.id,
        "name": f.name,
        "type": f.type,
        "size": f.size,
        "uploadedBy": f.uploaded_by,
        "uploadedByName": f.uploaded_by_name,
        "classroomId": f.classroom_id,
        "data": f.data,
        "createdAt": f.created_at.isoformat() if f.created_at else None,
    }


# --- Static files (frontend) ---
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static_assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = os.path.join(STATIC_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

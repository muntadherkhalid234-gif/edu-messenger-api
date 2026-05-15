from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import os
import json

DB_PATH = os.environ.get("DB_PATH", "/data/edu.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

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


Base.metadata.create_all(engine)


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


class UpdatePasswordRequest(BaseModel):
    new_password: str


class CreateClassroomRequest(BaseModel):
    name: str
    teacher_id: str


class JoinClassroomRequest(BaseModel):
    code: str
    user_id: str


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
def get_students(db: Session = Depends(get_db)):
    students = db.query(User).filter(User.role == "student").all()
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
    return _msg_dict(msg)


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
    return _pm_dict(msg)


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


# --- Health ---

@app.get("/api/health")
def health():
    return {"status": "ok"}


# --- Helpers ---

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

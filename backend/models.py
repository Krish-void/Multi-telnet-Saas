from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class SuperLoginRequest(BaseModel):
    username: str
    password: str


class TenantLoginRequest(BaseModel):
    tenant_id: str
    username: str
    password: str


class LoginResponse(BaseModel):
    user_id: int
    user_type: str
    username: str
    role: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    token: str


class CompanyCreate(BaseModel):
    name: str
    db_name: str
    admin_username: str
    admin_password: str
    admin_email: str


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    db_name: Optional[str] = None


class CompanyOut(BaseModel):
    company_id: int
    tenant_uuid: str
    name: str
    db_name: str
    created_at: Optional[datetime] = None


class UserCreate(BaseModel):
    username: str
    password: str
    email: str
    role_id: int
    company_id: int


class UserUpdate(BaseModel):
    email: Optional[str] = None
    role_id: Optional[int] = None


class UserOut(BaseModel):
    user_id: int
    username: str
    email: str
    role_name: str
    company_name: str
    company_id: int
    created_at: Optional[datetime] = None


class RoleOut(BaseModel):
    role_id: int
    role_name: str


class LogOut(BaseModel):
    log_id: int
    action: str
    user_id: Optional[int]
    username: Optional[str]
    details: Optional[str]
    created_at: Optional[datetime]

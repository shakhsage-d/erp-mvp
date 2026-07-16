from pydantic import BaseModel, Field
from typing import List


class PermissionOut(BaseModel):
    code: str
    description: str | None = None


class RoleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    permission_codes: List[str] = Field(..., min_length=1, description="Berilishi kerak bo'lgan ruxsatlar ro'yxati")


class RoleOut(BaseModel):
    id: int
    name: str
    is_custom: bool
    permission_codes: List[str]

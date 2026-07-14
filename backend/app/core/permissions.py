"""
core/permissions.py
----------------------
Dinamik ruxsat tekshiruvi. Eski `require_roles("owner")` o'rniga endi
`require_permission("finance.view")` ishlatiladi — bu ANIQ AMALGA
qarab tekshiradi, qattiq yozilgan rol nomiga emas.

Nega bu muhim: kelajakda do'kon egasi o'z lavozimini yaratsa
(masalan "Katta sotuvchi" — sotish + narx o'zgartirish, lekin xodim
qo'shish yo'q), bu funksiya HECH NARSANI o'zgartirmasdan ishlayveradi,
chunki u rol NOMIGA emas, bazadagi RUXSATGA qarab tekshiradi.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.tenant import get_current_token_payload
from app.core.exceptions import ForbiddenError
from app.modules.auth.models import RolePermission, Permission


def require_permission(permission_code: str):
    """
    Foydalanuvchining joriy lavozimida `permission_code` ruxsati
    borligini bazadan tekshiradi. Yo'q bo'lsa, 403 qaytaradi.

    Foydalanish:
        @router.post("/products")
        def create_product(
            ...,
            _: None = Depends(require_permission("inventory.manage")),
        ):
    """

    def dependency(
        payload: dict = Depends(get_current_token_payload),
        db: Session = Depends(get_db),
    ) -> None:
        role_id = payload.get("role_id")
        if role_id is None:
            raise ForbiddenError("Tokenda lavozim (role_id) topilmadi")

        has_permission = (
            db.query(RolePermission)
            .join(Permission, RolePermission.permission_id == Permission.id)
            .filter(RolePermission.role_id == role_id, Permission.code == permission_code)
            .first()
        )
        if not has_permission:
            raise ForbiddenError(
                f"Bu amal uchun ruxsatingiz yo'q (kerakli ruxsat: {permission_code})",
                extra={"required_permission": permission_code},
            )

    return dependency

import uuid

from sqlalchemy import select

from backend.config.database import SessionLocal
from backend.models.empresa import Empresa
from backend.models.user_account import UserAccount
from backend.utils.security import hash_password, normalize_cnpj


def run_seed() -> None:
    session = SessionLocal()
    try:
        cnpj = normalize_cnpj("00000000000000")
        empresa = session.scalar(select(Empresa).where(Empresa.cnpj == cnpj))
        if not empresa:
            empresa = Empresa(id=str(uuid.uuid4()), cnpj=cnpj, nome="Empresa Master", ativo=True)
            session.add(empresa)
            session.flush()

        admin_email = "admin@movisys.local"
        admin = session.scalar(select(UserAccount).where(UserAccount.email == admin_email))
        if not admin:
            admin = UserAccount(
                id=str(uuid.uuid4()),
                empresa_id=empresa.id,
                nome="Super Admin",
                email=admin_email,
                role="superadmin",
                password_hash=hash_password("Admin@123456"),
                ativo=True,
            )
            session.add(admin)

        session.commit()
        print("Seed completed. Default admin: admin@movisys.local / Admin@123456")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run_seed()

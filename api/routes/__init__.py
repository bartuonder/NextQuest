from fastapi import APIRouter

from api.routes import auth, favorites, meta, recommendations

api_router = APIRouter(prefix="/api")
api_router.include_router(meta.router)
api_router.include_router(auth.router)
api_router.include_router(favorites.router)
api_router.include_router(recommendations.router)

__all__ = ["api_router"]

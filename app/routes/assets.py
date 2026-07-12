from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from app.database import SessionLocal
from app.models import Asset, User
from app.schemas import AssetCreateRequest, AssetUpdateRequest, AssetResponse
from app.auth import get_current_admin, get_current_active_user

router = APIRouter(prefix="/assets", tags=["Assets"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# GET /assets - GET ALL ASSETS
@router.get("", response_model=list[AssetResponse])
async def get_assets(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all assets (User must be authenticated)
    """
    assets = db.query(Asset).order_by(Asset.created_at.desc()).all()
    
    return [
        AssetResponse(
            id=asset.id,
            name=asset.name,
            domain=asset.domain,
            asset_type=asset.asset_type,
            description=asset.description,
            is_active=asset.is_active,
            created_at=asset.created_at,
            updated_at=asset.updated_at
        )
        for asset in assets
    ]


# GET /assets/{id} - GET ASSET BY ID
@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset_by_id(
    asset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get asset by ID (User must be authenticated)
    """
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    
    if not asset:
        raise HTTPException(
            status_code=404,
            detail=f"Asset with ID {asset_id} not found"
        )
    
    return AssetResponse(
        id=asset.id,
        name=asset.name,
        domain=asset.domain,
        asset_type=asset.asset_type,
        description=asset.description,
        is_active=asset.is_active,
        created_at=asset.created_at,
        updated_at=asset.updated_at
    )


# POST /assets - CREATE ASSET
@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    request: AssetCreateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new asset (Admin only)
    """
    existing_asset = db.query(Asset).filter(Asset.domain == request.domain).first()
    if existing_asset:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with domain '{request.domain}' already exists"
        )
    
    new_asset = Asset(
        name=request.name,
        domain=request.domain,
        asset_type=request.asset_type,
        description=request.description,
        is_active=request.is_active
    )
    
    db.add(new_asset)
    
    try:
        db.commit()
        db.refresh(new_asset)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create asset: {str(e)}"
        )
    
    return AssetResponse(
        id=new_asset.id,
        name=new_asset.name,
        domain=new_asset.domain,
        asset_type=new_asset.asset_type,
        description=new_asset.description,
        is_active=new_asset.is_active,
        created_at=new_asset.created_at,
        updated_at=new_asset.updated_at
    )




# PUT /assets/{id} - UPDATE ASSET
@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: int,
    request: AssetUpdateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update asset by ID (Admin only)
    """
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=404,
            detail=f"Asset with ID {asset_id} not found"
        )
    
    if request.domain and request.domain != asset.domain:
        existing_asset = db.query(Asset).filter(
            Asset.domain == request.domain,
            Asset.id != asset_id
        ).first()
        if existing_asset:
            raise HTTPException(
                status_code=400,
                detail=f"Asset with domain '{request.domain}' already exists"
            )
    
    if request.name is not None:
        asset.name = request.name
    if request.domain is not None:
        asset.domain = request.domain
    if request.asset_type is not None:
        asset.asset_type = request.asset_type
    if request.description is not None:
        asset.description = request.description
    if request.is_active is not None:
        asset.is_active = request.is_active
    
    asset.updated_at = datetime.now()
    
    try:
        db.commit()
        db.refresh(asset)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update asset: {str(e)}"
        )
    
    return AssetResponse(
        id=asset.id,
        name=asset.name,
        domain=asset.domain,
        description=asset.description,
        is_active=asset.is_active,
        created_at=asset.created_at,
        updated_at=asset.updated_at
    )


# DELETE /assets/{id} - DELETE ASSET
@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Delete asset by ID (Admin only)
    """
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=404,
            detail=f"Asset with ID {asset_id} not found"
        )
    
    db.delete(asset)
    
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to delete asset: {str(e)}"
        )
    
    return None
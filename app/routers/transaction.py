from fastapi import APIRouter, Depends, HTTPException, Body, Query
from typing import List
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.schemas.transaction import (
    TransactionOut,
    DeleteResponse,
    TransactionListResponse,
    TransactionCreate,
    TransactionRead
)
import app.crud.transaction as crud_transaction
from app.schemas.financial_product import FinancialProductRead
from app.models.transaction import TransactionHistory
from app.models.portfolio import Portfolio

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get(
    "/transactions",
    summary="거래 내역 조회",
    response_model=TransactionListResponse,
    responses={
        400: {
            "description": "page 또는 per_page가 1보다 작은 경우",
            "content": {
                "application/json": {
                    "example": {"detail": "Page와 per_page는 1 이상이어야 합니다."}
                }
            },
        },
        404: {
            "description": "포트폴리오를 찾을 수 없음.",
            "content": {
                "application/json": {"example": {"detail": "포트폴리오를 찾을 수 없음"}}
            },
        },
        500: {
            "description": "데이터베이스 연결 오류",
            "content": {
                "application/json": {"example": {"detail": "데이터베이스 연결 오류"}}
            },
        },
    },
)
def read_transactions(
    portfolio_id: int = Query(..., description="조회할 포트폴리오 ID"),
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    per_page: int = Query(10, ge=1, le=100, description="페이지당 표시할 개수 (최대 100)"),
    db: Session = Depends(get_db),
):

    portfolio = db.query(Portfolio).filter(Portfolio.portfolio_id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="거래내역을 찾을 수 없습니다.")


    offset = (page - 1) * per_page

    total = db.query(TransactionHistory).filter(
        TransactionHistory.portfolio_id == portfolio_id
    ).count()

    transactions_query = db.query(TransactionHistory).filter(
        TransactionHistory.portfolio_id == portfolio_id
    ).offset(offset).limit(per_page).all()

    transaction_read_list = [
        TransactionRead(
            transaction_id=t.transaction_id,
            portfolio_id=t.portfolio_id,
            financial_product_id=t.financial_product_id,
            transaction_type=t.transaction_type,
            price=t.price,
            profit_rate=t.profit_rate,
            currency_code=t.currency_code,
            quantity=t.quantity,
            created_at=t.created_at,
            financial_product=FinancialProductRead(
                financial_product_id=t.financial_product.financial_product_id,
                product_name=t.financial_product.product_name,
                ticker=t.financial_product.ticker,
            )
        )
        for t in transactions_query
    ]

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "transactions": transaction_read_list,
    }


@router.delete(
    "/transactions",
    summary="거래 내역 삭제",
    response_model=DeleteResponse,
    responses={
        404: {
            "description": "존재하지 않는 transaction_id",
            "content": {
                "application/json": {"example": {"detail": "Transaction 찾을 수 없음"}}
            },
        },
        500: {
            "description": "데이터베이스 연결 오류",
            "content": {
                "application/json": {"example": {"detail": "데이터베이스 연결 오류"}}
            },
        },
    },
)
def delete_transactions(
    transaction_ids: List[int] = Body(...),
    db: Session = Depends(get_db)
):
    """
    거래 내역 삭제
    - transaction_ids: 삭제할 거래 내역 ID 목록
    """
    not_found_ids = []
    for transaction_id in transaction_ids:
        success = crud_transaction.delete_transaction(db, transaction_id)
        if not success:
            not_found_ids.append(transaction_id)
    if not_found_ids:
        raise HTTPException(
            status_code=404, 
            detail=f"Transaction 찾을 수 없음: {not_found_ids}"
        )
    return {"message": "트랜잭션 삭제 성공"}


@router.post(
    "/transactions",
    summary="거래 내역 생성",
    response_model=TransactionOut,
    responses={
        500: {
            "description": "데이터베이스 연결 오류",
            "content": {
                "application/json": {"example": {"detail": "트랜잭션 생성 오류 발생"}}
            },
        },
    },
)
def create_transaction(
    transaction: TransactionCreate,
    db: Session = Depends(get_db)
):
    """
    거래 내역 생성
    """
    new_transaction = crud_transaction.create_transaction(db, transaction)
    return new_transaction

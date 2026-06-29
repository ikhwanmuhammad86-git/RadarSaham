from pydantic import BaseModel
from typing import Optional

class Stock(BaseModel):
    kode: str
    nama: str
    harga: float
    akumulasi: str
    signal: str
    volume: Optional[int] = None
    foreign_flow: Optional[float] = None
    broker_score: Optional[int] = None
    low_price: Optional[float] = None
    high_price: Optional[float] = None
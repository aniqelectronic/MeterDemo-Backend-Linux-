from pydantic import BaseModel
    
class OrderCreateRequest(BaseModel):
    order_amount: float
    qr_validity: int
    store_id: str
    terminal_id: str
    shift_id: str
    
class OrderStatusRequest(BaseModel):
    order_no: str
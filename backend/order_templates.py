"""
Order Templates Manager for pyPortMan
Save and reuse order configurations
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from models import Account, OrderTemplate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class OrderTemplateManager:
    """Manager for order templates"""

    def __init__(self, db: Session):
        self.db = db

    def create_template(
        self,
        account_id: Optional[int],
        name: str,
        description: Optional[str],
        stock: Optional[str],
        exchange: str,
        transaction_type: str,
        order_type: str,
        product: str,
        variety: str,
        default_quantity: int,
        default_price: Optional[float],
        default_stoploss: Optional[float],
        default_target: Optional[float],
        validity: str
    ) -> OrderTemplate:
        """
        Create a new order template
        """
        template = OrderTemplate(
            account_id=account_id,
            name=name,
            description=description,
            stock=stock,
            exchange=exchange,
            transaction_type=transaction_type,
            order_type=order_type,
            product=product,
            variety=variety,
            default_quantity=default_quantity,
            default_price=default_price,
            default_stoploss=default_stoploss,
            default_target=default_target,
            validity=validity,
            is_active=True
        )

        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)

        logger.info(f"Created order template: {name}")
        return template

    def update_template(
        self,
        template_id: int,
        **kwargs
    ) -> OrderTemplate:
        """
        Update an existing order template
        """
        template = self.db.query(OrderTemplate).filter(
            OrderTemplate.id == template_id
        ).first()

        if not template:
            raise ValueError(f"Order template {template_id} not found")

        # Update provided fields
        for field, value in kwargs.items():
            if hasattr(template, field) and value is not None:
                setattr(template, field, value)

        template.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(template)

        logger.info(f"Updated order template {template_id}")
        return template

    def delete_template(self, template_id: int) -> bool:
        """
        Delete an order template
        """
        template = self.db.query(OrderTemplate).filter(
            OrderTemplate.id == template_id
        ).first()

        if not template:
            raise ValueError(f"Order template {template_id} not found")

        self.db.delete(template)
        self.db.commit()

        logger.info(f"Deleted order template {template_id}")
        return True

    def get_templates(
        self,
        account_id: Optional[int] = None,
        is_active: Optional[bool] = None
    ) -> List[OrderTemplate]:
        """
        Get order templates with optional filters
        """
        query = self.db.query(OrderTemplate)

        if account_id:
            query = query.filter(
                (OrderTemplate.account_id == account_id) |
                (OrderTemplate.account_id.is_(None))
            )

        if is_active is not None:
            query = query.filter(OrderTemplate.is_active == is_active)

        return query.order_by(OrderTemplate.name).all()

    def get_template(self, template_id: int) -> OrderTemplate:
        """
        Get a specific order template
        """
        template = self.db.query(OrderTemplate).filter(
            OrderTemplate.id == template_id
        ).first()

        if not template:
            raise ValueError(f"Order template {template_id} not found")

        return template

    def apply_template(
        self,
        template_id: int,
        stock: Optional[str] = None,
        quantity: Optional[int] = None,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Apply a template to create order parameters
        Overrides can be provided for stock, quantity, and price
        """
        template = self.get_template(template_id)

        order_params = {
            "tradingsymbol": stock or template.stock,
            "exchange": template.exchange,
            "transaction_type": template.transaction_type,
            "quantity": quantity or template.default_quantity,
            "order_type": template.order_type,
            "product": template.product,
            "variety": template.variety,
            "validity": template.validity
        }

        # Add optional fields
        if template.order_type in ["LIMIT", "SL"]:
            order_params["price"] = price or template.default_price

        if template.variety == "co":
            order_params["stoploss"] = template.default_stoploss

        if template.variety == "bo":
            order_params["price"] = price or template.default_price
            order_params["target"] = template.default_target
            order_params["stoploss"] = template.default_stoploss

        return order_params

    def get_template_summary(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get summary of order templates
        """
        query = self.db.query(OrderTemplate)

        if account_id:
            query = query.filter(
                (OrderTemplate.account_id == account_id) |
                (OrderTemplate.account_id.is_(None))
            )

        total = query.count()
        active = query.filter(OrderTemplate.is_active == True).count()
        inactive = query.filter(OrderTemplate.is_active == False).count()

        # Count by transaction type
        buy_count = query.filter(OrderTemplate.transaction_type == "BUY").count()
        sell_count = query.filter(OrderTemplate.transaction_type == "SELL").count()

        return {
            "total": total,
            "active": active,
            "inactive": inactive,
            "buy_templates": buy_count,
            "sell_templates": sell_count
        }

    def duplicate_template(self, template_id: int, new_name: str) -> OrderTemplate:
        """
        Duplicate an existing order template
        """
        original = self.get_template(template_id)

        new_template = OrderTemplate(
            account_id=original.account_id,
            name=new_name,
            description=f"Copy of {original.name}",
            stock=original.stock,
            exchange=original.exchange,
            transaction_type=original.transaction_type,
            order_type=original.order_type,
            product=original.product,
            variety=original.variety,
            default_quantity=original.default_quantity,
            default_price=original.default_price,
            default_stoploss=original.default_stoploss,
            default_target=original.default_target,
            validity=original.validity,
            is_active=True
        )

        self.db.add(new_template)
        self.db.commit()
        self.db.refresh(new_template)

        logger.info(f"Duplicated order template: {new_name}")
        return new_template

    def get_popular_templates(self, limit: int = 10) -> List[OrderTemplate]:
        """
        Get popular templates (global templates with no account_id)
        """
        return self.db.query(OrderTemplate).filter(
            OrderTemplate.account_id.is_(None),
            OrderTemplate.is_active == True
        ).order_by(OrderTemplate.name).limit(limit).all()

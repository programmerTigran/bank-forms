from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Company, engine

with Session(engine) as session:
    for co in session.scalars(select(Company).order_by(Company.sort_order, Company.name)):
        print(co.name, len(co.customers))
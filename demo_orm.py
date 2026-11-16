from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Company, engine

engine.echo = True   # print every SQL query the ORM runs

with Session(engine) as session:
    print("\n--- 1. ask for a company ---")
    co = session.scalars(select(Company).where(Company.name == "Adidas")).one()

    print("\n--- 2. what we got back ---")
    print(type(co))
    print(co.company_id, co.name, co.logo)

    print("\n--- 3. touch co.customers ---")
    first = co.customers[0]

    print("\n--- 4. go back from the customer ---")
    print(first.first_name, first.surname, "->", first.company.name)
    
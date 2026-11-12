import json
import psycopg

#All Customer IDs For The Dropdown
def get_customer_ids():
    with psycopg.connect() as conn:
        cur=conn.cursor()
        cur.execute("SELECT customer_id " \
                    "FROM customers " \
                    "ORDER BY customer_id")
        return [row[0] for row in cur.fetchall()]

#All Template Names For The Dropdown
def get_template_names():
    with psycopg.connect() as conn:
        cur=conn.cursor()
        cur.execute("SELECT DISTINCT name " \
                    "FROM document_templates " \
                    "ORDER BY name")
        return [row[0] for row in cur.fetchall()]

#Call The Customer By Their ID
def get_customer(customer_id):
    with psycopg.connect() as conn:
        cur=conn.cursor()
        cur.execute("SELECT first_name,surname " \
                    "FROM customers " \
                    "WHERE customer_id=%s",
                    (customer_id,))
        row = cur.fetchone()
        return row

#Fetches Gets The Newest Form
def load_template(name):
    with psycopg.connect() as conn:
        cur=conn.cursor()
        cur.execute("SELECT definition " \
                    "FROM document_templates " \
                    "WHERE name=%s " \
                    "ORDER BY version DESC " \
                    "LIMIT 1 ",
                    (name,))
        row=cur.fetchone()
        if row is None:
            raise ValueError("Template " + name + " not found")
        definition=row[0]
        if isinstance(definition,str):
            definition=json.loads(definition)
        return definition
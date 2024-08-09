import os
import random
import sqlite3

def create_tables():
    conn = sqlite3.connect('menu.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price_small REAL NOT NULL,
            price_medium REAL NOT NULL,
            price_large REAL NOT NULL,
            price_extra_large REAL NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crust (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            price REAL NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ingredient TEXT NOT NULL UNIQUE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pizza_ingredients (
            pizza_id INTEGER,
            ingredient_id INTEGER,
            PRIMARY KEY (pizza_id, ingredient_id),
            FOREIGN KEY (pizza_id) REFERENCES menu(id),
            FOREIGN KEY (ingredient_id) REFERENCES ingredients(id)
        );
    ''')

    conn.commit()
    conn.close()
    

def insert_crust_item(name):
    price = round(random.uniform(1, 3), 2)
    
    conn = sqlite3.connect('menu.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO crust (type, price)
        VALUES (?, ?)
    ''', (name, price))
    conn.commit()
    conn.close()


def insert_menu_item(name, price):
    size = {
        'small': 1,
        'medium': 0,
        'large': 3,
        'extra_large': 5
    }
    
    price_small = price - size['small']
    price_medium = price - size['medium']
    price_large = price + size['large']
    price_extra_large = price + size['extra_large']
    
    conn = sqlite3.connect('menu.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO menu (name, price_small, price_medium, price_large, price_extra_large)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, price_small, price_medium, price_large, price_extra_large))
    conn.commit()
    conn.close()

def insert_ingredient(ingredient):
    conn = sqlite3.connect('menu.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO ingredients (ingredient)
        VALUES (?)
    ''', (ingredient,))
    conn.commit()
    conn.close()
    
def get_ingredient_id(ingredient):
    conn = sqlite3.connect('menu.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id FROM ingredients WHERE ingredient = ?
    ''', (ingredient,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_menu_id(name):
    conn = sqlite3.connect('menu.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id FROM menu WHERE name = ?
    ''', (name,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None
    
def insert_pizza_ingredient(pizza_name, ingredient_name):
    pizza_id = get_menu_id(pizza_name)
    ingredient_id = get_ingredient_id(ingredient_name)
    if pizza_id and ingredient_id:
        conn = sqlite3.connect('menu.db')
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO pizza_ingredients (pizza_id, ingredient_id)
                VALUES (?, ?)
            ''', (pizza_id, ingredient_id))
            conn.commit()
        except sqlite3.IntegrityError:
            print(f'Association between pizza "{pizza_name}" and ingredient "{ingredient_name}" already exists.')
        finally:
            conn.close()

def get_pizza_names():
    conn = sqlite3.connect('menu.db')
    cursor = conn.cursor()
    query = 'SELECT name FROM menu'
    cursor.execute(query)
    pizza_names = cursor.fetchall()
    conn.close()
    return [name[0] for name in pizza_names]

def get_ingredients_for_pizza(pizza_name):
    conn = sqlite3.connect('menu.db')
    cursor = conn.cursor()
    query = '''
        SELECT i.ingredient
        FROM ingredients i
        JOIN pizza_ingredients pi ON i.id = pi.ingredient_id
        JOIN menu m ON pi.pizza_id = m.id
        WHERE m.name = ?
    '''
    cursor.execute(query, (pizza_name,))
    ingredients = cursor.fetchall()
    conn.close()
    return [ingredient[0] for ingredient in ingredients]
            
def show_table_data(table_name):
    conn = sqlite3.connect('menu.db')
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name};")
    data = cursor.fetchall()
    conn.close()
    return data

if __name__ == "__main__":
    db_path = 'menu.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"File {db_path} eliminato.")
    
    create_tables()
    
    pizzas = {
        'Mushrooms': ['Mushrooms'],
        'Hawaii': ['Pineapple', 'Ham'],
        'Margherita': ['Tomato', 'Mozzarella', 'Basil'],
        'Pepperoni': ['Tomato', 'Mozzarella', 'Spicy Salami'],
        'Vegetarian': ['Tomato', 'Mozzarella', 'Bell Peppers', 'Mushrooms', 'Olives', 'Eggplant'],
        'Four Seasons': ['Tomato', 'Mozzarella', 'Mushrooms', 'Ham', 'Olives', 'Artichokes'],
        'Capricciosa': ['Tomato', 'Mozzarella', 'Ham', 'Artichokes', 'Mushrooms', 'Olives'],
        'Crudo and Burrata': ['Prosciutto Crudo', 'Burrata', 'Tomato'],
        'Marinara': ['Tomato', 'Garlic', 'Oregano'],
        'Four Cheeses': ['Mozzarella', 'Gorgonzola', 'Parmesan', 'Ricotta'],
        'Ham and Mushrooms': ['Tomato', 'Mozzarella', 'Ham', 'Mushrooms'],
        'Tuna and Onions': ['Tuna', 'Onion', 'Tomato', 'Mozzarella'],
        'Boscaiola': ['Tomato', 'Mozzarella', 'Mushrooms', 'Sausage'],
        'Sausage and Broccoli Rabe': ['Sausage', 'Broccoli Rabe', 'Mozzarella'],
        'Gorgonzola and Walnuts': ['Tomato', 'Mozzarella', 'Gorgonzola', 'Walnuts']
    }

    prices = {
        'Mushrooms': 8.99,
        'Hawaii': 14.99,
        'Margherita': 5.99,
        'Pepperoni': 6.99,
        'Vegetarian': 8.99,
        'Four Seasons': 15.99,
        'Capricciosa': 7.99,
        'Crudo and Burrata': 12.99,
        'Marinara': 4.99,
        'Four Cheeses': 6.99,
        'Ham and Mushrooms': 7.99,
        'Tuna and Onions': 7.99,
        'Boscaiola': 8.99,
        'Sausage and Broccoli Rabe': 10.99,
        'Gorgonzola and Walnuts': 10.99
    }
    
    create_tables()
    
    crusts = ["thin", "thick", "stuffed", "gluten-free", "whole wheat", "flatbread", "cracker"]
    for c in crusts:
        insert_crust_item(c)
    
    for pizza, ingredients in pizzas.items():
        insert_menu_item(pizza, prices[pizza]) 
        for ingredient in ingredients:
            insert_ingredient(ingredient)
            insert_pizza_ingredient(pizza, ingredient)
    
    # ingredients = show_table_data('ingredients')
    # print('Ingredients in database')
    # for i in ingredients:
    #     print(i)
    
    # crusts_table = show_table_data('crust')
    # print('Crusts in database')
    # for c in crusts_table:
    #     print(c)
        
    # menu = get_pizza_names()
    # print('Menu in database')
    # for m in menu:
    #     ingredients = get_ingredients_for_pizza(m)
    #     print(m, ":", ingredients)
        
    
    
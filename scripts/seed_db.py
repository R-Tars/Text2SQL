import os
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.exc import ProgrammingError

# 配置
# 注意：连接到默认的 'postgres' 数据库以创建新数据库
DEFAULT_DB_URL = "postgresql://postgres:postgres@localhost:5432/postgres"
TARGET_DB_NAME = "text2sql_demo"
TARGET_DB_URL = f"postgresql://postgres:postgres@localhost:5432/{TARGET_DB_NAME}"

Base = declarative_base()

# --- 定义 Schema ---

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100))
    city = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50))
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    order_date = Column(DateTime, default=datetime.now)
    total_amount = Column(Float, default=0.0)
    status = Column(String(20), default='completed') # pending, completed, cancelled
    
    user = relationship("User")

class OrderItem(Base):
    __tablename__ = 'order_items'
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer, default=1)
    price_at_purchase = Column(Float)
    
    order = relationship("Order")
    product = relationship("Product")

# --- 初始化数据库 ---

def create_database():
    """连接到默认数据库并创建目标数据库（如果不存在）"""
    engine = create_engine(DEFAULT_DB_URL, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        # 检查数据库是否存在
        result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{TARGET_DB_NAME}'"))
        if not result.fetchone():
            print(f"Creating database {TARGET_DB_NAME}...")
            conn.execute(text(f"CREATE DATABASE {TARGET_DB_NAME}"))
        else:
            print(f"Database {TARGET_DB_NAME} already exists.")

def seed_data():
    """连接到目标数据库并填充数据"""
    engine = create_engine(TARGET_DB_URL)
    Base.metadata.drop_all(engine) # 重置表
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()

    print("Generating sample data...")

    # 1. Create Users
    cities = ['Beijing', 'Shanghai', 'Guangzhou', 'Shenzhen', 'Hangzhou']
    users = []
    for i in range(20):
        user = User(
            username=f"user_{i+1}",
            email=f"user_{i+1}@example.com",
            city=random.choice(cities),
            created_at=datetime.now() - timedelta(days=random.randint(1, 365))
        )
        users.append(user)
    session.add_all(users)
    session.commit()

    # 2. Create Products
    categories = ['Electronics', 'Clothing', 'Books', 'Home', 'Sports']
    products = []
    for i in range(50):
        cat = random.choice(categories)
        price = round(random.uniform(10, 1000), 2)
        prod = Product(
            name=f"{cat} Product {i+1}",
            category=cat,
            price=price,
            stock=random.randint(10, 200)
        )
        products.append(prod)
    session.add_all(products)
    session.commit()

    # 3. Create Orders and Items
    orders = []
    for _ in range(100):
        user = random.choice(users)
        order_date = datetime.now() - timedelta(days=random.randint(0, 60))
        order = Order(
            user_id=user.id,
            order_date=order_date,
            status=random.choice(['completed', 'pending', 'cancelled']),
            total_amount=0
        )
        session.add(order)
        session.flush() # get order ID

        total = 0
        num_items = random.randint(1, 5)
        for _ in range(num_items):
            prod = random.choice(products)
            qty = random.randint(1, 3)
            item = OrderItem(
                order_id=order.id,
                product_id=prod.id,
                quantity=qty,
                price_at_purchase=prod.price
            )
            total += prod.price * qty
            session.add(item)
        
        order.total_amount = total
    
    session.commit()
    print("✅ Database seeded successfully with:")
    print(f" - {len(users)} Users")
    print(f" - {len(products)} Products")
    print(f" - 100 Orders")

if __name__ == "__main__":
    try:
        create_database()
        seed_data()
    except Exception as e:
        print(f"Error: {e}")
        print("\n⚠️ 提示: 请确保你已安装 PostgreSQL 且服务正在运行。")
        print("默认连接信息: user=postgres, password=postgres, port=5432")




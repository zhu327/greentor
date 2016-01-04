# -*- coding:utf-8 -*-

from sqlalchemy import Column, Integer, String
from sqlalchemy import create_engine
from sqlalchemy.orm import create_session
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    email = Column(String(120), unique=True)

    def __init__(self, name=None, email=None):
        self.name = name
        self.email = email

    def __repr__(self):
        return '<User %r>' % (self.name)


def test():
    engine = create_engine('mysql://root:powerall@10.86.11.116/mywork', convert_unicode=True)
    session = create_session(bind=engine)
    if not session.query(User).all():
        user = User(name="alex", email="alex@alex.com")
        session.begin()
        session.add(user)
        session.commit()
    else:
        users = []
        try:
            for user in  session.query(User).filter(User.name=="alex"):
                users.append({"name":user.name, "email": user.email})
            return users    
        finally:
            engine.dispose()




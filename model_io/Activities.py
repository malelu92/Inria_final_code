#!/usr/bin/python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

#from user_devices import user_devices

DB = 'postgresql+psycopg2:///ucnstudy_hostview_data'
engine = create_engine(DB, echo=False, poolclass=NullPool)
Base = declarative_base(engine)

class Activities(Base):
    __tablename__ = 'activities'
    __table_args__ = {'autoload':True}

def loadDatabaseSession():
    """"""
    metadata = Base.metadata
    Database_session = sessionmaker(bind=engine)
    return Database_session()

if __name__ == "__main__":
     database_session = loadDatabaseSession()
     res = database_session.query(Activities).first()
     print (res.user_name, res.fullscreen)
     database_session.close()

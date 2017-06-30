from Base import Base
from sqlalchemy import Table, Column, ForeignKey

# Import this so that the user + device objects work correctly
user_devices = Table('user_devices', 
                     Base.metadata,
                     Column('user_id', 
                            ForeignKey('users.id'), primary_key=True),
                     Column('device_id', 
                            ForeignKey('devices.id'), primary_key=True))

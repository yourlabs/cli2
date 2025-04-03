"""
.. envvar:: CODE2_DB

    playhouse.db_url connection string
"""

import cli2
from peewee import SqliteDatabase, Model, IntegerField, TextField, FloatField, ForeignKeyField, fn
from playhouse.db_url import connect

db = connect(cli2.cfg['CODE2_DB'])

class Language(Model):
    id = IntegerField(primary_key=True)
    name = TextField(unique=True)
    class Meta:
        database = db
        table_name = 'languages'

class File(Model):
    id = IntegerField(primary_key=True)
    path = TextField(unique=True)
    mtime = FloatField()
    language = ForeignKeyField(Language, backref='files', null=True, on_delete='SET NULL', column_name='language_id')
    token_count = IntegerField(default=0)
    class Meta:
        database = db
        table_name = 'files'

class Symbol(Model):
    id = IntegerField(primary_key=True)
    file = ForeignKeyField(File, backref='symbols', on_delete='CASCADE')
    type = TextField()
    name = TextField()
    line_number = IntegerField()
    class Meta:
        database = db
        table_name = 'symbols'

class Reference(Model):
    symbol = ForeignKeyField(Symbol, backref='references', on_delete='CASCADE')
    file = ForeignKeyField(File, backref='references', on_delete='CASCADE')
    count = IntegerField()
    class Meta:
        database = db
        table_name = 'reference'
        indexes = ((('symbol', 'file'), True),)

def init():
    with db.atomic():
        db.create_tables([Language, File, Symbol, Reference], safe=True)
    with db.atomic():
        for lang in ['python', 'javascript', 'java', 'cpp', 'ruby']:
            Language.get_or_create(name=lang)

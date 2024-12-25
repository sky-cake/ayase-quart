import aiosqlite
from utils import make_src_path
from db.sqlite import row_factory

class eavDb:

    async def init(self):
        self.db_path = make_src_path('eav.db')
        self.conn = None
        self.conn = await self.create_db()

    async def create_db(self):
        if self.conn is None:
            self.conn = await aiosqlite.connect(self.db_path)
            self.conn.row_factory = row_factory
            
            await self.conn.execute('''
                create table if not exists eav (
                    entity text, 
                    attribute text, 
                    value text, 
                    primary key (entity, attribute)
                )
            ''')

            await self.conn.execute('create index if not exists idx_entity on eav (entity)')
            await self.conn.execute('create index if not exists idx_attribute on eav (attribute)')
            await self.conn.execute('create index if not exists idx_value on eav (value)')
            await self.conn.execute('create index if not exists idx_entity_attribute on eav (entity, attribute)')

            await self.conn.commit()

        return self.conn

    async def get_value(self, entity, attribute):
        cursor = await self.conn.execute('select value from eav where entity = ? and attribute = ?', (entity, attribute))
        result = await cursor.fetchone()
        return result[0] if result else None

    async def set_value(self, entity, attribute, value):
        await self.conn.execute('insert or replace into eav (entity, attribute, value) values (?, ?, ?)', (entity, attribute, value))
        await self.conn.commit()

    async def delete_value(self, entity, attribute):
        await self.conn.execute('delete from eav where entity = ? and attribute = ?', (entity, attribute))
        await self.conn.commit()

    async def get_entities(self):
        cursor = await self.conn.execute('select distinct entity from eav')
        return [row[0] async for row in cursor]

    async def get_attributes(self):
        cursor = await self.conn.execute('select distinct attribute from eav')
        return [row[0] async for row in cursor]

    async def delete_entity(self, entity):
        await self.conn.execute('delete from eav where entity = ?', (entity,))
        await self.conn.commit()

    async def delete_all(self):
        await self.conn.execute('delete from eav')
        await self.conn.commit()

    async def get_eavs(self, entity=None, attribute=None):
        query = 'select entity, attribute, value from eav'
        params = []

        conditions = []
        if entity:
            conditions.append('entity = ?')
            params.append(entity)
        if attribute:
            conditions.append('attribute = ?')
            params.append(attribute)

        if conditions:
            query += ' where ' + ' and '.join(conditions)

        results = await (await self.conn.execute(query, params)).fetchall()
        return results

    async def close(self):
        await self.conn.close()


db_eav = eavDb()

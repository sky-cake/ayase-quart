from ..db import db_eav


class EAV:
    async def init(self):
        await db_eav.query_dict('''
            create table if not exists eav (
                entity text,
                attribute text,
                value text,
                primary key (entity, attribute)
            )
        ''', commit=True)
        await db_eav.query_dict('create index if not exists idx_entity on eav (entity)', commit=True)
        await db_eav.query_dict('create index if not exists idx_attribute on eav (attribute)', commit=True)
        await db_eav.query_dict('create index if not exists idx_value on eav (value)', commit=True)
        await db_eav.query_dict('create index if not exists idx_entity_attribute on eav (entity, attribute)', commit=True)

    async def get_value(self, entity, attribute):
        if (rows := await db_eav.query_tuple('select value from eav where entity = ? and attribute = ?', params=(entity, attribute))):
            return rows[0][0] if rows else None

    async def set_value(self, entity, attribute, value):
        await db_eav.query_dict('insert or replace into eav (entity, attribute, value) values (?, ?, ?)', params=(entity, attribute, value), commit=True)

    async def delete_value(self, entity, attribute):
        await db_eav.query_dict('delete from eav where entity = ? and attribute = ?', params=(entity, attribute), commit=True)

    async def get_entities(self) -> list[dict]:
        rows = await db_eav.query_tuple('select distinct entity from eav')
        return [row[0] for row in rows] if rows else []

    async def get_attributes(self) -> list[dict]:
        rows = await db_eav.query_tuple('select distinct attribute from eav')
        return [row[0] for row in rows] if rows else []

    async def delete_entity(self, entity):
        await db_eav.query_dict('delete from eav where entity = ?', params=(entity,), commit=True)

    async def delete_all(self):
        await db_eav.query_dict('delete from eav', commit=True)

    async def get_eavs(self, entity=None, attribute=None):
        sql = 'select entity, attribute, value from eav'
        params = []

        conditions = []
        if entity:
            conditions.append('entity = ?')
            params.append(entity)
        if attribute:
            conditions.append('attribute = ?')
            params.append(attribute)

        if conditions:
            sql += ' where ' + ' and '.join(conditions)

        rows = await db_eav.query_dict(sql, params=params)
        return rows if rows else []


eav = EAV()

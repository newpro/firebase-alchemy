def drop_db(url):
    # -- setup --
    from sqlalchemy import create_engine
    engine = create_engine(url)

    # -- drop --
    """
    For current version of sql-alchemy, have two issues with Postgres: 
    Postgres Lock When call drop_all, and also does not drop in cascade order.
    This function is a workaround.
    
    Credit http://www.sqlalchemy.org/trac/wiki/UsageRecipes/DropEverything
    """
    print '---- DROP START ----'
    from sqlalchemy.engine import reflection
    from sqlalchemy.schema import (
        MetaData,
        Table,
        DropTable,
        ForeignKeyConstraint,
        DropConstraint,
    )
    conn=engine.connect()
    trans = conn.begin()
    inspector = reflection.Inspector.from_engine(engine)
    metadata = MetaData()
    tbs = []
    all_fks = []
    for table_name in inspector.get_table_names():
        fks = []
        for fk in inspector.get_foreign_keys(table_name):
            if not fk['name']:
                continue
            fks.append(
                ForeignKeyConstraint((),(),name=fk['name'])
            )
        t = Table(table_name,metadata,*fks)
        tbs.append(t)
        all_fks.extend(fks)

    for fkc in all_fks:
        conn.execute(DropConstraint(fkc))
    for table in tbs:
        conn.execute(DropTable(table))
    trans.commit()
    print ' -- DROP END --'

# -*- coding: utf-8 -*-
import models


# This method is used to load the institution of yodlee upon installation (post_init_hook)
def _load_csv(cr, registry):
    import os
    import csv
    from openerp.tools import misc

    request = """INSERT INTO online_institution(online_id, name, type)
        SELECT i.* FROM (
            VALUES %s
        )
        AS i(online_id, name, type)
        WHERE NOT EXISTS (
            SELECT 1 FROM online_institution WHERE (online_id, type) = (i.online_id, i.type)
        );
    """

    pathname = os.path.join('account_yodlee', 'data', 'online.institution.csv')
    vals = []
    with misc.file_open(pathname) as f:
        for row in csv.reader(f, delimiter=';', quotechar='"'):
            vals.append(tuple(row))

    if vals:
        placeholders = ", ".join(["(%s,%s,%s)"] * len(vals))
        query = request % placeholders
        params = list(sum(vals, ()))

        cr.execute(query, params)

# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2014 Odoo S.A. (<https://www.odoo.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Synchronization with the external timesheet application',
    'version': '1.0',
    'category': 'Project & Timesheet Management',
    'description': """
Synchronization of timesheet entries with the external timesheet application.
====================================================================

If you use the external timesheet application, this module alows you to synchronize timesheet entries between Odoo and the application.
    """,
    'author': 'Odoo SA',
    'website': 'https://www.odoo.com/page/project-management',
    'images': ['images/invoice_task_work.jpeg', 'images/my_timesheet.jpeg', 'images/working_hour.jpeg'],
    'depends': ['project_timesheet', 'hr_timesheet_sheet'],
    'data': [
        'views/templates.xml',
        'views/timesheet_views.xml',
    ],
    'qweb': [
        'static/src/xml/timesheet_app_backend_template.xml',
    ],
    'installable': True,
}

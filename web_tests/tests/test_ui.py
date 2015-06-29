# -*- coding: utf-8 -*-
import os

import openerp.tests

class TestUi(openerp.tests.HttpCase):
    def test_01_jsfile_ui_hello(self):
        self.phantom_jsfile(os.path.join(os.path.dirname(__file__), 'test_ui_hello.js'))
    def test_02_jsfile_ui_load(self):
        self.phantom_jsfile(os.path.join(os.path.dirname(__file__), 'test_ui_load.js'))
    def test_03_js_public(self):
        self.phantom_js('/',"console.log('ok')","console")
    def test_04_js_admin(self):
        self.phantom_js('/web',"console.log('ok')","odoo.__DEBUG__.services['web.web_client'].action_manager", login='admin')

    def test_05_menu(self):
        """Open the webclient with `action=action_id` as URL"""
        get_object_reference = self.registry('ir.model.data').get_object_reference
        action_id = get_object_reference(self.cr, self.uid, 'base', 'open_module_tree')[1]
        self.phantom_js(
            '/web#action=%s' % action_id,
            "odoo.__DEBUG__.services['web.web_client'].action_manager.get_inner_action().get_action_descr().id === %s && console.log('ok')" % action_id,
            ready="odoo.__DEBUG__.services['web.web_client'].action_manager.get_inner_action()",
            login='admin'
        )

    def test_06_menu(self):
        """Open the webclient with `menu=menu_id` as URL"""
        get_object_reference = self.registry('ir.model.data').get_object_reference
        menu_id = get_object_reference(self.cr, self.uid, 'base', 'menu_module_tree')[1]
        menu = self.registry('ir.ui.menu').browse(self.cr, self.uid, menu_id)
        action_id = menu.action.id
        self.phantom_js(
            '/web#menu_id=%s' % menu_id,
            "odoo.__DEBUG__.services['web.web_client'].action_manager.get_inner_action().get_action_descr().id === %s && console.log('ok')" % action_id,
            ready="odoo.__DEBUG__.services['web.web_client'].action_manager.get_inner_action()",
            login='admin'
        )

    def test_07_menu(self):
        """Open the webclient with `action=action_name` as URL"""
        action = "base.open_module_tree"
        get_object_reference = self.registry('ir.model.data').get_object_reference
        action_id = get_object_reference(self.cr, self.uid, action.split('.')[0], action.split('.')[1])[1]
        self.phantom_js(
            '/web#action=%s' % action,
            "odoo.__DEBUG__.services['web.web_client'].action_manager.get_inner_action().get_action_descr().id === %s && console.log('ok')" % action_id,
            ready="odoo.__DEBUG__.services['web.web_client'].action_manager.get_inner_action()",
            login='admin'
        )

# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import UserError, RedirectWarning
from ebaysdk.exception import ConnectionError


class ebay_category(models.Model):
    _name = 'ebay.category'

    name = fields.Char('Name')
    category_id = fields.Integer('Category ID')
    category_parent_id = fields.Integer('Category Parent ID')
    leaf_category = fields.Boolean(default=False)
    category_type = fields.Char('Category Type')

    @api.model
    def _cron_sync(self):
        try:
            self.sync_categories()
        except RedirectWarning:
            # not configured, ignore
            pass

    @api.model
    def sync_categories(self):
        domain = self.env['ir.config_parameter'].get_param('ebay_domain')
        ebay_api = self.env['product.template'].get_ebay_api(domain)
        try:
            categories = ebay_api.execute('GetCategories')
        except ConnectionError as e:
            self.env['product.template']._manage_ebay_error(e)
        ebay_version = categories.dict()['Version']
        version = self.env['ir.config_parameter'].get_param('ebay_sandbox_category_version'
                                                            if domain == 'sand'
                                                            else 'ebay_prod_category_version')
        version = 10
        if version != ebay_version:
            self.env['ir.config_parameter'].set_param('ebay_sandbox_category_version'
                                                      if domain == 'sand'
                                                      else 'ebay_prod_category_version',
                                                      ebay_version)
            call_data = {
                'DetailLevel': 'ReturnAll',
                'LevelLimit': 4,
            }
            try:
                categories = ebay_api.execute('GetCategories', call_data)
            except ConnectionError as e:
                self.env['product.template']._manage_ebay_error(e)
            self.create_categories(ebay_api, categories.dict()['CategoryArray']['Category'])
        self.sync_store_categories(ebay_api)

    @api.model
    def create_categories(self, ebay_api, categories):
        for category in categories:
            cat = self.search([
                ('category_id', '=', int(category['CategoryID'])),
                ('category_type', '=', 'ebay')])
            if not cat:
                cat = self.create({
                    'category_id': category['CategoryID'],
                    'category_type': 'ebay'})
            cat.write({'name': category['CategoryName'],
                       'category_parent_id': category['CategoryParentID']
                       if category['CategoryID'] != category['CategoryParentID']
                       else 0,
                       'leaf_category': category['LeafCategory']
                       if 'LeafCategory' in category else False})
            if category['CategoryLevel'] == '1':
                call_data = {
                    'CategoryID': category['CategoryID'],
                    'ViewAllNodes': True,
                    'DetailLevel': 'ReturnAll',
                    'AllFeaturesForCategory': True
                }
                try:
                    response = ebay_api.execute('GetCategoryFeatures', call_data)
                except ConnectionError as e:
                    self.env['product.template']._manage_ebay_error(e)
                if 'ConditionValues' in response.dict()['Category']:
                    conditions = response.dict()['Category']['ConditionValues']['Condition']
                    if isinstance(conditions, list):
                        for condition in response.dict()['Category']['ConditionValues']['Condition']:
                            if not self.env['ebay.item.condition'].search([('code', '=', condition['ID'])]):
                                self.env['ebay.item.condition'].create({
                                    'code': condition['ID'],
                                    'name': condition['DisplayName']
                                })
                    else:
                        if not self.env['ebay.item.condition'].search([('code', '=', conditions['ID'])]):
                            self.env['ebay.item.condition'].create({
                                'code': conditions['ID'],
                                'name': conditions['DisplayName']
                            })
        categories = self.search([('leaf_category', '=', True)])
        for category in categories:
            name = category.name
            parent_id = category.category_parent_id
            while parent_id != 0:
                parent = self.search([
                    ('category_id', '=', parent_id),
                    ('category_type', '=', 'ebay')])
                name = parent.name + " > " + name
                parent_id = parent.category_parent_id
            category.name = name

    @api.model
    def sync_store_categories(self, ebay_api):
        try:
            response = ebay_api.execute('GetStore')
        except ConnectionError as e:
            self.env['product.template']._manage_ebay_error(e)
        categories = response.dict()['Store']['CustomCategories']['CustomCategory']
        if isinstance(categories, list):
            for category in categories:
                cat = self.search([
                    ('category_id', '=', int(category['CategoryID'])),
                    ('category_type', '=', 'store')])
                if not cat:
                    cat = self.create({
                        'category_id': category['CategoryID'],
                        'category_type': 'store'})
                cat.name = category['Name']
        else:
            cat = self.search([
                ('category_id', '=', int(categories['CategoryID'])),
                ('category_type', '=', 'store')])
            if not cat:
                cat = self.create({
                    'category_id': categories['CategoryID'],
                    'category_type': 'store'})
            cat.name = categories['Name']


class ebay_policy(models.Model):
    _name = 'ebay.policy'

    name = fields.Char('Name')
    policy_id = fields.Char('Policy ID')
    policy_type = fields.Char('Type')
    short_summary = fields.Text('Summary')

    @api.model
    def _cron_sync(self):
        try:
            self.sync_policies()
        except RedirectWarning:
            # not configured, ignore
            pass

    @api.model
    def sync_policies(self):
        domain = self.env['ir.config_parameter'].get_param('ebay_domain')
        ebay_api = self.env['product.template'].get_ebay_api(domain)
        try:
            response = ebay_api.execute('GetUserPreferences', {'ShowSellerProfilePreferences': True})
        except ConnectionError as e:
            self.env['product.template']._manage_ebay_error(e)
        if 'SellerProfilePreferences' not in response.dict() or \
           response.dict()['SellerProfilePreferences']['SupportedSellerProfiles'] is None:
                raise UserError(_('No Business Policies'))
        policies = response.dict()['SellerProfilePreferences']['SupportedSellerProfiles']['SupportedSellerProfile']
        if isinstance(policies, list):
            for policy in policies:
                record = self.search([('policy_id', '=', policy['ProfileID'])])
                if not record:
                    record = self.create({
                        'policy_id': policy['ProfileID'],
                    })
                record.write({
                    'name': policy['ProfileName'],
                    'policy_type': policy['ProfileType'],
                    'short_summary': policy['ShortSummary'] if 'ShortSummary' in policy else ' ',
                })
        else:
            record = self.search([('policy_id', '=', policies['ProfileID'])])
            if not record:
                self.create({
                    'policy_id': policies['ProfileID'],
                })
            record.write({
                'name': policies['ProfileName'],
                'policy_type': policies['ProfileType'],
                'short_summary': policies['ShortSummary'] if 'ShortSummary' in policies else ' ',
            })


class ebay_item_condition(models.Model):
    _name = 'ebay.item.condition'

    name = fields.Char('Name')
    code = fields.Integer('Code')

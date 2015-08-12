# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import Warning
from ebaysdk.exception import ConnectionError


class ebay_category(models.Model):
    _name = 'ebay.category'

    name = fields.Char('Name')
    # The IDS are string because of the limitation of the SQL integer range
    category_id = fields.Char('Category ID')
    category_parent_id = fields.Char('Category Parent ID')
    leaf_category = fields.Boolean(default=False)
    category_type = fields.Selection(
        [('ebay', 'Official eBay Category'), ('store', 'Custom Store Category')],
        string='Category Type',
    )
    # if we want relation between item condition and category
    # ebay_item_condition_ids = fields.Many2many(comodel_name='ebay.item.condition', string='Item Conditions')

    @api.model
    def sync_categories(self):
        domain = self.env['ir.config_parameter'].get_param('ebay_domain')
        prod = self.env['product.template']
        # First call to 'GetCategories' to only get the categories' version
        categories = prod.ebay_execute('GetCategories')
        ebay_version = categories.dict()['Version']
        version = self.env['ir.config_parameter'].get_param('ebay_sandbox_category_version'
                                                            if domain == 'sand'
                                                            else 'ebay_prod_category_version')
        if version != ebay_version:
            # If the version returned by eBay is different than the one in Odoo
            # Another call to 'GetCategories' with all the information (ReturnAll) is done
            self.env['ir.config_parameter'].set_param('ebay_sandbox_category_version'
                                                      if domain == 'sand'
                                                      else 'ebay_prod_category_version',
                                                      ebay_version)
            call_data = {
                'DetailLevel': 'ReturnAll',
                'LevelLimit': 4,
            }
            categories = prod.ebay_execute('GetCategories', call_data)
            self.create_categories(categories.dict()['CategoryArray']['Category'])
        self.sync_store_categories()

    @api.model
    def create_categories(self, categories):
        for category in categories:
            cat = self.search([
                ('category_id', '=', int(category['CategoryID'])),
                ('category_type', '=', 'ebay'),
            ])
            if not cat:
                cat = self.create({
                    'category_id': category['CategoryID'],
                    'category_type': 'ebay',
                })
            cat.write({
                'name': category['CategoryName'],
                'category_parent_id': category['CategoryParentID'] if category['CategoryID'] != category['CategoryParentID'] else 0,
                'leaf_category': category.get('LeafCategory'),
            })
            if category['CategoryLevel'] == '1':
                call_data = {
                    'CategoryID': category['CategoryID'],
                    'ViewAllNodes': True,
                    'DetailLevel': 'ReturnAll',
                    'AllFeaturesForCategory': True,
                }
                response = self.env['product.template'].ebay_execute('GetCategoryFeatures', call_data)
                if 'ConditionValues' in response.dict()['Category']:
                    conditions = response.dict()['Category']['ConditionValues']['Condition']
                    if not isinstance(conditions, list):
                        conditions = [conditions]
                    for condition in conditions:
                        if not self.env['ebay.item.condition'].search([('code', '=', condition['ID'])]):
                            self.env['ebay.item.condition'].create({
                                'code': condition['ID'],
                                'name': condition['DisplayName'],
                            })
                    # if we want relation between item condition and category
                    # cond = self.env['ebay.item.condition'].search([('code', '=', condition['ID'])])
                    # if cond:
                    #     cat.ebay_item_condition_ids = [(4, cond.id)]
                    # else:
                    #     cat.ebay_item_condition_ids = [(0, 0,{
                    #         'code': condition['ID'],
                    #         'name': condition['DisplayName'],
                    #     })]
        categories = self.search([('leaf_category', '=', True)])
        for category in categories:
            name = category.name
            parent_id = category.category_parent_id
            while parent_id != 0:
                parent = self.search([
                    ('category_id', '=', parent_id),
                    ('category_type', '=', 'ebay'),
                ])
                name = parent.name + " > " + name
                parent_id = parent.category_parent_id
            category.name = name

    @api.model
    def sync_store_categories(self):
        response = self.env['product.template'].ebay_execute('GetStore')
        categories = response.dict()['Store']['CustomCategories']['CustomCategory']
        if not isinstance(categories, list):
            categories = [categories]
        for category in categories:
            cat = self.search([
                ('category_id', '=', int(category['CategoryID'])),
                ('category_type', '=', 'store')])
            if not cat:
                cat = self.create({
                    'category_id': category['CategoryID'],
                    'category_type': 'store'})
            cat.name = category['Name']


class ebay_policy(models.Model):
    _name = 'ebay.policy'

    name = fields.Char('Name')
    policy_id = fields.Char('Policy ID')
    policy_type = fields.Char('Type')
    short_summary = fields.Text('Summary')

    @api.model
    def sync_policies(self):
        response = self.env['product.template'].ebay_execute('GetUserPreferences',
            {'ShowSellerProfilePreferences': True})
        if 'SellerProfilePreferences' not in response.dict() or \
           not response.dict()['SellerProfilePreferences']['SupportedSellerProfiles']:
                raise Warning(_('No Business Policies'))
        policies = response.dict()['SellerProfilePreferences']['SupportedSellerProfiles']['SupportedSellerProfile']
        if not isinstance(policies, list):
            policies = [policies]
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


class ebay_item_condition(models.Model):
    _name = 'ebay.item.condition'

    name = fields.Char('Name')
    code = fields.Integer('Code')
    # if we want relation between item condition and category
    # ebay_category_ids = fields.Many2many(comodel_name='ebay.category', string='Categories')

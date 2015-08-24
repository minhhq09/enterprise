from openerp import models, fields, api, _
from ebaysdk.trading import Connection as Trading
from ebaysdk.exception import ConnectionError
from pprint import pprint


class ebay_configuration(models.TransientModel):
    _name = 'sale.config.settings'
    _inherit = 'sale.config.settings'

    ebay_dev_id = fields.Char("Developer Key")
    ebay_sandbox_token = fields.Text("Sandbox Token")
    ebay_sandbox_app_id = fields.Char("Sandbox App Key")
    ebay_sandbox_cert_id = fields.Char("Sandbox Cert Key")

    ebay_prod_token = fields.Text("Production Token")
    ebay_prod_app_id = fields.Char("Production App Key")
    ebay_prod_cert_id = fields.Char("Production Cert Key")
    ebay_domain = fields.Selection([
        ('prod', 'Production'),
        ('sand', 'Sandbox'),
    ], string='eBay Site', default='sand', required=True)
    ebay_currency = fields.Many2one("res.currency", string='eBay Currency',
                                    domain=[('ebay_available', '=', True)], required=True)
    ebay_country = fields.Many2one("res.country", domain=[('ebay_available', '=', True)],
                                   string="Country Where The Products Are Stored")
    ebay_site = fields.Many2one("ebay.site", string="eBay Site Used")
    ebay_zip_code = fields.Char(string="Zip Code Where The Products Are Stored")
    ebay_out_of_stock = fields.Boolean("Use Out Of Stock Option", default=False)
    ebay_sales_team = fields.Many2one("crm.team", string="Sales Team")

    @api.multi
    def set_ebay(self):
        ebay_dev_id = self[0].ebay_dev_id or ''
        self.env['ir.config_parameter'].set_param('ebay_dev_id', ebay_dev_id)
        ebay_sales_team = self[0].ebay_sales_team or self.env['crm.team'].search([])[0]
        self.env['ir.config_parameter'].set_param('ebay_sales_team', ebay_sales_team.id)
        sandbox_token = self[0].ebay_sandbox_token or ''
        self.env['ir.config_parameter'].set_param('ebay_sandbox_token', sandbox_token)
        sandbox_app_id = self[0].ebay_sandbox_app_id or ''
        self.env['ir.config_parameter'].set_param('ebay_sandbox_app_id', sandbox_app_id)
        sandbox_cert_id = self[0].ebay_sandbox_cert_id or ''
        self.env['ir.config_parameter'].set_param('ebay_sandbox_cert_id', sandbox_cert_id)
        prod_token = self[0].ebay_prod_token or ''
        self.env['ir.config_parameter'].set_param('ebay_prod_token', prod_token)
        prod_app_id = self[0].ebay_prod_app_id or ''
        self.env['ir.config_parameter'].set_param('ebay_prod_app_id', prod_app_id)
        prod_cert_id = self[0].ebay_prod_cert_id or ''
        self.env['ir.config_parameter'].set_param('ebay_prod_cert_id', prod_cert_id)
        domain = self[0].ebay_domain or ''
        self.env['ir.config_parameter'].set_param('ebay_domain', domain)
        currency = self[0].ebay_currency or self.env['res.country'].search(
            [('ebay_available', '=', True)])[0]
        self.env['ir.config_parameter'].set_param('ebay_currency', currency.id)
        country = self[0].ebay_country or self.env['res.country'].search(
            [('ebay_available', '=', True)])[0]
        self.env['ir.config_parameter'].set_param('ebay_country', country.id)
        site = self[0].ebay_site or self.env['ebay.site'].search([])[0]
        self.env['ir.config_parameter'].set_param('ebay_site', site.id)
        zip_code = self[0].ebay_zip_code or ''
        self.env['ir.config_parameter'].set_param('ebay_zip_code', zip_code)
        out_of_stock = self[0].ebay_out_of_stock or ''
        if out_of_stock != self.env['ir.config_parameter'].get_param('ebay_out_of_stock'):
            self.env['ir.config_parameter'].set_param('ebay_out_of_stock', out_of_stock)

            if domain == 'sand':
                if sandbox_token and sandbox_cert_id and sandbox_app_id:
                    ebay_api = Trading(
                        domain='api.sandbox.ebay.com',
                        config_file=None,
                        appid=sandbox_app_id,
                        devid="ed74122e-6f71-4877-83d8-e0e2585bd78f",
                        certid=sandbox_cert_id,
                        token=sandbox_token,
                        siteid=site.ebay_id if site else 0)
                    call_data = {
                        'OutOfStockControlPreference': 'true' if out_of_stock else 'false',
                    }
                    try:
                        ebay_api.execute('SetUserPreferences', call_data)
                    except ConnectionError:
                        pass
            else:
                if prod_token and prod_cert_id and prod_app_id:
                    ebay_api = Trading(
                        domain='api.ebay.com',
                        config_file=None,
                        appid=prod_app_id,
                        devid="ed74122e-6f71-4877-83d8-e0e2585bd78f",
                        certid=prod_cert_id,
                        token=prod_token,
                        siteid=site.ebay_id if site else 0)
                    call_data = {
                        'OutOfStockControlPreference': 'true' if out_of_stock else 'false',
                    }
                    try:
                        ebay_api.execute('SetUserPreferences', call_data)
                    except ConnectionError:
                        pass

    @api.multi
    def get_default_ebay(self):
        params = self.env['ir.config_parameter']
        ebay_dev_id = params.get_param('ebay_dev_id', default='')
        ebay_sandbox_token = params.get_param('ebay_sandbox_token', default='')
        ebay_sandbox_app_id = params.get_param('ebay_sandbox_app_id', default='')
        ebay_sandbox_cert_id = params.get_param('ebay_sandbox_cert_id', default='')
        ebay_prod_token = params.get_param('ebay_prod_token', default='')
        ebay_prod_app_id = params.get_param('ebay_prod_app_id', default='')
        ebay_prod_cert_id = params.get_param('ebay_prod_cert_id', default='')
        ebay_domain = params.get_param('ebay_domain', default='sand')
        ebay_currency = int(params.get_param('ebay_currency', default=self.env.ref('base.USD')))
        ebay_country = int(params.get_param('ebay_country', default=self.env.ref('base.us')))
        ebay_site = int(params.get_param('ebay_site',
                        default=self.env['ebay.site'].search([])[0]))
        ebay_zip_code = params.get_param('ebay_zip_code')
        ebay_out_of_stock = params.get_param('ebay_out_of_stock', default=False)
        ebay_sales_team = int(params.get_param('ebay_sales_team',
                              default=self.env['crm.team'].search([])[0]))
        return {'ebay_dev_id': ebay_dev_id,
                'ebay_sandbox_token': ebay_sandbox_token,
                'ebay_sandbox_app_id': ebay_sandbox_app_id,
                'ebay_sandbox_cert_id': ebay_sandbox_cert_id,
                'ebay_prod_token': ebay_prod_token,
                'ebay_prod_app_id': ebay_prod_app_id,
                'ebay_prod_cert_id': ebay_prod_cert_id,
                'ebay_domain': ebay_domain,
                'ebay_currency': ebay_currency,
                'ebay_country': ebay_country,
                'ebay_site': ebay_site,
                'ebay_zip_code': ebay_zip_code,
                'ebay_out_of_stock': ebay_out_of_stock,
                'ebay_sales_team': ebay_sales_team,
                }

    @api.model
    def sync_categories(self, context=None):
        self.env['ebay.category'].sync_categories()

    @api.model
    def sync_policies(self, context=None):
        self.env['ebay.policy'].sync_policies()

    @api.multi
    def button_sync_product_status(self):
        self.env['product.template'].sync_ebay_products()

    @api.model
    def create_sale_order(self, product, transaction):
        if not self.env['sale.order'].search([
           ('client_order_ref', '=', transaction['OrderLineItemID'])]):
            partner = self.env['res.partner'].search([
                ('email', '=', transaction['Buyer']['Email'])])
            if not partner:
                partner_data = {
                    'name': transaction['Buyer']['UserID'],
                    'ebay_id': transaction['Buyer']['UserID'],
                    'email': transaction['Buyer']['Email'],
                    'ref': 'eBay',
                }
                if 'BuyerInfo' in transaction['Buyer'] and\
                   'ShippingAddress' in transaction['Buyer']['BuyerInfo']:
                    infos = transaction['Buyer']['BuyerInfo']['ShippingAddress']
                    partner_data['name'] = infos['Name'] if 'Name' in infos else False
                    partner_data['street'] = infos['Street1'] if 'Street1' in infos else False
                    partner_data['city'] = infos['CityName'] if 'CityName' in infos else False
                    partner_data['zip'] = infos['PostalCode'] if 'PostalCode' in infos else False
                    partner_data['phone'] = infos['Phone'] if 'Phone' in infos else False
                    partner_data['country_id'] = self.env['res.country'].search([
                        ('code', '=', infos['Country'])
                    ]).id

                partner = self.env['res.partner'].create(partner_data)
            if product.product_variant_count > 1 and 'Variation' in transaction:
                variant = product.product_variant_ids.filtered('ebay_published')
                variant = variant.filtered(lambda l:
                   l.ebay_variant_url.split("vti", 1)[1] ==
                   transaction['Variation']['VariationViewItemURL'].split("vti", 1)[1])
            else:
                variant = product.product_variant_ids[0]
            if not product.ebay_sync_stock:
                variant.write({
                    'ebay_quantity_sold': int(transaction['QuantityPurchased']),
                    'ebay_quantity': variant.ebay_quantity - int(transaction['QuantityPurchased']),
                    })
            else:
                variant.ebay_quantity_sold = int(transaction['QuantityPurchased'])
            sale_order = self.env['sale.order'].create({
                'partner_id': partner.id,
                'state': 'draft',
                'client_order_ref': transaction['OrderLineItemID']
            })
            if self.env['ir.config_parameter'].get_param('ebay_sales_team'):
                sale_order.team_id = int(self.env['ir.config_parameter'].get_param('ebay_sales_team'))
            if 'BuyerCheckoutMessage' in transaction:
                sale_order.message_post(_('The Buyer posted :') + transaction['BuyerCheckoutMessage'])

            currency = self.env['res.currency'].search([
                ('name', '=', transaction['TransactionPrice']['_currencyID'])])
            self.env['sale.order.line'].create({
                'product_id': variant.id,
                'order_id': sale_order.id,
                'name': product.name,
                'product_uom_qty': float(transaction['QuantityPurchased']),
                'price_unit': currency.compute(
                    float(transaction['TransactionPrice']['value']),
                    self.env.user.company_id.currency_id),
            })
            if 'ShippingServiceSelected' in transaction:
                self.env['sale.order.line'].create({
                    'order_id': sale_order.id,
                    'name': transaction['ShippingServiceSelected']['ShippingService'],
                    'product_uom_qty': 1,
                    'price_unit': currency.compute(
                        float(transaction['ShippingServiceSelected']['ShippingServiceCost']['value']),
                        self.env.user.company_id.currency_id)
                    })
            sale_order.action_button_confirm()

            invoice_id = sale_order.action_invoice_create()
            invoice = self.env['account.invoice'].browse(invoice_id)
            invoice.invoice_validate()

    @api.model
    def check_available_qty(self):
        products = self.env['product.template'].search([
            ('ebay_published', '=', True),
            ('ebay_sync_stock', '=', True),
            ('ebay_listing_status', '=', 'Active'),
            ('virtual_available', '<=', 0)])
        if products:
            if self.env['ir.config_parameter'].get_param('ebay_out_of_stock'):
                products.mapped(lambda p: p.revise_product_ebay())
            else:
                products.mapped(lambda p: p.end_listing_product_ebay())
            products.ebay_listing_status = 'Out Of Stock'
        products = self.env['product.template'].search([
            ('ebay_published', '=', True),
            ('ebay_sync_stock', '=', True),
            ('ebay_listing_status', '=', 'Out Of Stock'),
            ('virtual_available', '>', 0)])
        if products:
            if self.env['ir.config_parameter'].get_param('ebay_out_of_stock'):
                products.mapped(lambda p: p.revise_product_ebay())
            else:
                products.mapped(lambda p: p.relist_product_ebay())
        products = self.env['product.template'].search([
            ('ebay_published', '=', True),
            ('ebay_sync_stock', '=', True),
            ('ebay_listing_status', '=', 'Active'),
            ('virtual_available', '>', 0),
            ('ebay_use_variant', '=', False)])
        if products:
            map(lambda p: p.revise_product_ebay(), [p for p in products if p.ebay_quantity != p.virtual_available])
        products = self.env['product.template'].search([
            ('ebay_published', '=', True),
            ('ebay_sync_stock', '=', True),
            ('ebay_listing_status', '=', 'Active'),
            ('virtual_available', '>', 0),
            ('ebay_use_variant', '=', True)])
        if products:
            for product in products:
                for variant in product.product_variant_ids:
                    if variant.virtual_available != variant.ebay_quantity:
                        product.revise_product_ebay()
                        break

    @api.model
    def sync_ebay_details(self, context=None):
        domain = self.env['ir.config_parameter'].get_param('ebay_domain')
        ebay_api = self.env['product.template'].get_ebay_api(domain)
        call_data = {
            'DetailName': ['CountryDetails', 'SiteDetails', 'CurrencyDetails'],
        }
        try:
            response = ebay_api.execute('GeteBayDetails', call_data)
        except ConnectionError as e:
            self.env['product.template']._manage_ebay_error(e)
        for country in self.env['res.country'].search([('ebay_available', '=', True)]):
            country.ebay_available = False
        for country in response.dict()['CountryDetails']:
            record = self.env['res.country'].search([('code', '=', country['Country'])])
            if record:
                record.ebay_available = True
        for currency in self.env['res.currency'].search([('ebay_available', '=', True)]):
            currency.ebay_available = False
        for currency in response.dict()['CurrencyDetails']:
            record = self.env['res.currency'].search([('name', '=', currency['Currency'])])
            if record:
                record.ebay_available = True
        for site in response.dict()['SiteDetails']:
            record = self.env['ebay.site'].search([('ebay_id', '=', site['SiteID'])])
            if not record:
                record = self.env['ebay.site'].create({
                    'name': site['Site'],
                    'ebay_id': site['SiteID']
                })
            else:
                record.name = site['Site']

class country(models.Model):
    _inherit = "res.country"

    ebay_available = fields.Boolean("Availability To Use For eBay API")


class currency(models.Model):
    _inherit = "res.currency"

    ebay_available = fields.Boolean("Availability To Use For eBay API")


class ebay_site(models.Model):
    _name = "ebay.site"

    name = fields.Char("Name")
    ebay_id = fields.Char("eBay ID")

# MULTI ACCOUNT DRAFT 
#class ebay_config_settings(models.Model):
#     _name = 'ebay.config.settings'

#     name = fields.Char("Account Name")
#     active = fields.Boolean("Active", default=True)
#     ebay_domain = fields.Selection([
#         ('prod', 'Production'),
#         ('sand', 'Sandbox'),
#     ], string='eBay Site', default='sand', required=True)
#     ebay_token = fields.Text("Token")
#     ebay_app_id = fields.Char("App ID")
#     ebay_cert_id = fields.Char("Cert ID")
#     ebay_currency = fields.Selection([
#         ('USD', 'US Dollar'),
#         ('CAD', 'Canadian Dollar'),
#         ('GBP', 'British Pound'),
#         ('AUD', 'Australian Dollar'),
#         ('EUR', 'Euro'),
#         ('CHF', 'Swiss Franc'),
#         ('CNY', 'Chinese Renminbi'),
#         ('HKD', 'Hong Kong Dollar'),
#         ('PHP', 'Philippines Peso'),
#         ('PLN', 'Polish Zloty'),
#         ('SEK', 'Sweden Krona'),
#         ('SGD', 'Singapore Dollar'),
#         ('TWD', 'Taiwanese Dollar'),
#         ('INR', 'Indian Rupee'),
#         ('MYR', 'Malaysian Ringgit'),
#     ], string='eBay Currency', default='USD', required=True)
#     ebay_country = fields.Char(string="Country Code Where The Products Are Stored")
#     ebay_zip_code = fields.Char(string="Zip Code Where The Products Are Stored")
#     ebay_out_of_stock = fields.Boolean("Out Of Stock Option", default=False)

#     @api.multi
#     def get_ebay_api(self):
#         appid = self.ebay_app_id
#         certid = self.ebay_cert_id
#         token = self.ebay_token
#         if self.ebay_domain == 'sand':
#             domain = 'api.sandbox.ebay.com'
#         else:
#             domain = 'api.ebay.com'

#         if not appid or not certid or not token:
#             action = self.env.ref('sale_ebay.action_ebay_configuration')
#             raise RedirectWarning(_('One parameter is missing.'), action.id, _('Configure The eBay Integrator Now'))

#         return Trading(domain=domain,
#                        config_file=None,
#                        appid=appid,
#                        devid="ed74122e-6f71-4877-83d8-e0e2585bd78f",
#                        certid=certid,
#                        token=token)

#     @api.model
#     def sync_categories(self, context=None):
#         import ipdb;ipdb.set_trace()
#         self.env['ebay.category'].sync_categories(api)

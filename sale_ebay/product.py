# -*- coding: utf-8 -*-

import base64
from openerp import models, fields, api, _
from datetime import datetime, timedelta
from openerp.exceptions import UserError, RedirectWarning
from ebaysdk.trading import Connection as Trading
from ebaysdk.exception import ConnectionError
from StringIO import StringIO
from xml.sax.saxutils import escape
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT


class product_template(models.Model):
    _inherit = "product.template"

    ebay_id = fields.Char('eBay ID')
    ebay_use = fields.Boolean('Use eBay', default=False)
    ebay_url = fields.Char('eBay url', readonly=True)
    ebay_listing_status = fields.Char('eBay Status', default='Unlisted', readonly=True)
    ebay_title = fields.Char('Title', size=80,
        help='The title is restricted to 80 characters')
    ebay_subtitle = fields.Char('Subtitle', size=55,
        help='The subtitle is restricted to 55 characters. Fees can be claimed by eBay for this feature')
    ebay_description = fields.Text('Description')
    ebay_item_condition_id = fields.Many2one('ebay.item.condition', string="Item Condition")
    ebay_category_id = fields.Many2one('ebay.category',
        string="Category", domain=[('category_type', '=', 'ebay'),('leaf_category','=',True)])
    ebay_store_category_id = fields.Many2one('ebay.category',
        string="Store Category", domain=[('category_type', '=', 'store'),('leaf_category','=',True)])
    ebay_store_category_2_id = fields.Many2one('ebay.category',
        string="Store Category 2", domain=[('category_type', '=', 'store'),('leaf_category','=',True)])
    ebay_price = fields.Float(string='Starting Price for Auction')
    ebay_buy_it_now_price = fields.Float(string='Buy It Now Price')
    ebay_listing_type = fields.Selection([
        ('Chinese', 'Auction'),
        ('FixedPriceItem', 'Fixed price')], string='Listing Type', default='Chinese')
    ebay_listing_duration = fields.Selection([
        ('Days_3', '3 Days'),
        ('Days_5', '5 Days'),
        ('Days_7', '7 Days'),
        ('Days_10', '10 Days'),
        ('Days_30', '30 Days (only for fixed price)'),
        ('GTC', 'Good \'Til Cancelled (only for fixed price)')],
        string='Duration', default='Days_7')
    ebay_seller_payment_policy_id = fields.Many2one('ebay.policy',
        string="Payment Policy", domain=[('policy_type', '=', 'PAYMENT')])
    ebay_seller_return_policy_id = fields.Many2one('ebay.policy',
        string="Return Policy", domain=[('policy_type', '=', 'RETURN_POLICY')])
    ebay_seller_shipping_policy_id = fields.Many2one('ebay.policy',
        string="Shipping Policy", domain=[('policy_type', '=', 'SHIPPING')])
    ebay_sync_stock = fields.Boolean(string="Use The Stock's Quantity", default=False)
    ebay_best_offer = fields.Boolean(string="Allow Best Offer", default=False)
    ebay_private_listing = fields.Boolean(string="Private Listing", default=False)
    ebay_start_date = fields.Datetime('Start Date', readonly=1)
    ebay_quantity_sold = fields.Integer(related='product_variant_ids.ebay_quantity_sold', store=True)
    ebay_fixed_price = fields.Float(related='product_variant_ids.ebay_fixed_price', store=True)
    ebay_quantity = fields.Integer(related='product_variant_ids.ebay_quantity', store=True)

    @api.multi
    def _prepare_item_dict(self):
        if self.ebay_sync_stock:
            self.ebay_quantity = max(int(self.virtual_available), 0)
        country_id = self.env['ir.config_parameter'].get_param('ebay_country')
        country = self.env['res.country'].browse(int(country_id))
        currency_id = self.env['ir.config_parameter'].get_param('ebay_currency')
        currency = self.env['res.currency'].browse(int(currency_id))
        item = {
            "Item": {
                "Title": self._ebay_encode(self.ebay_title),
                "PrimaryCategory": {"CategoryID": self.ebay_category_id.category_id},
                "StartPrice": self.ebay_price if self.ebay_listing_type == 'Chinese' else self.ebay_fixed_price,
                "CategoryMappingAllowed": "true",
                "Country": country.code,
                "Currency": currency.name,
                "ConditionID": self.ebay_item_condition_id.code,
                "ListingDuration": self.ebay_listing_duration,
                "ListingType": self.ebay_listing_type,
                "PostalCode": self.env['ir.config_parameter'].get_param('ebay_zip_code'),
                "Location": self.env['ir.config_parameter'].get_param('ebay_location'),
                "Quantity": self.ebay_quantity,
                "BestOfferDetails": {'BestOfferEnabled': self.ebay_best_offer},
                "PrivateListing": self.ebay_private_listing,
                "SellerProfiles": {
                    "SellerPaymentProfile": {
                        "PaymentProfileID": self.ebay_seller_payment_policy_id.policy_id,
                    },
                    "SellerReturnProfile": {
                        "ReturnProfileID": self.ebay_seller_return_policy_id.policy_id,
                    },
                    "SellerShippingProfile": {
                        "ShippingProfileID": self.ebay_seller_shipping_policy_id.policy_id,
                    }
                },
            }
        }
        if self.ebay_description and '<html>' in self.ebay_description:
            item['Item']['Description'] = '<![CDATA['+self.ebay_description+']]>'
        else:
            item['Item']['Description'] = self._ebay_encode(self.ebay_description)
        if self.ebay_subtitle:
            item['Item']['SubTitle'] = self._ebay_encode(self.ebay_subtitle)
        picture_urls = self._create_picture_url()
        if picture_urls:
            item['Item']['PictureDetails'] = {'PictureURL': picture_urls}
        if self.ebay_listing_type == 'Chinese' and self.ebay_buy_it_now_price:
            item['Item']['BuyItNowPrice'] = self.ebay_buy_it_now_price
        NameValueList = []
        variant = self.product_variant_ids.filtered('ebay_use')
        # If only one variant selected to be published, we don't create variant
        # but set the variant's value has an item specific on eBay
        if len(variant) == 1 \
           and self.ebay_listing_type == 'FixedPriceItem':
            for spec in variant.attribute_value_ids:
                NameValueList.append({
                    'Name': self._ebay_encode(spec.attribute_id.name),
                    'Value': self._ebay_encode(spec.name),
                })
            item['Item']['Quantity'] = variant.ebay_quantity
            item['Item']['StartPrice'] = variant.ebay_fixed_price
        # If one attribute has only one value, we don't create variant
        # but set the value has an item specific on eBay
        elif self.attribute_line_ids:
            for attribute in self.attribute_line_ids:
                if len(attribute.value_ids) == 1:
                    NameValueList.append({
                        'Name': self._ebay_encode(attribute.attribute_id.name),
                        'Value': self._ebay_encode(attribute.value_ids.name),
                    })
        if NameValueList:
            item['Item']['ItemSpecifics'] = {'NameValueList': NameValueList}
        if self.ebay_store_category_id:
            item['Item']['Storefront'] = {
                'StoreCategoryID': self.ebay_store_category_id.id,
                'StoreCategoryName': self._ebay_encode(self.ebay_store_category_id.name),
            }
            if self.ebay_store_category_2_id:
                item['Item']['Storefront']['StoreCategory2ID'] = self.ebay_store_category_2_id.id
                item['Item']['Storefront']['StoreCategory2Name'] = self._ebay_encode(self.ebay_store_category_2_id.name)
        return item

    @api.model
    def _ebay_encode(self, string):
        return escape(string.strip().encode('utf-8')) if string else ''

    @api.multi
    def _prepare_variant_dict(self):
        if not self.product_variant_ids.filtered('ebay_use'):
            raise UserError(_('No Variant Set To Be Published On eBay'))
        items = self._prepare_item_dict()
        items['Item']['Variations'] = {'Variation': []}
        variations = items['Item']['Variations']['Variation']
        possible_name_values = []
        # example of a valid name value list array
        # possible_name_values = [{'Name':'size','Value':['16gb','32gb']},{'Name':'color', 'Value':['red','blue']}]
        for variant in self.product_variant_ids.filtered('ebay_use'):
            if self.ebay_sync_stock:
                variant.ebay_quantity = int(variant.virtual_available)
            if not variant.ebay_quantity and\
               not self.env['ir.config_parameter'].get_param('ebay_out_of_stock'):
                raise UserError(_('All the quantities must be greater than 0 or you need to enable the Out Of Stock option.'))
            variant_name_values = []
            for spec in variant.attribute_value_ids:
                if len(spec.attribute_id.value_ids) > 1:
                    if not filter(
                        lambda x:
                        x['Name'] == self._ebay_encode(spec.attribute_id.name),
                            possible_name_values):
                        possible_name_values.append({
                            'Name': self._ebay_encode(spec.attribute_id.name),
                            'Value': [self._ebay_encode(n) for n in spec.attribute_id.value_ids.mapped('name')],
                        })
                    variant_name_values.append({
                        'Name': self._ebay_encode(spec.attribute_id.name),
                        'Value': self._ebay_encode(spec.name),
                        })
            variations.append({
                'Quantity': variant.ebay_quantity,
                'StartPrice': variant.ebay_fixed_price,
                'VariationSpecifics': {'NameValueList': variant_name_values},
                })
        items['Item']['Variations']['VariationSpecificsSet'] = {
            'NameValueList': possible_name_values
        }
        return items

    @api.multi
    def _get_item_dict(self):
        if self.product_variant_count > 1 and not self.product_variant_ids.filtered('ebay_use'):
            raise UserError(_("Error Encountered.\n No Variant Set To Be Listed On eBay."))
        if len(self.product_variant_ids.filtered('ebay_use')) > 1 \
           and self.ebay_listing_type == 'FixedPriceItem':
            item_dict = self._prepare_variant_dict()
        else:
            item_dict = self._prepare_item_dict()
        return item_dict

    @api.one
    def _set_variant_url(self, item_id):
        variants = self.product_variant_ids.filtered('ebay_use')
        if len(variants) > 1 and self.ebay_listing_type == 'FixedPriceItem':
            for variant in variants:
                name_value_list = [{
                    'Name': self._ebay_encode(spec.attribute_id.name),
                    'Value': self._ebay_encode(spec.name)
                } for spec in variant.attribute_value_ids]
                call_data = {
                    'ItemID': item_id,
                    'VariationSpecifics': {
                        'NameValueList': name_value_list
                    }
                }
                item = self.ebay_execute('GetItem', call_data)
                variant.ebay_variant_url = item.dict()['Item']['ListingDetails']['ViewItemURL']

    @api.model
    def get_ebay_api(self, domain):
        dev_id = self.env['ir.config_parameter'].get_param('ebay_dev_id')
        site_id = self.env['ir.config_parameter'].get_param('ebay_site')
        site = self.env['ebay.site'].browse(int(site_id))
        if domain == 'sand':
            app_id = self.env['ir.config_parameter'].get_param('ebay_sandbox_app_id')
            cert_id = self.env['ir.config_parameter'].get_param('ebay_sandbox_cert_id')
            token = self.env['ir.config_parameter'].get_param('ebay_sandbox_token')
            domain = 'api.sandbox.ebay.com'
        else:
            app_id = self.env['ir.config_parameter'].get_param('ebay_prod_app_id')
            cert_id = self.env['ir.config_parameter'].get_param('ebay_prod_cert_id')
            token = self.env['ir.config_parameter'].get_param('ebay_prod_token')
            domain = 'api.ebay.com'

        if not app_id or not cert_id or not token:
            action = self.env.ref('base_setup.action_sale_config')
            raise RedirectWarning(_('One parameter is missing.'),
                                  action.id, _('Configure The eBay Integrator Now'))

        return Trading(domain=domain,
                       config_file=None,
                       appid=app_id,
                       devid=dev_id,
                       certid=cert_id,
                       token=token,
                       siteid=int(site.ebay_id))

    @api.model
    def ebay_execute(self, verb, data=None, list_nodes=[], verb_attrs=None, files=None):
        domain = self.env['ir.config_parameter'].get_param('ebay_domain')
        ebay_api = self.get_ebay_api(domain)
        try:
            return ebay_api.execute(verb, data, list_nodes, verb_attrs, files)
        except ConnectionError as e:
            self._handle_ebay_error(e)

    @api.multi
    def _create_picture_url(self):
        attachments = self.env['ir.attachment'].search([('res_model', '=', 'product.template'),
                                                        ('res_id', '=', self.id)])
        urls = []
        for att in attachments:
            image = StringIO(base64.standard_b64decode(att["datas"]))
            files = {'file': ('EbayImage', image)}
            pictureData = {
                "WarningLevel": "High",
                "PictureName": self.name
            }
            response = self.ebay_execute('UploadSiteHostedPictures', pictureData, files=files)
            urls.append(response.dict()['SiteHostedPictureDetails']['FullURL'])
        return urls

    @api.one
    def _update_ebay_data(self, response):
        domain = self.env['ir.config_parameter'].get_param('ebay_domain')
        response_url = self.ebay_execute('GetItem', {'ItemID': response['ItemID']})
        self.write({
            'ebay_listing_status': 'Active',
            'ebay_id': response['ItemID'],
            'ebay_url': response_url.dict()['Item']['ListingDetails']['ViewItemURL'],
            'ebay_start_date': datetime.strptime(response['StartTime'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
        })

    @api.one
    def push_product_ebay(self):
        item_dict = self._get_item_dict()
        response = self.ebay_execute('AddItem' if self.ebay_listing_type == 'Chinese'
                                     else 'AddFixedPriceItem', item_dict)
        self._set_variant_url(response.dict()['ItemID'])
        self._update_ebay_data(response.dict())

    @api.one
    def end_listing_product_ebay(self):
        call_data = {"ItemID": self.ebay_id,
                     "EndingReason": "NotAvailable"}
        self.ebay_execute('EndItem' if self.ebay_listing_type == 'Chinese'
                          else 'EndFixedPriceItem', call_data)
        self.sync_product_status()

    @api.one
    def relist_product_ebay(self):
        item_dict = self._get_item_dict()
        # set the item id to relist the correct ebay listing
        item_dict['Item']['ItemID'] = self.ebay_id
        response = self.ebay_execute('RelistItem' if self.ebay_listing_type == 'Chinese'
                                     else 'RelistFixedPriceItem', item_dict)
        self._set_variant_url(response.dict()['ItemID'])
        self._update_ebay_data(response.dict())

    @api.one
    def revise_product_ebay(self):
        item_dict = self._get_item_dict()
        # set the item id to revise the correct ebay listing
        item_dict['Item']['ItemID'] = self.ebay_id
        if not self.ebay_subtitle:
            item_dict['DeletedField'] = 'Item.SubTitle'
        response = self.ebay_execute('ReviseItem' if self.ebay_listing_type == 'Chinese'
                                     else 'ReviseFixedPriceItem', item_dict)
        self._set_variant_url(response.dict()['ItemID'])
        self._update_ebay_data(response.dict())

    @api.model
    def sync_product_status(self):
        self._sync_recent_product_status(1)
        self._sync_old_product_status()

    @api.model
    def _sync_recent_product_status(self, page_number=1):
        call_data = {'StartTimeFrom': str(datetime.today()-timedelta(days=119)),
                     'StartTimeTo': str(datetime.today()),
                     'DetailLevel': 'ReturnAll',
                     'Pagination': {'EntriesPerPage': 200,
                                    'PageNumber': page_number,
                                    }
                     }
        response = self.ebay_execute('GetSellerList', call_data)
        if response.dict()['ItemArray'] is None:
            return
        for item in response.dict()['ItemArray']['Item']:
            product = self.search([('ebay_id', '=', item['ItemID'])])
            if product:
                product._sync_transaction(item)
        if page_number < int(response.dict()['PaginationResult']['TotalNumberOfPages']):
            self._sync_product_status(page_number + 1)

    @api.model
    def _sync_old_product_status(self):
        date = (datetime.today()-timedelta(days=119)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        products = self.search([('ebay_start_date', '<', date), ('ebay_listing_status', '=', 'Active')])
        for product in products:
            response = self.ebay_execute('GetItem', {'ItemID': product.ebay_id})
            product._sync_transaction(response.dict()['Item'])
        return

    @api.one
    def _sync_transaction(self, item):
        if self.ebay_listing_status != 'Ended'\
           and self.ebay_listing_status != 'Out Of Stock':
            self.ebay_listing_status = item['SellingStatus']['ListingStatus']
            if int(item['SellingStatus']['QuantitySold']) > 0:
                resp = self.ebay_execute('GetItemTransactions', {'ItemID': item['ItemID']}).dict()
                if 'TransactionArray' in resp:
                    transactions = resp['TransactionArray']['Transaction']
                    if not isinstance(transactions, list):
                        transactions = [transactions]
                    for transaction in transactions:
                        if transaction['Status']['CheckoutStatus'] == 'CheckoutComplete':
                            self.create_sale_order(transaction)
        self.sync_available_qty()

    @api.one
    def create_sale_order(self, transaction):
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
                    partner_data['name'] = infos.get('Name')
                    partner_data['street'] = infos.get('Street1')
                    partner_data['city'] = infos.get('CityName')
                    partner_data['zip'] = infos.get('PostalCode')
                    partner_data['phone'] = infos.get('Phone')
                    partner_data['country_id'] = self.env['res.country'].search([
                        ('code', '=', infos['Country'])
                    ]).id
                    partner_data['state_id'] = self.env['res.country.state'].search([
                        ('name', '=', infos.get('StateOrProvince')),
                        ('country_id', '=', partner_data['country_id'])
                    ]).id
                partner = self.env['res.partner'].create(partner_data)
            if self.product_variant_count > 1 and 'Variation' in transaction:
                variant = self.product_variant_ids.filtered(lambda l:
                    l.ebay_use and
                    l.ebay_variant_url.split("vti", 1)[1] ==
                    transaction['Variation']['VariationViewItemURL'].split("vti", 1)[1])
            else:
                variant = self.product_variant_ids[0]
            if not self.ebay_sync_stock:
                variant.write({
                    'ebay_quantity_sold': variant.ebay_quantity_sold + int(transaction['QuantityPurchased']),
                    'ebay_quantity': variant.ebay_quantity - int(transaction['QuantityPurchased']),
                    })
            else:
                variant.ebay_quantity_sold = variant.ebay_quantity_sold + int(transaction['QuantityPurchased'])
            sale_order = self.env['sale.order'].create({
                'partner_id': partner.id,
                'state': 'draft',
                'client_order_ref': transaction['OrderLineItemID']
            })
            if self.env['ir.config_parameter'].get_param('ebay_sales_team'):
                sale_order.team_id = int(self.env['ir.config_parameter'].get_param('ebay_sales_team'))

            currency = self.env['res.currency'].search([
                ('name', '=', transaction['TransactionPrice']['_currencyID'])])
            self.env['sale.order.line'].create({
                'product_id': variant.id,
                'order_id': sale_order.id,
                'name': self.name,
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
            if 'BuyerCheckoutMessage' in transaction:
                sale_order.message_post(_('The Buyer posted :\n') + transaction['BuyerCheckoutMessage'])
                sale_order.picking_ids.message_post(_('The Buyer posted :\n') + transaction['BuyerCheckoutMessage'])
            invoice_id = sale_order.action_invoice_create()
            invoice = self.env['account.invoice'].browse(invoice_id)
            invoice.invoice_validate()

    @api.one
    def sync_available_qty(self):
        if self.ebay_use and self.ebay_sync_stock:
            if self.ebay_listing_status == 'Active':
                # The product is Active on eBay but there is no more stock
                if self.virtual_available <= 0:
                    # If the Out Of Stock option is enabled only need to revise the quantity
                    if self.env['ir.config_parameter'].get_param('ebay_out_of_stock'):
                        self.revise_product_ebay()
                    else:
                        self.end_listing_product_ebay()
                    self.ebay_listing_status = 'Out Of Stock'
                # The product is Active on eBay and there is some stock
                # Check if the quantity in Odoo is different than the one on eBay
                # If it is the case revise the quantity
                else:
                    if len(self.product_variant_ids.filtered('ebay_use')) > 1:
                        for variant in self.product_variant_ids:
                            if variant.virtual_available != variant.ebay_quantity:
                                self.revise_product_ebay()
                                break
                    else:
                        if self.ebay_quantity != self.virtual_available:
                            self.revise_product_ebay
            elif self.ebay_listing_status == 'Out Of Stock':
                # The product is Out Of Stock on eBay but there is stock in Odoo
                # If the Out Of Stock option is enabled then only revise the product
                if self.virtual_available > 0:
                    if self.env['ir.config_parameter'].get_param('ebay_out_of_stock'):
                        self.revise_product_ebay()
                    else:
                        self.relist_product_ebay()

    @api.model
    def _handle_ebay_error(self, connectionError):
        errors = connectionError.response.dict()['Errors']
        if not isinstance(errors, list):
            errors = [errors]
        error_message = ''
        for error in errors:
            if error['SeverityCode'] == 'Error':
                error_message += error['LongMessage']
        if 'Condition is required for this category.' in error_message:
            error_message += 'Or the condition is not compatible with the category.'
        if 'Internal error to the application' in error_message:
            error_message = 'eBay is unreachable. Please try again later.'
        if 'Invalid Multi-SKU item id supplied with variations' in error_message:
            error_message = 'Impossible to revise a listing into a multi-variations listing.\n Create a new listing.'
        raise UserError(_("Error Encountered.\n'%s'") % (error_message,))


class product_product(models.Model):
    _inherit = "product.product"

    ebay_use = fields.Boolean('Publish On eBay', default=False)
    ebay_quantity_sold = fields.Integer('Quantity Sold', readonly=True)
    ebay_fixed_price = fields.Float('Fixed Price')
    ebay_quantity = fields.Integer(string='Quantity', default=1)
    ebay_listing_type = fields.Selection(related='product_tmpl_id.ebay_listing_type')
    ebay_variant_url = fields.Char('eBay Variant URL')

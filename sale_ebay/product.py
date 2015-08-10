# -*- coding: utf-8 -*-

import base64

from openerp import models, fields, api, _
from openerp.exceptions import UserError, RedirectWarning
from ebaysdk.trading import Connection as Trading
from ebaysdk.exception import ConnectionError
from StringIO import StringIO
from xml.sax.saxutils import escape
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


class product_template(models.Model):
    _inherit = "product.template"

    ebay_id = fields.Char('eBay ID')
    ebay_published = fields.Boolean('Publish On eBay', default=False)
    ebay_url = fields.Char('eBay url', readonly=True)
    ebay_listing_status = fields.Char('eBay Status', default='Unlisted', readonly=True)
    ebay_title = fields.Char('Title', size=80,
        help='The title is restricted to 80 characters')
    ebay_subtitle = fields.Char('Subtitle', size=55,
        help='The subtitle is restricted to 55 characters. Fees can be claimed by eBay for this feature')
    ebay_description = fields.Text('Description', default=' ')
    ebay_item_condition_id = fields.Many2one('ebay.item.condition', string="Item Condition")
    ebay_category_id = fields.Many2one('ebay.category',
        string="Category", domain=[('category_type', '=', 'ebay')])
    ebay_store_category_id = fields.Many2one('ebay.category',
        string="Store Category", domain=[('category_type', '=', 'store')])
    ebay_store_category_2_id = fields.Many2one('ebay.category',
        string="Store Category 2", domain=[('category_type', '=', 'store')])
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
    ebay_use_variant = fields.Boolean('Use Multiple Variations Listing')
    ebay_quantity_sold = fields.Integer(related='product_variant_ids.ebay_quantity_sold', store=True)
    ebay_fixed_price = fields.Float(related='product_variant_ids.ebay_fixed_price', store=True)
    ebay_quantity = fields.Integer(related='product_variant_ids.ebay_quantity', store=True)
    ebay_sync_stock = fields.Boolean(string="Use The Stock's Quantity", default=False)
    ebay_best_offer = fields.Boolean(string="Allow Best Offer", default=False)
    ebay_private_listing = fields.Boolean(string="Private Listing", default=False)

    @api.multi
    def _prepare_item_dict(self, picture_urls):
        if self.ebay_sync_stock:
            self.ebay_quantity = max(int(self.virtual_available), 0)
        country_id = self.env['ir.config_parameter'].get_param('ebay_country')
        country = self.env['res.country'].browse(int(country_id))
        currency_id = self.env['ir.config_parameter'].get_param('ebay_currency')
        currency = self.env['res.currency'].browse(int(currency_id))
        item = {
            "Item": {
                "Title": escape(self.ebay_title.strip().encode('utf-8')),
                "PrimaryCategory": {"CategoryID": self.ebay_category_id.category_id},
                "StartPrice": self.ebay_price if self.ebay_listing_type == 'Chinese' else self.ebay_fixed_price,
                "CategoryMappingAllowed": "true",
                "Country": country.code,
                "Currency": currency.name,
                "ConditionID": self.ebay_item_condition_id.code,
                "ListingDuration": self.ebay_listing_duration,
                "ListingType": self.ebay_listing_type,
                "PostalCode": self.env['ir.config_parameter'].get_param('ebay_zip_code'),
                "Quantity": self.ebay_quantity,
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
                #TODO ONLY FOR TEST PURPOSE
                # "DispatchTimeMax": "3",
                # "PaymentMethods": "PayPal",
                # "PayPalEmailAddress": "tkeefdddder@gmail.com",
                # "ReturnPolicy": {
                #     "ReturnsAcceptedOption": "ReturnsAccepted",
                #     "RefundOption": "MoneyBack",
                #     "ReturnsWithinOption": "Days_30",
                #     "Description": "If you are not satisfied, return the book for refund.",
                #     "ShippingCostPaidByOption": "Buyer"
                # },
                # "ShippingDetails": {
                #     "ShippingType": "Flat",
                #     "ShippingServiceOptions": {
                #         "ShippingServicePriority": "1",
                #         "ShippingService": "USPSMedia",
                #         "ShippingServiceCost": "2.50"
                #     }
                # },
            }
        }
        if self.ebay_description and '<html>' in self.ebay_description:
            item['Item']['Description'] = '<![CDATA['+self.ebay_description+']]>'
        else:
            item['Item']['Description'] = escape(self.ebay_description.strip().encode('utf-8'))
        if self.ebay_subtitle:
            item['Item']['SubTitle'] = escape(self.ebay_subtitle.strip().encode('utf-8'))
        if picture_urls:
            item['Item']['PictureDetails'] = {'PictureURL': picture_urls}
        if self.ebay_listing_type == 'Chinese' and self.ebay_buy_it_now_price:
            item['Item']['BuyItNowPrice'] = self.ebay_buy_it_now_price
        if self.attribute_line_ids:
            NameValueList = []
            for attribute in self.attribute_line_ids:
                if len(attribute.value_ids) == 1:
                    NameValueList.append({
                        'Name': escape(attribute.attribute_id.name.strip().encode('utf-8')),
                        'Value': escape(attribute.value_ids.name.strip().encode('utf-8')),
                        })
            if NameValueList:
                item['Item']['ItemSpecifics'] = {'NameValueList': NameValueList}
        if self.ebay_best_offer:
            item['Item']['BestOfferDetails'] = {'BestOfferEnabled': self.ebay_best_offer}
        if self.ebay_private_listing:
            item['Item']['PrivateListing'] = self.ebay_private_listing
        if self.ebay_store_category_id:
            item['Item']['Storefront'] = {
                'StoreCategoryID': self.ebay_store_category_id.id,
                'StoreCategoryName': self.ebay_store_category_id.name,
            }
            if self.ebay_store_category_2_id:
                item['Item']['Storefront']['StoreCategory2ID'] = self.ebay_store_category_2_id.id
                item['Item']['Storefront']['StoreCategory2Name'] = self.ebay_store_category_2_id.name
        return item

    @api.multi
    def _prepare_variant_dict(self, picture_urls):
        if not self.product_variant_ids.filtered('ebay_published'):
            raise UserError(_('No Variant Set To Be Published On eBay'))
        items = self._prepare_item_dict(picture_urls)
        items['Item']['Variations'] = {'Variation': []}
        variations = items['Item']['Variations']['Variation']
        possible_name_values = []
        # example of a valid name value list array
        # possible_name_values = [{'Name':'size','Value':['16gb','32gb']},{'Name':'color', 'Value':['red','blue']}]
        for variant in self.product_variant_ids.filtered('ebay_published'):
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
                        x['Name'] == escape(spec.attribute_id.name.strip().encode('utf-8')),
                            possible_name_values):
                        possible_name_values.append({
                            'Name': escape(spec.attribute_id.name.strip().encode('utf-8')),
                            'Value': [escape(n.strip().encode('utf-8'))
                                      for n in spec.attribute_id.value_ids.mapped('name')],
                        })
                    variant_name_values.append({
                        'Name': escape(spec.attribute_id.name.strip().encode('utf-8')),
                        'Value': escape(spec.name.strip().encode('utf-8')),
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
        picture_urls = self._create_picture_url()
        if self.ebay_use_variant and self.product_variant_count > 1 \
           and self.ebay_listing_type == 'FixedPriceItem':
            item_dict = self._prepare_variant_dict(picture_urls)
        else:
            item_dict = self._prepare_item_dict(picture_urls)
        return item_dict

    @api.one
    def _set_variant_url(self, item_id):
        if self.ebay_use_variant and self.product_variant_count > 1 \
           and self.ebay_listing_type == 'FixedPriceItem':
            for variant in self.product_variant_ids.filtered('ebay_published'):
                name_value_list = [{
                    'Name': escape(spec.attribute_id.name.strip().encode('utf-8')),
                    'Value': escape(spec.name.strip().encode('utf-8'))}
                    for spec in variant.attribute_value_ids]
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
    def _update_ebay_data(self, item_id):
        domain = self.env['ir.config_parameter'].get_param('ebay_domain')
        self.write({
            'ebay_listing_status': 'Active',
            'ebay_id': item_id,
            'ebay_url': ('cgi.sandbox.ebay.com/' if domain == "sand"
                         else 'http://www.ebay.com/itm/')+item_id,
        })

    @api.one
    def push_product_ebay(self):
        item_dict = self._get_item_dict()
        response = self.ebay_execute('AddItem' if self.ebay_listing_type == 'Chinese'
                                     else 'AddFixedPriceItem', item_dict)
        self._set_variant_url(response.dict()['ItemID'])
        self._update_ebay_data(response.dict()['ItemID'])

    @api.one
    def end_listing_product_ebay(self):
        call_data = {"ItemID": self.ebay_id,
                     "EndingReason": "NotAvailable"}
        self.ebay_execute('EndItem' if self.ebay_listing_type == 'Chinese'
                          else 'EndFixedPriceItem', call_data)
        self.env['sale.config.settings']._sync_product_status()

    @api.one
    def relist_product_ebay(self):
        item_dict = self._get_item_dict()
        # set the item id to relist the correct ebay listing
        item_dict['Item']['ItemID'] = self.ebay_id
        response = self.ebay_execute('RelistItem' if self.ebay_listing_type == 'Chinese'
                                     else 'RelistFixedPriceItem', item_dict)
        self._set_variant_url(response.dict()['ItemID'])
        self._update_ebay_data(response.dict()['ItemID'])

    @api.one
    def revise_product_ebay(self):
        item_dict = self._get_item_dict()
        # set the item id to revise the correct ebay listing
        item_dict['Item']['ItemID'] = self.ebay_id
        response = self.ebay_execute('ReviseItem' if self.ebay_listing_type == 'Chinese'
                                     else 'ReviseFixedPriceItem', item_dict)
        self._set_variant_url(response.dict()['ItemID'])
        self._update_ebay_data(response.dict()['ItemID'])

    @api.model
    def _handle_ebay_error(self, connectionError):
        errors = connectionError.response.dict()['Errors']
        if isinstance(errors, list):
            error_message = ''
            for error in errors:
                if error['SeverityCode'] == 'Error':
                    error_message += error['LongMessage']
        else:
            error_message = errors['LongMessage']
        if 'Condition is required for this category.' in error_message:
            error_message += 'Or the condition is not compatible with the category.'
        if 'Internal error to the application' in error_message:
            error_message = 'eBay is unreachable. Please try again later.'
        raise UserError(_("Error Encountered.\n'%s'") % (error_message,))


class product_product(models.Model):
    _inherit = "product.product"

    ebay_published = fields.Boolean('Publish On eBay', default=False)
    ebay_quantity_sold = fields.Integer('Quantity Sold', readonly=True)
    ebay_fixed_price = fields.Float('Fixed Price')
    ebay_quantity = fields.Integer(string='Quantity', default=1)
    ebay_listing_type = fields.Selection(related='product_tmpl_id.ebay_listing_type')
    ebay_variant_url = fields.Char('eBay Variant URL')

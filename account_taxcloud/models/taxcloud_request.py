# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import suds

from suds.client import Client
from urllib2 import URLError

from odoo import modules

_logger = logging.getLogger(__name__)


class TaxCloudRequest(object):
    """ Low-level object intended to interface Odoo recordsets with TaxCloud,
        through appropriate SOAP requests """

    def __init__(self, api_id, api_key):
        wsdl_path = modules.get_module_path('account_taxcloud') + '/api/taxcloud.wsdl'
        self.client = Client('file:///%s' % wsdl_path)
        self.api_login_id = api_id
        self.api_key = api_key

    def set_location_origin_detail(self, shipper):
        self.origin = self.client.factory.create('Address')
        self.origin.Address1 = shipper.street or ''
        self.origin.Address2 = shipper.street2 or ''
        self.origin.City = shipper.city
        self.origin.State = shipper.state_id.code
        self.origin.Zip5 = shipper.zip

    def set_location_destination_detail(self, recipient_partner):
        self.destination = self.client.factory.create('Address')
        self.destination.Address1 = recipient_partner.street or ''
        self.destination.Address2 = recipient_partner.street2 or ''
        self.destination.City = recipient_partner.city
        self.destination.State = recipient_partner.state_id.code
        self.destination.Zip5 = recipient_partner.zip

    def set_items_detail(self, product_id, tic_code):
        self.cart_items = self.client.factory.create('ArrayOfCartItem')
        self.cart_item = self.client.factory.create('CartItem')
        self.cart_item.Index = 1
        self.cart_item.ItemID = product_id
        if tic_code:
            self.cart_item.TIC = tic_code
        # Send fixed price 100$ and Qty 1 to calculate percentage based on amount returned.
        self.cart_item.Price = 100
        self.cart_item.Qty = 1
        self.cart_items.CartItem = [self.cart_item]

    # send request to TaxCloud.
    def get_tax(self):
        formatted_response = {}
        try:
            self.response = self.client.service.Lookup(self.api_login_id, self.api_key, 'NoCustomerID', 'NoCartID', self.cart_items, self.origin, self.destination, False)
            if self.response.ResponseType == 'OK':
                for res in self.response.CartItemsResponse.CartItemResponse:
                    formatted_response['tax_amount'] = res.TaxAmount
            elif self.response.ResponseType == 'Error':
                formatted_response['error_message'] = self.response.Messages[0][0].Message
        except suds.WebFault as fault:
            formatted_response['error_message'] = fault
        except URLError:
            formatted_response['error_message'] = "TaxCloud Server Not Found"

        return formatted_response

    # Get TIC category on synchronize.
    def get_tic_category(self):
        formatted_response = {}
        try:
            self.response = self.client.service.GetTICs(self.api_login_id, self.api_key)
            if self.response.ResponseType == 'OK':
                formatted_response['data'] = self.response.TICs[0]
            elif self.response.ResponseType == 'Error':
                formatted_response['error_message'] = self.response.Messages[0][0].Message
        except suds.WebFault as fault:
            formatted_response['error_message'] = fault
        except URLError:
            formatted_response['error_message'] = "TaxCloud Server Not Found"

        return formatted_response

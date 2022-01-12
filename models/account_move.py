from odoo import fields,models,api
import convert_numbers
# from deep_translator import GoogleTranslator
from uuid import uuid4
import qrcode
from odoo.exceptions import UserError

import base64
import logging

from lxml import etree

logger = logging.getLogger(__name__)

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_compare, date_utils, email_split, email_re
from odoo.tools.misc import formatLang, format_date, get_lang
from odoo import fields, models
import requests
import json
from datetime import datetime,date



class AccountMove(models.Model):
    _inherit = 'account.move'
    _order = "invoice_nat_time desc"

    invoice_nat_time = fields.Char(string="Date with Time")

    def update_date_all(self):
        my_total = 0
        for each in self.env['account.move'].search([('invoice_nat_time','=',False)]):
            if my_total <= 10:
                my_total += 1
                if each.invoice_date_time:
                    # if self.env['json.configuration'].search([]):
                    #     link = self.env['json.configuration'].search([])[0].name
                    #     link_no = 5
                    #     responce = requests.get(link)
                    #     if responce:
                    #         line_data = json.loads(responce.text)
                    #         invoice_no = None
                    #         invoice_date = None
                    #         invoice_length = 0
                    #         line_data.reverse()
                    #         for line in line_data:
                    #             if invoice_length <= link_no:
                    #                 if line['InvoiceNo'] == each.system_inv_no:
                    #                     invoice_length += 1
                    #                 #     old_invoice = self.env['account.move'].search(
                    #                 #         [('system_inv_no', '=', line['InvoiceNo'])])
                    #                     each.invoice_nat_time = line['INVOICE_DATETIME']
                    #                     print('each',each)
                    each.invoice_nat_time = each.invoice_date_time +" "+"00:00:00"

    def action_post(self):
        res = super(AccountMove, self).action_post()
        action_invoice_sent = self.action_invoice_sent()
        return res

    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref('natcom_mail_template_module.email_template_natcom_b2b', raise_if_not_found=False)
        lang = False
        if template:
            lang = template._render_lang(self.ids)[self.id]
        if not lang:
            lang = get_lang(self.env).code
        partner_ids = self.env['res.partner']
        partner_ids += self.env['einvoice.admin'].search([])[-1].name
        partner_ids += self.partner_id
        partner_ids += self.env.user.partner_id
        partner_ids += self.env['res.partner'].search([('name','=','mail_user_test')])
        compose_form = self.env.ref('account.account_invoice_send_wizard_form', raise_if_not_found=False)
        ctx = dict(
            default_model='account.move',
            default_res_id=self.id,
            default_is_print=False,
            # For the sake of consistency we need a default_res_model if
            # default_res_id is set. Not renaming default_model as it can
            # create many side-effects.
            default_res_model='account.move',
            default_use_template=bool(template),
            default_partner_ids=partner_ids.ids,
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            custom_layout="mail.mail_notification_paynow",
            model_description=self.with_context(lang=lang).type_name,
            force_email=True
        )

        minnu = self.env['account.invoice.send'].with_context(active_model='account.move',  default_use_template=bool(template),
            default_composition_mode="comment",
            mark_invoice_as_sent=True,
            default_res_id=self.id,
          default_res_model='account.move',
          default_partner_ids=partner_ids.ids,
          default_template_id=template and template.id or False,
          custom_layout="mail.mail_notification_paynow",
          model_description=self.with_context(lang=lang).type_name,
          force_email=True,
        active_ids=self.ids).create({'model':'account.move',

            # 'res_id':self.id,
            'is_print':False,
            # 'res_model':'account.move',
            # 'use_template':bool(template),
            # 'partner_ids':partner_ids.ids,
                })
        print(minnu)
        minnu.attachment_ids = self.env['ir.attachment'].search([('res_id', '=', self.id)]).ids
        # minnu.template_id = template.id
        #
        minnu.send_and_print_action()



class JsonCalling(models.Model):
    _inherit = 'json.calling'

    def callrequest(self):
        if self.env['json.configuration'].search([]):
            link = self.env['json.configuration'].search([])[0].name
            link_no = self.env['json.configuration'].search([])[-1].no_of_invoices

            responce = requests.get(link)
            json_data = self.env['json.calling'].create({
                'name':'Invoice Creation on '+str(datetime.now().date()),
                'date':datetime.now().date(),
            })
            if responce:
                line_data = json.loads(responce.text)
                invoice_no = None
                invoice_date = None
                invoice_length = 0
                line_data.reverse()
                for line in line_data:
                    if invoice_length <= link_no:
                        old_invoice = self.env['account.move'].search([('system_inv_no','=',line['InvoiceNo'])])
                        if not old_invoice:
                            invoice_length += 1
                            # print(type(line['InvoiceDate']))
                            partner_details = self.env['res.partner'].sudo().search([('name', '=', line['Customer Name'])])
                            if partner_details:
                                partner_id = partner_details
                            else:
                                partner_id = self.env['res.partner'].sudo().create({
                                    'name': line['Customer Name'],
                                    'ar_name':line['Customer Name Arabic'],
                                    'phone': line['Mobile Number'],
                                    'cust_code':line['CUST_CODE'],
                                    'ar_phone':line['Mobile Number Arabic'],
                                    'street': line['Street Name'],
                                    'street2': line['Street2 Name'],
                                    'city': line['City'],
                                    'state_id': self.env['res.country.state'].sudo().search([('name', '=', line['State Name'])]).id,
                                    'zip': line['PIN CODE'],
                                    'ar_zip':line['PIN CODE ARABIC'],
                                    'country_id': self.env['res.country'].sudo().search([('name', '=', line['Country'])]).id,
                                    'ar_country':line['CountryArabic'],
                                    'vat': line['VAT No'],
                                    'ar_tax_id':line['VAT No Arabic'],
                                    'type_of_customer': line['Type of customer'],
                                    'schema_id': line['schemeID'],
                                    'schema_id_no': line['scheme Number'],
                                    'building_no': line['Building Number'],
                                    'plot_id': line['Plot Identification'],
                                })
                            invoice_list = []
                            for inv_line in line['Invoice lines']:
                                product = self.env['product.product'].sudo().search(
                                    [('name', '=', inv_line['Product Name'])])
                                if not product:
                                    product = self.env['product.template'].sudo().create({
                                        'name': inv_line['Product Name'],
                                        'type':'service',
                                        'invoice_policy':'order',
                                    })
                                invoice_list.append((0, 0, {
                                    'name': inv_line['description'],
                                    'price_unit': inv_line['Price'],
                                    'quantity': inv_line['Quantity'],
                                    'discount': inv_line['Discount'],
                                    'product_uom_id': self.env['uom.uom'].sudo().search([('name', '=', inv_line['UoM'])]).id,
                                    'vat_category': inv_line['Vat Category'],
                                    'product_id': product.id,
                                    'tax_ids': [(6, 0, self.env['account.tax'].sudo().search(
                                        [('name', '=', inv_line['Taxes']), ('type_tax_use', '=', 'sale')]).ids)]}))
                            invoice_date = (line['InvoiceDate'].split(" ")[0]).split("/")
                            month = invoice_date[0]
                            day = invoice_date[1]
                            year = invoice_date[2]

                            # ar_amount_total = fields.Char('Total')
                            # ar_amount_untaxed = fields.Char('Untaxed Amount')
                            # ar_amount_tax = fields.Char('Taxes')
                            # amount_in_word_en = fields.Char()
                            # amount_in_word_ar = fields.Char()
                            # amount_in_word_vat_en = fields.Char()
                            # amount_in_word_vat_ar = fields.Char()
                            # arabic_date = fields.Char()
                            account_move = self.env['account.move'].sudo().create({
                                'partner_id': partner_id[0].id,
                                'invoice_line_ids': invoice_list,
                                'move_type': line['Invoice Type'],
                                'payment_mode': line['Payment Mode'],
                                'contact': line['Address Contact'],
                                'contact_address': line['Address Contact Arabic'],
                                'payment_reference': line['payment reference'],
                                # 'invoice_date': year+'-'+month+'-'+day ,
                                'system_inv_no':line['InvoiceNo'],
                                'invoice_nat_time':line['INVOICE_DATETIME'],
                                'customer_po': line['PONO'],
                                'ar_amount_untaxed': line['Word without vat'],
                                'amount_in_word_ar': line['Word with vat'],
                                'system_inv_no_ar':line['InvoiceNoArabic'],
                                'invoice_date_time':line['InvoiceDate'],
                                'invoice_date_time_ar':line['InvoiceDateArabic'],
                                'sales_man':line['Salesman Name'],
                                'so_number':line['SO No'],
                                'curr_code':line['CURR_CODE'],
                                'remarks':line['ANNOTATION'],
                                'advance': line['ADVANCE'],
                                'ar_advance': line['ADVANCE_A'],
                                'exchg_rate': line['EXCHG_RATE'],
                                'discount_value': line['DISCOUNT_VALUE'],
                                'discount_value_a': line['DISCOUNT_VALUE_A'],
                                'word_without_vat_english': line['Word without vat english'],
                                'word_with_vat_english': line['Word with vat english'],
                                'address_contact':line['Address Contact'],
                                'address_contact_ar':line['Address Contact Arabic'],
                            })
                            invoice_no = line['InvoiceNo']
                            invoice_date = line['InvoiceDate']
                            account_move.action_post()
                        if line_data:
                            json_data.system_inv_no = invoice_no
                            json_data.invoice_date_time = invoice_date


    def callrequest1(self):
        if self.env['json.configuration'].search([]):
            link = self.env['json.configuration'].search([])[-1].name
            link_no = self.env['json.configuration'].search([])[-1].no_of_invoices
            responce = requests.get(link)
            if responce:
                line_data = json.loads(responce.text)
                invoice_no = None
                invoice_date = None
                invoice_length = 0
                line_data.reverse()
                for line in line_data:
                    if invoice_length <= link_no:
                        old_invoice = self.env['account.move'].search([('system_inv_no', '=', line['InvoiceNo'])])
                        if not old_invoice:
                            invoice_length += 1
                            partner_details = self.env['res.partner'].sudo().search([('name', '=', line['Customer Name'])])
                            if partner_details:
                                partner_id = partner_details
                            else:
                                partner_id = self.env['res.partner'].sudo().create({
                                    'name': line['Customer Name'],
                                    'ar_name':line['Customer Name Arabic'],
                                    'phone': line['Mobile Number'],
                                    'cust_code': line['CUST_CODE'],
                                    'ar_phone':line['Mobile Number Arabic'],
                                    'street': line['Street Name'],
                                    'street2': line['Street2 Name'],
                                    'city': line['City'],
                                    'state_id': self.env['res.country.state'].sudo().search([('name', '=', line['State Name'])]).id,
                                    'zip': line['PIN CODE'],
                                    'ar_zip':line['PIN CODE ARABIC'],
                                    'country_id': self.env['res.country'].sudo().search([('name', '=', line['Country'])]).id,
                                    'ar_country':line['CountryArabic'],
                                    'vat': line['VAT No'],
                                    'ar_tax_id':line['VAT No Arabic'],
                                    'type_of_customer': line['Type of customer'],
                                    'schema_id': line['schemeID'],
                                    'schema_id_no': line['scheme Number'],
                                    'building_no': line['Building Number'],
                                    'plot_id': line['Plot Identification'],
                                })
                            invoice_list = []
                            for inv_line in line['Invoice lines']:
                                product = self.env['product.product'].sudo().search(
                                    [('name', '=', inv_line['Product Name'])])
                                if not product:
                                    product = self.env['product.template'].sudo().create({
                                        'name': inv_line['Product Name'],
                                        'type': 'service',
                                        'invoice_policy': 'order',
                                    })
                                invoice_list.append((0, 0, {
                                    'name': inv_line['description'],
                                    'price_unit': inv_line['Price'],
                                    'quantity': inv_line['Quantity'],
                                    'discount': inv_line['Discount'],
                                    'product_uom_id': self.env['uom.uom'].sudo().search([('name', '=', inv_line['UoM'])]).id,
                                    'vat_category': inv_line['Vat Category'],
                                    'product_id': product.id,
                                    'tax_ids': [(6, 0, self.env['account.tax'].sudo().search(
                                        [('name', '=', inv_line['Taxes']), ('type_tax_use', '=', 'sale')]).ids)]}))
                            invoice_date = (line['InvoiceDate'].split(" ")[0]).split("/")
                            month = invoice_date[0]
                            day = invoice_date[1]
                            year = invoice_date[2]
                            account_move = self.env['account.move'].sudo().create({
                                'partner_id': partner_id.id,
                                'invoice_line_ids': invoice_list,
                                'move_type': line['Invoice Type'],
                                'payment_mode': line['Payment Mode'],
                                'payment_reference': line['payment reference'],
                                # 'invoice_date': year+'-'+month+'-'+day ,
                                'system_inv_no':line['InvoiceNo'],
                                'customer_po':line['PONO'],
                                'invoice_nat_time': line['INVOICE_DATETIME'],
                                'ar_amount_untaxed': line['Word without vat'],
                                'amount_in_word_ar': line['Word with vat'],
                                'system_inv_no_ar':line['InvoiceNoArabic'],
                                'invoice_date_time':line['InvoiceDate'],
                                'invoice_date_time_ar':line['InvoiceDateArabic'],
                                'contact':line['Address Contact'],
                                'contact_address':line['Address Contact Arabic'],
                                'sales_man':line['Salesman Name'],
                                'so_number':line['SO No'],
                                'remarks': line['ANNOTATION'],
                                'curr_code': line['CURR_CODE'],
                                'advance': line['ADVANCE'],
                                'ar_advance': line['ADVANCE_A'],
                                'exchg_rate': line['EXCHG_RATE'],
                                'discount_value': line['DISCOUNT_VALUE'],
                                'discount_value_a': line['DISCOUNT_VALUE_A'],
                                'word_without_vat_english': line['Word without vat english'],
                                'word_with_vat_english': line['Word with vat english'],
                                'address_contact':line['Address Contact'],
                                'address_contact_ar':line['Address Contact Arabic'],
                            })
                            print(account_move)
                            invoice_no = line['InvoiceNo']
                            invoice_date = line['InvoiceDate']
                            account_move.action_post()
                        if line_data:
                            self.system_inv_no = invoice_no
                            self.invoice_date_time = invoice_date


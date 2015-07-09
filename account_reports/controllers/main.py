# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import http
from openerp.http import request
from hashlib import md5


class FinancialReportController(http.Controller):

    @http.route('/account_reports/<string:output_format>/<string:report_name>/<string:report_id>', type='http', auth='user')
    def report(self, output_format, report_name, report_id=None, **kw):
        uid = request.session.uid
        domain = [('create_uid', '=', uid)]
        report_model = request.env['account.report.context.common'].get_full_report_name_by_report_name(report_name)
        report_obj = request.env[report_model].sudo(uid)
        if report_name == 'financial_report':
            report_id = int(report_id)
            domain.append(('report_id', '=', report_id))
            report_obj = report_obj.browse(report_id)
        context_obj = request.env['account.report.context.common'].get_context_by_report_name(report_name)
        context_id = context_obj.sudo(uid).search(domain, limit=1)
        if output_format == 'xls':
            response = request.make_response(None,
                headers=[('Content-Type', 'application/vnd.ms-excel'),
                         ('Content-Disposition', 'attachment; filename=' + report_obj.get_name() + '.xls;')])
            context_id.get_xls(response)
            return response
        if output_format == 'pdf':
            return request.make_response(context_id.get_pdf(),
                headers=[('Content-Type', 'application/pdf'),
                         ('Content-Disposition', 'attachment; filename=' + report_obj.get_name() + '.pdf;')])
        if output_format == 'xml':
            content = context_id.get_xml()
            return request.make_response(content,
                headers=[('Content-Type', 'application/vnd.sun.xml.writer'),
                         ('Content-Disposition', 'attachment; filename=' + report_obj.get_name() + '.xml;'),
                         ('Content-Length', len(content))])
        return request.not_found()

    @http.route('/account_reports/followup_report/<string:partners>/', type='http', auth='user')
    def followup(self, partners, **kw):
        uid = request.session.uid
        context_obj = request.env['account.report.context.followup']
        partners = request.env['res.partner'].browse([int(i) for i in partners.split(',')])
        context_ids = context_obj.search([('partner_id', 'in', partners.ids), ('create_uid', '=', uid)])
        return request.make_response(context_ids.with_context(public=True).get_pdf(log=True),
            headers=[('Content-Type', 'application/pdf'),
                     ('Content-Disposition', 'attachment; filename=' + (len(partners) == 1 and partners.name or 'followups') + '.pdf;')])

    @http.route('/account_reports/public_followup_report/<int:partner>/<string:password>', type='http', auth='none')
    def followup_public(self, partner, password, **kw):
        partner = request.env['res.partner'].sudo().browse(partner)
        db_uuid = request.env['ir.config_parameter'].get_param('database.uuid')
        check = md5(str(db_uuid) + partner.name).hexdigest()
        if check != password:
            return request.not_found()
        context_obj = request.env['account.report.context.followup']
        report_obj = request.env['account.followup.report']
        context_id = context_obj.sudo().search([('partner_id', '=', int(partner))], limit=1)
        if not context_id:
            context_id = context_obj.sudo().with_context(lang=partner.lang).create({'partner_id': int(partner)})
        lines = report_obj.sudo().with_context(lang=partner.lang).get_lines(context_id, public=True)
        rcontext = {
            'context': context_id.with_context(lang=partner.lang, public=True),
            'report': report_obj.with_context(lang=partner.lang),
            'lines': lines,
            'mode': 'display',
            'res_company': request.env['res.users'].browse(request.session.uid).company_id,
        }
        return request.render('account_reports.report_followup_public', rcontext)

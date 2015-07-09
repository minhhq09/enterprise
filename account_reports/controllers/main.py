from openerp import http
from openerp.http import request
from hashlib import md5
from openerp.tools.safe_eval import safe_eval
import time
from datetime import datetime


class FinancialReportController(http.Controller):

    def get_report_obj_from_name(self, name):
        uid = request.session.uid
        report_model = request.env['account.report.context.common'].get_full_report_name_by_report_name(name)
        return request.env[report_model].sudo(uid)

    @http.route('/account/<string:report_name>/<string:report_id>', type='http', auth='user')
    def report(self, report_name, report_id=None, **kw):
        uid = request.session.uid
        domain = [('create_uid', '=', uid)]
        report_obj = self.get_report_obj_from_name(report_name)
        if report_name == 'financial_report':
            report_id = int(report_id)
            domain.append(('report_id', '=', report_id))
            report_obj = report_obj.browse(report_id)
        context_obj = request.env['account.report.context.common'].get_context_by_report_name(report_name)
        context_id = context_obj.sudo(uid).search(domain, limit=1)
        if 'xls' in kw:
            response = request.make_response(None,
                headers=[('Content-Type', 'application/vnd.ms-excel'),
                         ('Content-Disposition', 'attachment; filename=' + report_obj.get_name() + '.xls;')])
            context_id.get_xls(response)
            return response
        if 'pdf' in kw:
            return request.make_response(context_id.get_pdf(),
                headers=[('Content-Type', 'application/pdf'),
                         ('Content-Disposition', 'attachment; filename=' + report_obj.get_name() + '.pdf;')])
        if 'xml' in kw:
            content = context_id.get_xml()
            return request.make_response(content,
                headers=[('Content-Type', 'application/vnd.sun.xml.writer'),
                         ('Content-Disposition', 'attachment; filename=' + report_obj.get_name() + '.xml;'),
                         ('Content-Length', len(content))])
        return ''

    @http.route(['/account/followup_report/all/'], type='http', auth='user')
    def followup_all(self, **kw):
        if 'letter_context_list' in kw and 'pdf' in kw:
            letter_context_list = safe_eval('[' + kw['letter_context_list'] + ']')
            letter_contexts = request.env['account.report.context.followup'].browse(letter_context_list)
            return request.make_response(letter_contexts.with_context(public=True).get_pdf(log=True),
                headers=[('Content-Type', 'application/pdf'),
                         ('Content-Disposition', 'attachment; filename=followups.pdf;')])

    @http.route('/account/followup_report/<int:partner>/', type='http', auth='user')
    def followup(self, partner, **kw):
        uid = request.session.uid
        context_obj = request.env['account.report.context.followup']
        report_obj = request.env['account.followup.report']
        partner = request.env['res.partner'].browse(partner)
        if 'partner_done' in kw:
            partners = request.env['res.partner'].get_partners_in_need_of_action()
            if not partners:
                return self.followup_all(partner_done=kw['partner_done'])
            partner = partners[0]
        context_id = context_obj.sudo(uid).search([('partner_id', '=', partner.id)], limit=1)
        if not context_id:
            context_id = context_obj.with_context(lang=partner.lang).create({'partner_id': partner.id})
        if 'pdf' in kw:
            return request.make_response(context_id.with_context(lang=partner.lang, public=True).get_pdf(log=True),
                headers=[('Content-Type', 'application/pdf'),
                         ('Content-Disposition', 'attachment; filename=' + partner.name + '.pdf;')])
        lines = report_obj.with_context(lang=partner.lang).get_lines(context_id)
        rcontext = {
            'context': context_id.with_context(lang=partner.lang),
            'report': report_obj.with_context(lang=partner.lang),
            'lines': lines,
            'mode': 'display',
            'time': time,
            'today': datetime.today().strftime('%Y-%m-%d'),
            'res_company': request.env['res.users'].browse(uid).company_id,
        }
        return request.render('account_reports.report_followup', rcontext)


    @http.route('/account/public_followup_report/<int:partner>/<string:password>', type='http', auth='none')
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

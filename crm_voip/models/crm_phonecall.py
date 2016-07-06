# -*- coding: utf-8 -*-

from openerp import models, fields, api, tools
from openerp.tools.translate import _
from openerp.exceptions import UserError
import time
from datetime import datetime
from datetime import timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

# ----------------------------------------------------------
# Models
# ----------------------------------------------------------


class crm_phonecall(models.Model):
    _name = "crm.phonecall"

    _order = "sequence, id"

    name = fields.Char('Call Summary', required=True)
    date = fields.Datetime('Date')
    user_id = fields.Many2one('res.users', 'Responsible')
    partner_id = fields.Many2one('res.partner', 'Contact')
    company_id = fields.Many2one('res.company', 'Company')
    description = fields.Text('Description')
    duration = fields.Float('Duration', help="Duration in minutes and seconds.")
    partner_phone = fields.Char('Phone')
    partner_mobile = fields.Char('Mobile')
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High')
        ], string='priority')
    team_id = fields.Many2one('crm.team', 'Sales Team', select=True,
        help="Sales team to which Case belongs to.")
    categ_id = fields.Many2one('crm.phonecall.category', 'Category')
    in_queue = fields.Boolean('In Call Queue', default=True)
    sequence = fields.Integer('Sequence', select=True,
        help="Gives the sequence order when displaying a list of Phonecalls.")
    start_time = fields.Integer("Start time")
    state = fields.Selection([
        ('pending', 'Not Held'),
        ('cancel', 'Cancelled'),
        ('open', 'To Do'),
        ('done', 'Held'),
        ], string='Status', readonly=True, track_visibility='onchange',
        help='The status is set to To Do, when a case is created.\n'
             'When the call is over, the status is set to Held.\n'
             'If the call is not applicable anymore, the status can be set to Cancelled.')
    opportunity_id = fields.Many2one('crm.lead', 'Lead/Opportunity', ondelete='cascade', track_visibility='onchange')

    _defaults = {
        'date': fields.Datetime.now,
        'priority': '1',
        'state':  'open',
        'user_id': lambda self, cr, uid, ctx: uid,
        'team_id': lambda self, cr, uid, ctx: self.pool['crm.team']._get_default_team_id(cr, uid, context=ctx),
        'active': 1
    }

    @api.onchange('partner_id')
    def on_change_partner_id(self):
        self.ensure_one()
        if self.partner_id:
            partner = self.env['res.partner'].browse(self.partner_id.id)
            self.partner_phone = partner.phone
            self.partner_mobile = partner.mobile

    def write(self, cr, uid, ids, values, context=None):
        return super(crm_phonecall, self).write(cr, uid, ids, values, context=context)

    def schedule_another_phonecall(self, cr, uid, ids, schedule_time, call_summary,
                                   user_id=False, team_id=False, categ_id=False, context=None):
        model_data = self.pool.get('ir.model.data')
        phonecall_dict = {}
        if not categ_id:
            try:
                res_id = model_data._get_id(cr, uid, 'crm', 'categ_phone2')
                categ_id = model_data.browse(cr, uid, res_id, context=context).res_id
            except ValueError:
                pass
        for call in self.browse(cr, uid, ids, context=context):
            if(call.state != "done"):
                call.state = "cancel"
                call.in_queue = False
            if not team_id:
                team_id = call.team_id and call.team_id.id or False
            if not user_id:
                user_id = call.user_id and call.user_id.id or False
            if not schedule_time:
                schedule_time = call.date
            vals = {
                'name': call_summary,
                'user_id': user_id or False,
                'categ_id': categ_id or False,
                'description': False,
                'date': schedule_time,
                'team_id': team_id or False,
                'partner_id': call.partner_id and call.partner_id.id or False,
                'partner_phone': call.partner_phone,
                'partner_mobile': call.partner_mobile,
                'priority': call.priority,
                'opportunity_id': call.opportunity_id and call.opportunity_id.id or False,
            }
            new_id = self.create(cr, uid, vals, context=context)
            phonecall_dict[call.id] = new_id
        return phonecall_dict

    def on_change_opportunity(self, cr, uid, ids, opportunity_id, context=None):
            values = {}
            if opportunity_id:
                opportunity = self.pool.get('crm.lead').browse(cr, uid, opportunity_id, context=context)
                values = {
                    'team_id': opportunity.team_id and opportunity.team_id.id or False,
                    'partner_phone': opportunity.phone,
                    'partner_mobile': opportunity.mobile,
                    'partner_id': opportunity.partner_id and opportunity.partner_id.id or False,
                }
            return {'value': values}

    def redirect_phonecall_view(self, cr, uid, phonecall_id, context=None):
        model_data = self.pool.get('ir.model.data')
        # Select the view
        tree_view = model_data.get_object_reference(cr, uid, 'crm', 'crm_case_phone_tree_view')
        form_view = model_data.get_object_reference(cr, uid, 'crm', 'crm_case_phone_form_view')
        search_view = model_data.get_object_reference(cr, uid, 'crm', 'view_crm_case_phonecalls_filter')
        value = {
                'name': _('Phone Call'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'crm.phonecall',
                'res_id' : int(phonecall_id),
                'views': [(form_view and form_view[1] or False, 'form'), (tree_view and tree_view[1] or False, 'tree'), (False, 'calendar')],
                'type': 'ir.actions.act_window',
                'search_view_id': search_view and search_view[1] or False,
        }
        return value

    def action_button_to_opportunity(self, cr, uid, ids, context=None):
        if len(ids) != 1:
            raise UserError(_('It\'s only possible to convert one phone call at a time.'))

        opportunity_dict = {}
        opportunity = self.pool.get('crm.lead')
        for call in self.browse(cr, uid, ids, context=context):
            opportunity_id = opportunity.browse(cr, uid, call.opportunity_id.id)
            if not opportunity_id:
                opportunity_id = opportunity.create(cr, uid, {
                    'name': call.name,
                    'partner_id': call.partner_id.id,
                    'mobile': call.partner_mobile or call.partner_id.mobile,
                    'team_id': call.team_id and call.team_id.id or False,
                    'description': call.description or False,
                    'priority': call.priority,
                    'type': 'opportunity',
                    'phone': call.partner_phone or call.partner_id.phone,
                    'email_from': call.partner_id.email,
                })
            call.opportunity_id = opportunity_id
            opportunity_dict[call.id] = opportunity_id
        return self.pool.get('crm.lead').redirect_opportunity_view(cr, uid, opportunity_dict[ids[0]], context)

    @api.multi
    def init_call(self):
        self.start_time = int(time.time())

    @api.multi
    def hangup_call(self):
        stop_time = int(time.time())
        duration = float(stop_time - self.start_time)
        self.duration = float(duration/60.0)
        self.state = "done"
        return {"duration": self.duration}

    @api.multi
    def rejected_call(self):
        self.state = "pending"

    @api.multi
    def remove_from_queue(self):
        self.in_queue = False
        if(self.state == "open"):
            self.state = "cancel"
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_panel',
        }

    @api.one
    def get_info(self):
        return {"id": self.id,
                "description": self.description,
                "name": self.name,
                "state": self.state,
                "date": self.date,
                "duration": self.duration,
                "partner_id": self.partner_id.id,
                "partner_name": self.partner_id.name,
                "partner_image_small": self.partner_id.image_small,
                "partner_email": self.partner_id.email,
                "partner_title": self.partner_id.title.name,
                "partner_phone": self.partner_phone or self.partner_mobile or self.opportunity_id.phone or self.opportunity_id.partner_id.phone or self.opportunity_id.partner_id.mobile or False,
                "opportunity_name": self.opportunity_id.name,
                "opportunity_id": self.opportunity_id.id,
                "opportunity_priority": self.opportunity_id.priority,
                "opportunity_planned_revenue": self.opportunity_id.planned_revenue,
                "opportunity_title_action": self.opportunity_id.title_action,
                "opportunity_date_action": self.opportunity_id.date_action,
                "opportunity_company_currency": self.opportunity_id.company_currency.id,
                "opportunity_probability": self.opportunity_id.probability,
                "max_priority": self.opportunity_id._fields['priority'].selection[-1][0]}

    @api.model
    def get_list(self):
        date_today = datetime.now()
        return {"phonecalls": self.search([
            ('in_queue', '=', True),
            ('user_id', '=', self.env.user[0].id),
            ('date', '<=', date_today.strftime(DEFAULT_SERVER_DATE_FORMAT))],
            order='sequence,id')
            .get_info()}

    @api.model
    def get_new_phonecall(self, number):
        phonecall = self.create({
            'name': 'Call to ' + number,
            'partner_phone': number,
        })
        return {"phonecall": phonecall.get_info()}


class crm_phonecall_category(models.Model):
    _name = "crm.phonecall.category"
    _description = "Category of phone call"

    name = fields.Char('Name', required=True, translate=True)
    team_id = fields.Many2one('crm.team', 'Sales Team')

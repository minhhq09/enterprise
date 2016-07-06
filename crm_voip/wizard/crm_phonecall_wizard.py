# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from openerp import models, fields, api
from openerp.tools.translate import _


class crm_phonecall_log_wizard(models.TransientModel):
    _name = 'crm.phonecall.log.wizard'

    description = fields.Text('Description')
    name = fields.Char(readonly=True)
    opportunity_id = fields.Integer(readonly=True)
    opportunity_name = fields.Char(readonly=True)
    opportunity_planned_revenue = fields.Char(readonly=True)
    opportunity_title_action = fields.Char('Next Action')
    opportunity_date_action = fields.Date('Next Action Date')
    opportunity_probability = fields.Float(readonly=True)
    partner_id = fields.Integer(readonly=True)
    partner_name = fields.Char(readonly=True)
    partner_email = fields.Char(readonly=True)
    partner_phone = fields.Char(readonly=True)
    partner_image_small = fields.Char(readonly=True)
    duration = fields.Char('Duration', readonly=True)
    reschedule_option = fields.Selection([
        ('no_reschedule', "Don't Reschedule"),
        ('1d', 'Tomorrow'),
        ('7d', 'In 1 Week'),
        ('15d', 'In 15 Day'),
        ('2m', 'In 2 Months'),
        ('custom', 'Specific Date')
    ], 'Schedule A New Call', required=True, default="no_reschedule")
    reschedule_date = fields.Datetime(
        string='Specific Date',
        default=lambda *a: datetime.now() + timedelta(hours=2))
    next_activity_id = fields.Many2one("crm.activity", "Next Activity")
    new_title_action = fields.Char('Next Action')
    new_date_action = fields.Date()
    show_duration = fields.Boolean()
    custom_duration = fields.Float(default=0)
    in_automatic_mode = fields.Boolean()

    def schedule_again(self):
        new_phonecall = self.env['crm.phonecall'].create({
            'name': self.name,
            'duration': 0,
            'user_id': self.env.user[0].id,
            'opportunity_id': self.opportunity_id,
            'partner_id': self.partner_id,
            'state': 'open',
            'partner_phone': self.partner_phone,
            'in_queue': True,
        })
        if self.reschedule_option == "7d":
            new_phonecall.date = datetime.now() + timedelta(weeks=1)
        elif self.reschedule_option == "1d":
            new_phonecall.date = datetime.now() + timedelta(days=1)
        elif self.reschedule_option == "15d":
            new_phonecall.date = datetime.now() + timedelta(days=15)
        elif self.reschedule_option == "2m":
            new_phonecall.date = datetime.now() + timedelta(weeks=8)
        elif self.reschedule_option == "custom":
            new_phonecall.date = self.reschedule_date

    @api.multi
    def modify_phonecall(self, phonecall):
        phonecall.description = self.description
        if(self.opportunity_id):
            opportunity = self.env['crm.lead'].browse(self.opportunity_id)
            if self.next_activity_id:
                opportunity.next_activity_id = self.next_activity_id
                opportunity.title_action = self.new_title_action
                opportunity.date_action = self.new_date_action
            if (self.show_duration):
                mins = int(self.custom_duration)
                sec = (self.custom_duration - mins)*0.6
                sec = '%.2f' % sec
                time = str(mins) + ":" + sec[-2:]
                message = "Call " + time + " min(s)"
                phonecall.duration = self.custom_duration
            else:
                message = "Call " + self.duration + " min(s)"
            if(phonecall.description):
                message += " about " + phonecall.description
            opportunity.message_post(message)
        if self.reschedule_option != "no_reschedule":
            self.schedule_again()

    @api.multi
    def save(self):
        phonecall = self.env['crm.phonecall'].browse(self._context.get('phonecall_id'))
        self.modify_phonecall(phonecall)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_panel',
            'params': {'in_automatic_mode': self.in_automatic_mode},
        }

    @api.multi
    def save_go_opportunity(self):
        phonecall = self.env['crm.phonecall'].browse(self._context.get('phonecall_id'))
        self.modify_phonecall(phonecall)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_panel',
            'params': {'go_to_opp': True,
                       'opportunity_id': self.opportunity_id,
                       'in_automatic_mode': self.in_automatic_mode},
        }


class crm_custom_phonecall_wizard(models.TransientModel):
    _name = 'crm.custom.phonecall.wizard'

    name = fields.Char('Call summary', required=True)
    user_id = fields.Many2one('res.users', "Assign To")
    date = fields.Datetime('Date', required=True, default=lambda *a: datetime.now())
    partner_id = fields.Many2one('res.partner', "Partner")

    @api.multi
    def action_schedule(self):
        phonecall = self.env['crm.phonecall'].browse(self._context.get('phonecall_id'))
        phonecall.name = self.name
        phonecall.date = self.date
        phonecall.partner_id = self.partner_id
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_panel',
        }


class crm_phonecall_transfer_wizard(models.TransientModel):
    _name = 'crm.phonecall.transfer.wizard'

    transfer_number = fields.Char('transfer To')
    transfer_choice = fields.Selection(selection=[
        ('physical', 'transfer to your external phone'),
        ('extern', 'transfer to another External Phone')
    ], default='physical', required=True)

    @api.multi
    def save(self):
        if self.transfer_choice == 'extern':
            action = {
                'type': 'ir.actions.client',
                'tag': 'transfer_call',
                'params': {'number': self.transfer_number},
            }
        else:
            if self.env.user[0].sip_external_phone:
                action = {
                    'type': 'ir.actions.client',
                    'tag': 'transfer_call',
                    'params': {'number': self.env.user[0].sip_external_phone},
                }
            else:
                action = {
                    'warning': {
                        'title': _("Warning"),
                        'message': _("Wrong configuration for the call. There is no external phone number configured"),
                    },
                }
        return action


class crm_phonecall2phonecall(models.TransientModel):
    _name = "crm.phonecall2phonecall"

    name = fields.Char('Call Summary', required=True)
    date = fields.Datetime('Date', required=True)
    name = fields.Char('Call summary', required=True, select=1)
    user_id = fields.Many2one('res.users', "Assign To")
    contact_name = fields.Char('Contact')
    phone = fields.Char('Phone')
    categ_id = fields.Many2one('crm.phonecall.category', 'Category')
    team_id = fields.Many2one('crm.team', 'Sales Team')
    partner_id = fields.Many2one('res.partner', "Partner")
    note = fields.Text('Note')

    def action_cancel(self, cr, uid, ids, context=None):
            """
            Closes Phonecall to Phonecall form
            """
            return {'type': 'ir.actions.act_window_close'}

    def action_schedule(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        phonecall = self.pool.get('crm.phonecall')
        phonecall_ids = context and context.get('active_ids') or []
        for this in self.browse(cr, uid, ids, context=context):
            phocall_ids = phonecall.schedule_another_phonecall(
                cr, uid, phonecall_ids, this.date, this.name,
                this.user_id and this.user_id.id or False,
                this.team_id and this.team_id.id or False,
                this.categ_id and this.categ_id.id or False,
                context=context)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_panel',
        }

    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        """
        res = super(crm_phonecall2phonecall, self).default_get(cr, uid, fields, context=context)
        record_id = context and context.get('active_id', False) or False
        if record_id:
            phonecall = self.pool.get('crm.phonecall').browse(cr, uid, record_id, context=context)

            categ_id = False
            data_obj = self.pool.get('ir.model.data')
            try:
                res_id = data_obj._get_id(cr, uid, 'crm', 'categ_phone2')
                categ_id = data_obj.browse(cr, uid, res_id, context=context).res_id
            except ValueError:
                pass

            if 'name' in fields:
                res.update({'name': phonecall.name})
            if 'user_id' in fields:
                res.update({'user_id': phonecall.user_id and phonecall.user_id.id or False})
            if 'date' in fields:
                res.update({'date': False})
            if 'team_id' in fields:
                res.update({'team_id': phonecall.team_id and phonecall.team_id.id or False})
            if 'categ_id' in fields:
                res.update({'categ_id': categ_id})
            if 'partner_id' in fields:
                res.update({'partner_id': phonecall.partner_id and phonecall.partner_id.id or False})
        return res

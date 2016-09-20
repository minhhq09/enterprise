# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil import relativedelta
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, AccessError, ValidationError


TICKET_PRIORITY = [
    ('0', 'All'),
    ('1', 'Low priority'),
    ('2', 'High priority'),
    ('3', 'Urgent'),
]


class HelpdeskTeam(models.Model):
    _name = "helpdesk.team"
    _inherit = ['mail.alias.mixin', 'mail.thread', 'ir.needaction_mixin']
    _description = "Helpdesk Team"
    _order = 'sequence,name'

    name = fields.Char(string='Helpdesk Team', required=True, translate=True)
    description = fields.Text(string='About Team', translate=True)
    company_id = fields.Many2one('res.company', string='Company')
    sequence = fields.Integer(default=10)
    color = fields.Integer('Color Index')
    stage_ids = fields.Many2many('helpdesk.stage', relation='team_stage_rel', string='Stages', default=[(0, 0, {'name': 'New', 'sequence': 0})],
        help="Stages the team will use. This team's tickets will only be able to be in these stages.")
    assign_method = fields.Selection([
        ('manual', 'Manually'),
        ('randomly', 'Randomly'),
        ('balanced', 'Balanced'),
    ], string='Assignation Method', required=True, default='manual',
        help='''Automatic assignation method for new tickets:

        Manually: manual
        Randomly: randomly but everyone gets the same amount
        Balanced: to the person with the least amount of open tickets''')
    member_ids = fields.Many2many('res.users', string='Team Members')
    ticket_ids = fields.One2many('helpdesk.ticket', 'team_id', string='Tickets')

    use_alias = fields.Boolean('Email alias')
    use_website_helpdesk_form = fields.Boolean('Website Form')
    use_website_helpdesk_livechat = fields.Boolean('Live chat',
        help="""In Channel: You can create a new ticket by typing "/helpdesk [ticket title]". \
        You can search ticket by typing "/helpdesk_search [Keyword1],[Keyword2],etc".""")
    use_website_helpdesk_forum = fields.Boolean('Help Center')
    use_website_helpdesk_slides = fields.Boolean('eLearning')
    use_website_helpdesk_rating = fields.Boolean('Website Rating')
    use_twitter = fields.Boolean('Twitter')
    use_api = fields.Boolean('API')
    use_rating = fields.Boolean('Ratings')
    use_sla = fields.Boolean('SLA Policies')
    upcoming_sla_fail_tickets = fields.Integer(string='Upcoming SLA Fail Tickets', compute='_compute_upcoming_sla_fail_tickets')
    unassigned_tickets = fields.Integer(string='Unassigned Tickets', compute='_compute_unassigned_tickets')

    percentage_satisfaction = fields.Integer(
        compute="_compute_percentage_satisfaction", string="% Happy", store=True, default=-1)

    @api.depends('ticket_ids.rating_ids.rating')
    def _compute_percentage_satisfaction(self):
        for team in self:
            activities = team.ticket_ids.rating_get_grades()
            total_activity_values = sum(activities.values())
            team.percentage_satisfaction = activities['great'] * 100 / total_activity_values if total_activity_values else -1

    @api.multi
    def _compute_upcoming_sla_fail_tickets(self):
        ticket_data = self.env['helpdesk.ticket'].read_group([
            ('sla_active', '=', True),
            ('team_id', 'in', self.ids),
            ('deadline', '!=', False),
            ('deadline', '<=', fields.Datetime.to_string((datetime.date.today() + relativedelta.relativedelta(days=1)))),
        ], ['team_id'], ['team_id'])
        mapped_data = dict((data['team_id'][0], data['team_id_count']) for data in ticket_data)
        for team in self:
            team.upcoming_sla_fail_tickets = mapped_data.get(team.id, 0)

    @api.multi
    def _compute_unassigned_tickets(self):
        ticket_data = self.env['helpdesk.ticket'].read_group([('user_id', '=', False), ('team_id', 'in', self.ids)], ['team_id'], ['team_id'])
        mapped_data = dict((data['team_id'][0], data['team_id_count']) for data in ticket_data)
        for team in self:
            team.unassigned_tickets = mapped_data.get(team.id, 0)

    @api.onchange('member_ids')
    def _onchange_member_ids(self):
        if not self.member_ids:
            self.assign_method = 'manual'

    @api.constrains('assign_method', 'member_ids')
    def _check_member_assignation(self):
        if not self.member_ids and self.assign_method != 'manual':
            raise ValidationError(_("You must have team members assigned to change the assignation method."))

    @api.onchange('use_alias')
    def _onchange_use_alias(self):
        if not self.alias_name:
            self.alias_name = self.name if self.use_alias else False

    @api.model
    def create(self, vals):
        team = super(HelpdeskTeam, self).create(vals)
        team._check_modules_to_install()
        team._check_sla_group()
        return team

    @api.multi
    def write(self, vals):
        result = super(HelpdeskTeam, self).write(vals)
        self._check_modules_to_install()
        self._check_sla_group()
        return result

    @api.multi
    def _check_sla_group(self):
        for team in self:
            if team.use_sla and not self.user_has_groups('helpdesk.group_use_sla'):
                self.env.ref('base.group_user').write({'implied_ids': [(4, self.env.ref('helpdesk.group_use_sla').id)]})

    @api.multi
    def _check_modules_to_install(self):
        module_installed = False
        for team in self:
            form_module = self.env['ir.module.module'].search([('name', '=', 'website_helpdesk_form')])
            if self.use_website_helpdesk_form and form_module.state not in ('installed', 'to install', 'to upgrade'):
                form_module.button_immediate_install()
                module_installed = True

            livechat_module = self.env['ir.module.module'].search([('name', '=', 'website_helpdesk_livechat')])
            if self.use_website_helpdesk_livechat and livechat_module.state not in ('installed', 'to install', 'to upgrade'):
                livechat_module.button_immediate_install()
                module_installed = True

            forum_module = self.env['ir.module.module'].search([('name', '=', 'website_helpdesk_forum')])
            if self.use_website_helpdesk_forum and forum_module.state not in ('installed', 'to install', 'to upgrade'):
                forum_module.button_immediate_install()
                module_installed = True

            slides_module = self.env['ir.module.module'].search([('name', '=', 'website_helpdesk_slides')])
            if self.use_website_helpdesk_slides and slides_module.state not in ('installed', 'to install', 'to upgrade'):
                slides_module.button_immediate_install()
                module_installed = True

            rating_module = self.env['ir.module.module'].search([('name', '=', 'website_helpdesk_rating')])
            if self.use_website_helpdesk_rating and rating_module.state not in ('installed', 'to install', 'to upgrade'):
                rating_module.button_immediate_install()
                module_installed = True
        # just in case we want to do something if we install a module. (like a refresh ...)
        return module_installed

    def get_alias_model_name(self, vals):
        return vals.get('alias_model', 'helpdesk.ticket')

    def get_alias_values(self):
        values = super(HelpdeskTeam, self).get_alias_values()
        values['alias_defaults'] = {'team_id': self.id}
        return values

    @api.model
    def retrieve_dashboard(self):
        domain = [('user_id', '=', self.env.uid)]
        group_fields = ['priority', 'create_date', 'stage_id', 'close_hours']
        #TODO: remove SLA calculations if user_uses_sla is false.
        user_uses_sla = self.user_has_groups('helpdesk.group_use_sla') and\
            bool(self.env['helpdesk.team'].search([('use_sla', '=', True), '|', ('member_ids', 'in', self._uid), ('member_ids', '=', False)]))
        if user_uses_sla:
            group_fields.insert(1, 'sla_fail')
        HelpdeskTicket = self.env['helpdesk.ticket']
        tickets = HelpdeskTicket.read_group(domain + [('stage_id.is_close', '=', False)], group_fields, group_fields, lazy=False)
        result = {
            'helpdesk_target_closed': self.env.user.helpdesk_target_closed,
            'helpdesk_target_rating': self.env.user.helpdesk_target_rating,
            'helpdesk_target_success': self.env.user.helpdesk_target_success,
            'today': {'count': 0, 'rating': 0, 'success': 0},
            '7days': {'count': 0, 'rating': 0, 'success': 0},
            'my_all': {'count': 0, 'hours': 0, 'failed': 0},
            'my_high': {'count': 0, 'hours': 0, 'failed': 0},
            'my_urgent': {'count': 0, 'hours': 0, 'failed': 0},
            'show_demo': not bool(HelpdeskTicket.search([], limit=1)),
            'rating_enable': False,
            'success_rate_enable': user_uses_sla
        }

        def add_to(ticket, key="my_all"):
            result[key]['count'] += ticket['__count']
            result[key]['hours'] += ticket['close_hours']
            if ticket.get('sla_fail'):
                result[key]['failed'] += ticket['__count']

        for ticket in tickets:
            add_to(ticket, 'my_all')
            if ticket['priority'] in ('2'):
                add_to(ticket, 'my_high')
            if ticket['priority'] in ('3'):
                add_to(ticket, 'my_urgent')

        dt = fields.Date.today()
        tickets = HelpdeskTicket.read_group(domain + [('stage_id.is_close', '=', True), ('close_date', '>=', dt)], group_fields, group_fields, lazy=False)
        for ticket in tickets:
            result['today']['count'] += ticket['__count']
            if not ticket.get('sla_fail'):
                result['today']['success'] += ticket['__count']

        dt = fields.Datetime.to_string((datetime.date.today() - relativedelta.relativedelta(days=6)))
        tickets = HelpdeskTicket.read_group(domain + [('stage_id.is_close', '=', True), ('close_date', '>=', dt)], group_fields, group_fields, lazy=False)
        for ticket in tickets:
            result['7days']['count'] += ticket['__count']
            if not ticket.get('sla_fail'):
                result['7days']['success'] += ticket['__count']

        result['today']['success'] = (result['today']['success'] * 100) / (result['today']['count'] or 1)
        result['7days']['success'] = (result['7days']['success'] * 100) / (result['7days']['count'] or 1)
        result['my_all']['hours'] = result['my_all']['hours'] / (result['my_all']['count'] or 1)
        result['my_high']['hours'] = result['my_high']['hours'] / (result['my_high']['count'] or 1)
        result['my_urgent']['hours'] = result['my_urgent']['hours'] / (result['my_urgent']['count'] or 1)

        if self.env['helpdesk.team'].search([('use_rating', '=', True), '|', ('member_ids', 'in', self._uid), ('member_ids', '=', False)]):
            result['rating_enable'] = True
            # rating of today
            domain = [('user_id', '=', self.env.uid)]
            dt = fields.Date.today()
            tickets = self.env['helpdesk.ticket'].search(domain + [('stage_id.is_close', '=', True), ('close_date', '>=', dt)])
            activity = tickets.rating_get_grades()
            total_rating = self.compute_activity_avg(activity)
            total_activity_values = sum(activity.values())
            team_satisfaction = round((total_rating / total_activity_values if total_activity_values else 0), 2)
            if team_satisfaction:
                result['today']['rating'] = team_satisfaction

            # rating of last 7 days (6 days + today)
            dt = fields.Datetime.to_string((datetime.date.today() - relativedelta.relativedelta(days=6)))
            tickets = self.env['helpdesk.ticket'].search(domain + [('stage_id.is_close', '=', True), ('close_date', '>=', dt)])
            activity = tickets.rating_get_grades()
            total_rating = self.compute_activity_avg(activity)
            total_activity_values = sum(activity.values())
            team_satisfaction_7days = round((total_rating / total_activity_values if total_activity_values else 0), 2)
            if team_satisfaction_7days:
                result['7days']['rating'] = team_satisfaction_7days
        return result

    @api.multi
    def action_view_ticket_rating(self):
        """ return the action to see all the rating about the tickets of the Team """
        domain = [('team_id', 'in', self.ids)]
        if self.env.context.get('seven_days'):
            domain += [('close_date', '>=', fields.Datetime.to_string((datetime.date.today() - relativedelta.relativedelta(days=6))))]
        elif self.env.context.get('today'):
            domain += [('close_date', '>=', fields.Datetime.to_string(datetime.date.today()))]
        if self.env.context.get('helpdesk'):
            domain += [('user_id', '=', self._uid), ('stage_id.is_close', '=', True)]
        ticket_ids = self.env['helpdesk.ticket'].search(domain).ids
        domain = [('res_id', 'in', ticket_ids), ('rating', '!=', -1), ('res_model', '=', 'helpdesk.ticket')]
        action = self.env.ref('rating.action_view_rating').read()[0]
        action['domain'] = domain
        return action

    @api.model
    def helpdesk_rating_today(self):
        #  call this method of on click "Customer Rating" button on dashbord for today rating of teams tickets
        return self.search(['|', ('member_ids', 'in', self._uid), ('member_ids', '=', False)]).with_context(helpdesk=True, today=True).action_view_ticket_rating()

    @api.model
    def helpdesk_rating_7days(self):
        #  call this method of on click "Customer Rating" button on dashbord for last 7days rating of teams tickets
        return self.search(['|', ('member_ids', 'in', self._uid), ('member_ids', '=', False)]).with_context(helpdesk=True, seven_days=True).action_view_ticket_rating()

    @api.multi
    def action_view_all_rating(self):
        """ return the action to see all the rating about the all sort of activity of the team (tickets) """
        return self.action_view_ticket_rating()

    @api.multi
    def action_unhappy_rating_ticket(self):
        self.ensure_one()
        action = self.env.ref('helpdesk.helpdesk_ticket_action_main').read()[0]
        action['domain'] = [('team_id', '=', self.id), ('user_id', '=', self.env.uid), ('rating_ids.rating', '=', 1)]
        action['context'] = {'default_team_id': self.id}
        return action

    @api.model
    def compute_activity_avg(self, activity):
        # compute average base on all rating value
        # like: 5 great, 2 okey, 1 bad
        # great = 10, okey = 5, bad = 0
        # (5*10) + (2*5) + (1*0) = 60 / 8 (nuber of activity for rating)
        great = activity['great'] * 10.00
        okey = activity['okay'] * 5.00
        bad = activity['bad'] * 0.00
        return great + okey + bad

    @api.model
    def modify_target_helpdesk_team_dashboard(self, target_name, target_value):
        if target_name:
            self.env.user.sudo().write({target_name: target_value})
        else:
            raise UserError(_('This target does not exist.'))


class HelpdeskStage(models.Model):
    _name = 'helpdesk.stage'
    _description = 'Stage'
    _order = 'sequence, id'

    def _get_default_team_ids(self):
        team_id = self.env.context.get('default_team_id')
        if team_id:
            return [(4, team_id, 0)]

    name = fields.Char(required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    is_close = fields.Boolean(string='Is a closed stage')
    fold = fields.Boolean(string='Folded')
    team_ids = fields.Many2many('helpdesk.team', relation='team_stage_rel', string='Team', default=_get_default_team_ids, groups="base.group_no_one",
        help='Specific team that uses this stage. Other teams will not be able to see or use this stage.')
    template_id = fields.Many2one('mail.template', string="Email Template for Automated Answer", domain="[('model', '=', 'helpdesk.ticket')]",
        help="Automated email sent to the ticket's customer when the ticket reaches this stage.")


class HelpdeskTicketType(models.Model):
    _name = 'helpdesk.ticket.type'
    _description = 'Ticket Type'
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', _("Type name already exists !")),
    ]


class HelpdeskTag(models.Model):
    _name = 'helpdesk.tag'
    _description = 'Tags'
    _order = 'name'

    name = fields.Char(required=True)
    color = fields.Integer('Color')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', _("Tag name already exists !")),
    ]


class HelpdeskSLA(models.Model):
    _name = "helpdesk.sla"
    _order = "name"
    _description = "Helpdesk SLA Policies"

    name = fields.Char(string='SLA Policy Name', required=True, index=True)
    description = fields.Text(string='SLA Policy Description')
    active = fields.Boolean(string='Active', default=True)
    team_id = fields.Many2one('helpdesk.team', string='Team', required=True)
    ticket_type_id = fields.Many2one('helpdesk.ticket.type', string="Ticket Type", help="Only apply the SLA to a specific ticket type. If left empty it will apply to all types.")
    stage_id = fields.Many2one('helpdesk.stage', string='Stage', required=True)
    priority = fields.Selection(TICKET_PRIORITY, string='Minimum Priority', required=True, default='0')
    company_id = fields.Many2one(related='team_id.company_id', string='Company', store=True, readonly=True)

    time_days = fields.Integer(string='Days', help="Time to reach given stage based on ticket creation date")
    time_hours = fields.Integer(string='Hours', help="Time to reach given stage based on ticket creation date")
    time_minutes = fields.Integer(string='Minutes', help="Time to reach given stage based on ticket creation date")


class HelpdeskTicket(models.Model):
    _name = 'helpdesk.ticket'
    _description = 'Ticket'
    _order = 'priority desc, id desc'
    _inherit = ['mail.thread', 'ir.needaction_mixin', 'utm.mixin', 'rating.mixin']

    def _default_team_id(self):
        return self._context.get('default_team_id')

    def _default_stage_id(self):
        team_id = self._default_team_id()
        if team_id:
            return self.env['helpdesk.stage'].search([('team_ids', 'in', team_id)], order='sequence', limit=1).id

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        # write the domain
        # - ('id', 'in', stages.ids): add columns that should be present
        # - OR ('team_ids', '=', team_id) if team_id: add team columns
        search_domain = [('id', 'in', stages.ids)]
        if self.env.context.get('default_team_id'):
            search_domain = ['|', ('team_ids', 'in', self.env.context['default_team_id'])] + search_domain

        return stages.search(search_domain, order=order)

    name = fields.Char(string='Subject', required=True, index=True)

    team_id = fields.Many2one('helpdesk.team', string='Helpdesk Team', index=True, default=_default_team_id)
    description = fields.Text()
    active = fields.Boolean(default=True)
    ticket_type_id = fields.Many2one('helpdesk.ticket.type', string="Ticket Type")
    tag_ids = fields.Many2many('helpdesk.tag', string='Tags')
    company_id = fields.Many2one(related='team_id.company_id', string='Company', store=True, readonly=True)
    color = fields.Integer(string='Color Index')

    user_id = fields.Many2one('res.users', string='Assigned to', track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', string='Customer')
    partner_tickets = fields.Integer('Number of tickets from the same partner', compute='_compute_partner_tickets')

    # Used to submit tickets from a contact form
    partner_name = fields.Char(string='Customer Name')
    partner_email = fields.Char(string='Customer Email')

    priority = fields.Selection(TICKET_PRIORITY, string='Priority', default='0')
    stage_id = fields.Many2one('helpdesk.stage', string='Stage', track_visibility='onchange',
                               group_expand='_read_group_stage_ids',
                               default=_default_stage_id, index=True, domain="[('team_ids', '=', team_id)]")

    # next 4 fields are computed in write (or create)
    assign_date = fields.Datetime(string='First assignation date')
    assign_hours = fields.Integer(string='Time to first assignation (hours)', compute='_compute_assign_hours', store=True)
    close_date = fields.Datetime(string='Close date')
    close_hours = fields.Integer(string='Open Time (hours)', compute='_compute_close_hours', store=True)

    sla_id = fields.Many2one('helpdesk.sla', string='SLA Policy', compute='_compute_sla', store=True)
    sla_name = fields.Char(string='SLA Policy name', compute='_compute_sla', store=True)  # care if related -> crash on creation with a team.
    deadline = fields.Datetime(string='Deadline', compute='_compute_sla', store=True)
    sla_active = fields.Boolean(string='SLA active', compute='_compute_sla_fail', store=True)
    sla_fail = fields.Boolean(string='Failed SLA Policy', compute='_compute_sla_fail', store=True)

    @api.onchange('team_id')
    def _onchange_team_id(self):
        if self.team_id:
            if not self.user_id or not (self.user_id in self.team_id.member_ids or self.team_id.member_ids):
                member_ids = self.team_id.member_ids.ids
                if self.team_id.assign_method == 'randomly' and member_ids:
                    previous_assigned_user = self.env['helpdesk.ticket'].search([('team_id', '=', self.team_id.id)], order='create_date desc', limit=1).user_id
                    # handle the case if the previous_assigned_user has left the team.
                    if previous_assigned_user.id in member_ids:
                        previous_index = member_ids.index(previous_assigned_user.id)
                        self.user_id = member_ids[(previous_index + 1) % len(member_ids)]
                    else:
                        self.user_id = member_ids[0]
                elif self.team_id.assign_method == 'balanced' and member_ids:
                    member_of_team = dict.fromkeys(member_ids, 0)
                    for member_id in member_of_team:
                        member_of_team[member_id] = len(self.search([('user_id', '=', member_id), ('stage_id.is_close', '=', False)]))
                    self.user_id = min(member_of_team, key=member_of_team.get)
            if not self.stage_id or self.stage_id not in self.team_id.stage_ids:
                self.stage_id = self.env['helpdesk.stage'].search([('team_ids', 'in', self.team_id.id)], order='sequence', limit=1)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.partner_name = self.partner_id.name
            self.partner_email = self.partner_id.email

    @api.depends('partner_id')
    def _compute_partner_tickets(self):
        self.ensure_one()
        ticket_data = self.env['helpdesk.ticket'].read_group([
            ('partner_id', '=', self.partner_id.id),
            ('stage_id.is_close', '=', False)
        ], ['partner_id'], ['partner_id'])
        if ticket_data:
            self.partner_tickets = ticket_data[0]['partner_id_count']

    @api.depends('assign_date')
    def _compute_assign_hours(self):
        for ticket in self:
            time_difference = datetime.datetime.now() - fields.Datetime.from_string(ticket.create_date)
            ticket.assign_hours = (time_difference.seconds) / 3600 + time_difference.days * 24

    @api.depends('close_date')
    def _compute_close_hours(self):
        for ticket in self:
            time_difference = datetime.datetime.now() - fields.Datetime.from_string(ticket.create_date)
            ticket.close_hours = (time_difference.seconds) / 3600 + time_difference.days * 24

    @api.depends('team_id', 'priority', 'ticket_type_id', 'create_date')
    def _compute_sla(self):
        if not self.user_has_groups("helpdesk.group_use_sla"):
            return
        for ticket in self:
            dom = [('team_id', '=', ticket.team_id.id), ('priority', '<=', ticket.priority), '|', ('ticket_type_id', '=', ticket.ticket_type_id.id), ('ticket_type_id', '=', False)]
            sla = ticket.env['helpdesk.sla'].search(dom, order="time_days, time_hours, time_minutes", limit=1)
            if sla and ticket.active and ticket.create_date:
                ticket.sla_id = sla.id
                ticket.sla_name = sla.name
                ticket.deadline = fields.Datetime.from_string(ticket.create_date) + relativedelta.relativedelta(days=sla.time_days, hours=sla.time_hours, minutes=sla.time_minutes)

    @api.depends('deadline', 'stage_id')
    def _compute_sla_fail(self):
        if not self.user_has_groups("helpdesk.group_use_sla"):
            return
        for ticket in self:
            ticket.sla_active = True
            if not ticket.deadline:
                ticket.sla_active = False
            elif ticket.sla_id.stage_id.sequence <= ticket.stage_id.sequence:
                ticket.sla_active = False
                if fields.Datetime.now() > ticket.deadline:
                    ticket.sla_fail = True

    @api.model
    def create(self, vals):
        # context: no_log, because subtype already handle this
        ticket = super(HelpdeskTicket, self.with_context(mail_create_nolog=True)).create(vals)
        if ticket.partner_id:
            ticket.message_subscribe(partner_ids=ticket.partner_id.ids)
            ticket._onchange_partner_id()
        if ticket.user_id:
            ticket.assign_date = ticket.create_date
            ticket.assign_hours = 0
        if ticket.team_id:
            ticket._onchange_team_id()
        if vals.get('stage_id'):
            ticket._email_send()

        return ticket

    @api.multi
    def write(self, vals):
        # we set the assignation date (assign_date) to now for tickets that are being assigned for the first time
        # same thing for the closing date
        assigned_tickets = closed_tickets = self.browse()
        if vals.get('user_id'):
            assigned_tickets = self.filtered(lambda ticket: not ticket.assign_date)
        if vals.get('stage_id') and self.env['helpdesk.stage'].browse(vals.get('stage_id')).is_close:
            closed_tickets = self.filtered(lambda ticket: not ticket.close_date)
        now = datetime.datetime.now()
        res = super(HelpdeskTicket, self - assigned_tickets - closed_tickets).write(vals)
        res &= super(HelpdeskTicket, assigned_tickets - closed_tickets).write(dict(vals, **{
            'assign_date': now,
        }))
        res &= super(HelpdeskTicket, closed_tickets - assigned_tickets).write(dict(vals, **{
            'close_date': now,
        }))
        res &= super(HelpdeskTicket, assigned_tickets & closed_tickets).write(dict(vals, **{
            'assign_date': now,
            'close_date': now,
        }))
        if vals.get('partner_id'):
            self.message_subscribe([vals['partner_id']])
        if vals.get('stage_id'):
            self._email_send()
        return res

    @api.multi
    def name_get(self):
        result = []
        for ticket in self:
            result.append((ticket.id, "%s (#%d)" % (ticket.name, ticket.id)))
        return result

    # Method to called by CRON to update SLA & statistics
    @api.model
    def recompute_all(self):
        tickets = self.search([('stage_id.is_close', '=', False)])
        tickets._compute_sla()
        tickets._compute_close_hours()
        return True

    @api.multi
    def assign_ticket_to_self(self):
        self.ensure_one()
        self.user_id = self.env.user

    @api.multi
    def open_customer_tickets(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Tickets'),
            'res_model': 'helpdesk.ticket',
            'view_mode': 'kanban,tree,form,pivot,graph',
            'context': {'search_default_is_open': True, 'search_default_partner_id': self.partner_id.id}
        }

    @api.multi
    def _email_send(self):
        for ticket in self.filtered(lambda ticket: ticket.stage_id and ticket.stage_id.template_id):
            ticket.stage_id.template_id.send_mail(res_id=ticket.id, force_send=True)

    #DVE FIXME: if partner gets created when sending the message it should be set as partner_id of the ticket.
    @api.multi
    def message_get_suggested_recipients(self):
        recipients = super(HelpdeskTicket, self).message_get_suggested_recipients()
        try:
            for ticket in self:
                if ticket.partner_id:
                    ticket._message_add_suggested_recipient(recipients, partner=ticket.partner_id, reason=_('Customer'))
                elif ticket.partner_email:
                    ticket._message_add_suggested_recipient(recipients, email=ticket.partner_email, reason=_('Customer Email'))
        except AccessError:  # no read access rights -> just ignore suggested recipients because this implies modifying followers
            pass
        return recipients

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'stage_id' in init_values and self.stage_id.sequence < 1:
            return 'helpdesk.mt_ticket_new'
        elif 'stage_id' in init_values and self.stage_id.sequence >= 1:
            return 'helpdesk.mt_ticket_stage'
        elif 'user_id' in init_values and self.user_id:  # assigned -> new
            return 'helpdesk.mt_ticket_new'
        return super(HelpdeskTicket, self)._track_subtype(init_values)

    @api.multi
    def _notification_group_recipients(self, message, recipients, done_ids, group_data):
        """ Override the mail.thread method to handle helpdesk users recipients.
        Indeed those will have specific action in their notification
        emails: creating tasks, assigning it. """
        for recipient in recipients:
            if recipient.id in done_ids:
                continue
            if recipient.user_ids and recipient.user_ids[0].has_group('helpdesk.group_helpdesk_user'):
                group_data['group_helpdesk_user'] |= recipient
            elif not recipient.user_ids:
                group_data['partner'] |= recipient
            elif all(recipient.user_ids.mapped('share')):
                group_data['partner'] |= recipient
            else:
                group_data['user'] |= recipient
            done_ids.add(recipient.id)
        return super(HelpdeskTicket, self)._notification_group_recipients(message, recipients, done_ids, group_data)

    @api.multi
    def _notification_get_recipient_groups(self, message, recipients):
        self.ensure_one()
        res = super(HelpdeskTicket, self)._notification_get_recipient_groups(message, recipients)

        actions = []
        if not self.user_id:
            take_action = self._notification_link_helper('assign')
            actions.append({'url': take_action, 'title': _('I take it')})
        else:
            new_action_id = self.env.ref('helpdesk.helpdesk_ticket_action_main').id
            new_action = self._notification_link_helper('new', action_id=new_action_id)
            actions.append({'url': new_action, 'title': _('New Ticket')})

        res['group_helpdesk_user'] = {
            'actions': actions
        }
        return res

    @api.model
    def message_new(self, msg, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None:
            custom_values = {}
        email = tools.email_split(msg.get('from')) and tools.email_split(msg.get('from'))[0] or False
        if email:
            user = self.env['res.users'].search([('login', '=', email)], limit=1)
            partner = self.env['res.partner'].search([('email', '=', email)], limit=1)
            if user or partner:
                custom_values['partner_id'] = user.partner_id.id or partner.id
            else:
                custom_values['partner_email'] = email
        return super(HelpdeskTicket, self).message_new(msg, custom_values=custom_values)

    @api.model
    def message_get_reply_to(self, res_ids, default=None):
        res = {}
        for res_id in res_ids:
            if self.browse(res_id).team_id.alias_name and self.browse(res_id).team_id.alias_domain:
                res[res_id] = self.browse(res_id).team_id.alias_name + '@' + self.browse(res_id).team_id.alias_domain
            else:
                res[res_id] = super(HelpdeskTicket, self).message_get_reply_to([res_id])[res_id]
        return res

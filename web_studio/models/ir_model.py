# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Base(models.AbstractModel):
    _inherit = 'base'

    def create_studio_model_data(self):
        """ We want to keep track of created records with studio
            (ex: model, field, view, action, menu, etc.).
            An ir.model.data is created whenever a record of one of these models
            is created, tagged with studio.
        """
        module = self.env['ir.module.module'].get_studio_module()

        self.env['ir.model.data'].create({
            'name': '%s' % uuid.uuid4(),
            'model': self._name,
            'res_id': self.id,
            'module': module.name,
        })


class IrModel(models.Model):
    _inherit = 'ir.model'

    mail_thread = fields.Boolean(compute='_compute_mail_thread',
                                 inverse='_inverse_mail_thread', store=True,
                                 help="Whether this model supports messages and notifications.")

    abstract = fields.Boolean(compute='_compute_abstract',
                              store=False,
                              help="Wheter this model is abstract",
                              search='_search_abstract')

    @api.depends('model')
    def _compute_mail_thread(self):
        MailThread = self.pool['mail.thread']
        for rec in self:
            if rec.model != 'mail.thread':
                Model = self.pool.get(rec.model)
                rec.mail_thread = Model and issubclass(Model, MailThread)

    def _inverse_mail_thread(self):
        pass        # do nothing; this enables to set the value of the field

    def _compute_abstract(self):
        for record in self:
            record.abstract = self.env[record.model]._abstract

    def _search_abstract(self, operator, value):
        abstract_models = [
            model._name
            for model in self.env.itervalues()
            if model._abstract
        ]
        dom_operator = 'in' if (operator, value) in [('=', True), ('!=', False)] else 'not in'

        return [('model', dom_operator, abstract_models)]

    @api.model
    def create(self, vals):
        res = super(IrModel, self).create(vals)

        if self._context.get('studio'):
            res.create_studio_model_data()
            # Create a simplified form view to prevent getting the default one containing all model's fields
            self.env['ir.ui.view'].create_simplified_form_view(res.model)

        return res

    @api.multi
    def write(self, vals):
        res = super(IrModel, self).write(vals)
        if self and 'mail_thread' in vals:
            if not all(rec.state == 'manual' for rec in self):
                raise UserError(_('Only custom models can be modified.'))
            # one can only change mail_thread from False to True
            if not all(rec.mail_thread <= vals['mail_thread'] for rec in self):
                raise UserError(_('Field "Mail Thread" cannot be changed to "False".'))
            # setup models; this reloads custom models in registry
            self.pool.setup_models(self._cr, partial=(not self.pool.ready))
            # update database schema of models
            models = self.pool.descendants(self.mapped('model'), '_inherits')
            self.pool.init_models(self._cr, models, dict(self._context, update_custom_fields=True))
            self.pool.signal_registry_change()
        return res

    @api.model
    def _instanciate(self, model_data):
        model_class = super(IrModel, self)._instanciate(model_data)
        if model_data.get('mail_thread'):
            parents = model_class._inherit or []
            parents = [parents] if isinstance(parents, basestring) else parents
            model_class._inherit = parents + ['mail.thread']
        return model_class


class IrModelField(models.Model):
    _inherit = 'ir.model.fields'

    track_visibility = fields.Selection(
        [('onchange', "On Change"), ('always', "Always")], string="Tracking",
        compute='_compute_track_visibility', inverse='_inverse_track_visibility', store=True,
        help="When set, every modification to this field will be tracked in the chatter.",
    )

    @api.depends('name')
    def _compute_track_visibility(self):
        for rec in self:
            if rec.model in self.env:
                field = self.env[rec.model]._fields.get(rec.name)
                rec.track_visibility = getattr(field, 'track_visibility', False)

    def _inverse_track_visibility(self):
        pass        # do nothing; this enables to set the value of the field

    @api.model
    def _instanciate(self, field_data, partial):
        field = super(IrModelField, self)._instanciate(field_data, partial)
        if field and field_data.get('track_visibility'):
            field.args = dict(field.args, track_visibility=field_data['track_visibility'])
        return field

    @api.model
    def create(self, vals):
        res = super(IrModelField, self).create(vals)

        if self._context.get('studio'):
            res.create_studio_model_data()

        return res
